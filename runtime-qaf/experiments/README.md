# Experiment protocol

The aim is to show that the Quality Index (a) tracks real quality changes, (b) separates normal operation from degraded operation, and (c) points to the service responsible. Traditional monitoring only shows separate charts per metric; these experiments compare that with the framework's output.

Each run takes about 5 minutes. Record it while the load test is running:

```bash
# terminal 1 - workload
docker compose run --rm k6 run -e PROFILE=<profile> --summary-export /scripts/results/k6-<scenario>.json /scripts/load.js
# terminal 2 - framework (start about 30 s after the load starts)
qaf record --scenario <scenario> --duration 240 --interval 15
```

Before each scenario, reset any faults with `qaf chaos <service> --reset` for every service, then wait about 1 minute so the rate windows clear.

| # | Scenario | Workload | Fault | Expected outcome |
|---|---|---|---|---|
| E1 | `low` | 5 VUs | none | All services Excellent |
| E2 | `medium` | 25 VUs | none | Excellent or Good; efficiency slightly lower |
| E3 | `peak` | 100 VUs | none | Performance, efficiency and scalability drop; QI falls to Fair or Poor; bottleneck = most CPU-bound service |
| E4 | `spike` | 10 → 150 → 10 VUs | none | QI dips, then recovers |
| E5 | `failure-payment-errors` | medium | `qaf chaos payment --error-rate 0.3` | payment and order reliability collapse; bottleneck = payment; circuit-breaker recommendation |
| E6 | `failure-order-latency` | medium | `qaf chaos order --latency 800` | order performance drops to Poor; caching recommendation |
| E7 | `failure-product-cpu` | medium | `qaf chaos product --cpu-burn 30` | product efficiency and performance drop; scale-out recommendation |
| E8 | `failure-user-memory` | low | `qaf chaos user --leak-mb 220` | user efficiency drops; memory-leak recommendation |
| E9 | `outage-payment` | medium | `docker compose stop payment` | payment QI = 0 (Critical); order reliability drops; system QI falls |

Afterwards:

```bash
qaf summarize experiments/results/*.csv              # mean QI / dimensions per scenario and service
qaf weights --csv experiments/results/*.csv          # AHP vs entropy vs hybrid weights
```

For the report, include the Grafana screenshots and the `summarize` tables. Discuss how the QI ranks the scenarios compared with reading the raw metric charts by hand.
