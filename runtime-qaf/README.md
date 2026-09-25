# Runtime Quality Assessment Framework (QAF) for Cloud-Native Microservices

M.Tech dissertation prototype (BITS ZG628T) —
**"Design and Development of a Lightweight Runtime Quality Assessment Framework for Cloud-Native Microservice Applications"**

Monitoring tools such as Prometheus and Grafana collect many runtime metrics and show each one separately. This framework combines those metrics into a single **Quality Index (QI, 0–100)** for each service and one for the whole system. It also rates quality on a scale from Excellent to Critical, finds which service causes the most quality loss, and recommends corrective actions.

## Architecture

```
  k6 load generator (low / medium / peak / spike)      fault injection (qaf chaos ...)
             │                                                  │
             ▼                                                  ▼
  ┌──────────────── Demo microservices (Node.js, Docker) ────────────────┐
  │   user :3001     product :3002     order :3003 ──► user/product/payment │
  │   payment :3004        each exposes /metrics, /health, /chaos          │
  └───────────────────────────────┬──────────────────────────────────────┘
                                  │ scrape every 5 s
                                  ▼
                         Prometheus :9090   ◄──────────────┐
                                  │ PromQL (query_range)   │ scrape qaf_* metrics
                                  ▼                        │
  ┌─────────────────── QAF engine (Python, :8000) ─────────┴───────────────┐
  │ M1 Metric Collector → M2 Preprocessing (noise / missing data)            │
  │ → M3 Quality Analyzer (normalisation, dimension scores)                  │
  │ → Weight Assignment (Fixed / AHP / Entropy / Hybrid)                     │
  │ → M4 Quality Index Calculator → Classification → M5 Recommendation Engine│
  └───────────────────────────────┬─────────────────────────────────────────┘
                                  ▼
               Console report / CSV experiment log / Grafana :3000
```

## Quality model

| Dimension | Metrics (sub-weight) | AHP weight |
|---|---|---|
| Performance (P) | p95 latency (0.6), mean latency (0.4) | 0.301 |
| Reliability (R) | 5xx error rate | 0.265 |
| Availability (A) | uptime (`up` over the window) | 0.186 |
| Resource efficiency (E) | CPU % of limit (0.5), memory % of limit (0.5) | 0.159 |
| Scalability (S) | tail ratio p99/p50 latency (grows as the service saturates and requests queue) | 0.089 |

- **Normalisation.** Each metric is mapped to a score from 0 to 100 against two thresholds, `good` and `bad`, set in `qaf/config/qaf.yaml`. The score is linear between them and clamped at either end. Because the thresholds are fixed, a score means the same thing in every run.
- **Quality Index.** `QI = w1·P + w2·R + w3·A + w4·E + w5·S`. The weights come from an AHP pairwise comparison matrix (λmax = 5.056, CR = 0.012, well under the 0.10 limit). The Entropy Weight Method and a hybrid of AHP and entropy are also built in.
- **Missing data.** Weights are renormalised over the dimensions that have data. A service that is down has only an availability score, which is 0, so its QI is 0.
- **System QI.** The average of the service QIs, weighted by how business-critical each service is (order 0.35, payment 0.30, product 0.20, user 0.15).
- **Bottleneck.** Each service's share of the system quality loss: `w_s(100 − QI_s) / Σ w_k(100 − QI_k)`.
- **Levels.** Excellent ≥ 90, Good ≥ 75, Fair ≥ 60, Poor ≥ 40, Critical < 40.

## Repository layout

```
runtime-qaf/
├── services/            Demo microservices (Node.js + Express + prom-client), fault injection
├── qaf/                 The framework (Python package)
│   ├── qaf/collector.py      M1 Metric Collector (Prometheus HTTP API, PromQL)
│   ├── qaf/preprocessing.py  M2 Preprocessing (IQR outlier removal, missing data, aggregation)
│   ├── qaf/scoring.py        M3/M4 Normalisation, dimension scores, QI, classification
│   ├── qaf/weighting.py      Fixed / AHP (+ consistency ratio) / Entropy / Hybrid weights
│   ├── qaf/recommender.py    M5 Rule-based recommendation engine
│   ├── qaf/engine.py         End-to-end assessment pipeline
│   ├── qaf/exporter.py       Publishes QI as Prometheus metrics for Grafana
│   ├── qaf/cli.py            `qaf` command line
│   ├── config/qaf.yaml       Thresholds, dimensions, weights, quality levels
│   └── tests/                Unit tests (pytest)
├── monitoring/          Prometheus config, Grafana datasource + "Runtime QAF Overview" dashboard
├── load-tests/          k6 workload profiles (low / medium / peak / spike)
├── experiments/         Experiment protocol and recorded results (CSV)
├── docs/                Notes for the dissertation reports
└── docker-compose.yml   Complete stack
```

## Quick start

Prerequisites: Docker Desktop and Python 3.10 or later.

```bash
# 1. Start the microservices, Prometheus, Grafana and the QAF exporter
docker compose up -d --build

# 2. Install the QAF command line on the host
pip install -e "./qaf[dev]"

# 3. Generate some traffic (runs ~5 minutes)
docker compose run --rm k6 run -e PROFILE=low /scripts/load.js

# 4. In another terminal: one-off quality assessment
qaf assess
```

| URL | What it is |
|---|---|
| http://localhost:3000 | Grafana: the "Runtime Quality Assessment – Overview" dashboard (opens with anonymous access) |
| http://localhost:9090 | Prometheus |
| http://localhost:8000/metrics | QAF output as `qaf_*` metrics |
| http://localhost:3001-3004/health | the microservices |

### CLI

```bash
qaf assess                         # table report: dimension scores, QI, level, bottleneck, recommendations
qaf assess --json --save out.json  # machine-readable result
qaf weights                        # AHP weights, lambda_max, CI, CR
qaf weights --csv experiments/results/*.csv   # entropy + hybrid weights from recorded data
qaf record --scenario medium --duration 300   # log an experiment run to CSV
qaf summarize experiments/results/*.csv       # compare scenarios
qaf chaos payment --error-rate 0.3            # inject 30% failures into payment
qaf chaos order --latency 800 --cpu-burn 20   # slow + CPU-heavy order service
qaf chaos payment --reset                     # remove faults
python -m pytest qaf                          # run the unit tests
```

See [experiments/README.md](experiments/README.md) for the full experiment protocol (low, medium and peak load, and failure scenarios).

## Running the services without Docker

```bash
cd services && npm install
npm run user    # likewise: npm run product / order / payment (each in its own terminal)
```

You would then need your own Prometheus instance scraping `localhost:3001-3004`.

## Tech stack

Node.js 22 (Express, prom-client) · Python 3.11 (numpy, requests, prometheus-client) · Docker Compose · Prometheus 2.53 · Grafana 11 · k6
