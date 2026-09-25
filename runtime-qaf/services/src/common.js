'use strict';

/**
 * Shared bootstrap for the demo microservices.
 *
 * Every service gets:
 *   - Prometheus instrumentation (request latency histogram, request counter,
 *     default process metrics such as CPU and resident memory)
 *   - /health endpoint
 *   - /chaos endpoint for fault injection (latency, errors, CPU burn, memory leak),
 *     used to create the "service failure" experiment scenarios.
 */

const express = require('express');
const client = require('prom-client');

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function burnCpu(ms) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    Math.sqrt(Math.random());
  }
}

/** Simulates backend work (e.g. a database call) taking between minMs and maxMs. */
function simulateWork(minMs, maxMs) {
  return sleep(minMs + Math.random() * (maxMs - minMs));
}

function createService(name) {
  const app = express();
  app.use(express.json());

  const register = new client.Registry();
  register.setDefaultLabels({ service: name });
  client.collectDefaultMetrics({ register });

  const labelNames = ['method', 'route', 'status'];
  const duration = new client.Histogram({
    name: 'http_request_duration_seconds',
    help: 'HTTP request latency in seconds',
    labelNames,
    buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
    registers: [register],
  });
  const requests = new client.Counter({
    name: 'http_requests_total',
    help: 'Total number of HTTP requests',
    labelNames,
    registers: [register],
  });

  const chaos = {
    latencyMs: Number(process.env.CHAOS_LATENCY_MS || 0),
    errorRate: Number(process.env.CHAOS_ERROR_RATE || 0),
    cpuBurnMs: Number(process.env.CHAOS_CPU_BURN_MS || 0),
  };
  const leaked = [];

  const internalPaths = new Set(['/metrics', '/health', '/chaos']);

  // Instrumentation + fault injection for every business request.
  app.use(async (req, res, next) => {
    if (internalPaths.has(req.path)) return next();

    const stopTimer = duration.startTimer();
    res.on('finish', () => {
      const route = req.route ? req.baseUrl + req.route.path : '/' + (req.path.split('/')[1] || '');
      const labels = { method: req.method, route, status: String(res.statusCode) };
      stopTimer(labels);
      requests.inc(labels);
    });

    if (chaos.latencyMs > 0) await sleep(chaos.latencyMs * (0.5 + Math.random()));
    if (chaos.cpuBurnMs > 0) burnCpu(chaos.cpuBurnMs);
    if (chaos.errorRate > 0 && Math.random() < chaos.errorRate) {
      return res.status(500).json({ error: 'injected fault', service: name });
    }
    return next();
  });

  app.get('/health', (req, res) => res.json({ status: 'UP', service: name }));

  app.get('/metrics', async (req, res) => {
    res.set('Content-Type', register.contentType);
    res.end(await register.metrics());
  });

  const chaosState = () => ({ service: name, ...chaos, leakedMb: leaked.length });

  app.get('/chaos', (req, res) => res.json(chaosState()));

  app.post('/chaos', (req, res) => {
    const body = req.body || {};
    for (const key of ['latencyMs', 'errorRate', 'cpuBurnMs']) {
      if (body[key] !== undefined) chaos[key] = Number(body[key]);
    }
    const leakMb = Number(body.leakMb || 0);
    for (let i = 0; i < leakMb; i++) leaked.push(Buffer.alloc(1024 * 1024, 1));
    res.json(chaosState());
  });

  app.delete('/chaos', (req, res) => {
    chaos.latencyMs = 0;
    chaos.errorRate = 0;
    chaos.cpuBurnMs = 0;
    leaked.length = 0;
    res.json(chaosState());
  });

  function start(port) {
    app.listen(port, () => console.log(`[${name}] listening on port ${port}`));
  }

  return { app, start };
}

/** Calls another service; throws an error carrying an HTTP status on failure. */
async function callService(baseUrl, path, options = {}) {
  let res;
  try {
    res = await fetch(baseUrl + path, {
      ...options,
      headers: { 'content-type': 'application/json' },
      signal: AbortSignal.timeout(Number(process.env.DOWNSTREAM_TIMEOUT_MS || 3000)),
    });
  } catch (err) {
    const wrapped = new Error(`${baseUrl}${path} unreachable: ${err.message}`);
    wrapped.status = err.name === 'TimeoutError' ? 504 : 502;
    throw wrapped;
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(`${baseUrl}${path} returned ${res.status}`);
    err.status = res.status >= 500 ? 502 : res.status;
    throw err;
  }
  return body;
}

module.exports = { createService, callService, simulateWork };
