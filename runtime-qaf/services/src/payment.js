'use strict';

const { createService, simulateWork } = require('./common');

const { app, start } = createService('payment');

let nextId = 1;

app.post('/payments', async (req, res) => {
  const { orderId, amount } = req.body || {};
  if (!orderId || !(Number(amount) > 0)) {
    return res.status(400).json({ error: 'orderId and a positive amount are required' });
  }
  // Payment gateways are typically the slowest dependency.
  await simulateWork(20, 60);
  return res.status(201).json({ id: nextId++, orderId, amount: Number(amount), status: 'CAPTURED' });
});

start(Number(process.env.PORT) || 3004);
