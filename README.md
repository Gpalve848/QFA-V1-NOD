# Runtime Quality Assessment Framework (QAF) — Project Knowledge Base

> **Purpose of this document.** This is the single, self-contained reference for the M.Tech dissertation project *"Design and Development of a Lightweight Runtime Quality Assessment Framework for Cloud-Native Microservice Applications"*. It is written so that a person **or another LLM** can answer any question about the project — its motivation, research contribution, design, formulas, implementation, functional and non-functional requirements, experiments, results, limitations, status and future plan — from this file alone.
>
> **How to use it (for LLMs):** Treat the numbers, formulas and file paths here as authoritative for the state of the project on **16 October 2026** (after the mid-semester submission). Section numbers are stable; cite them. Section 25 contains a question-and-answer bank; Sections 28–33 add the completion status and presentation guide, the live demo script, the AHP explanation, how to connect new services, a beginner's guide and the submission/plagiarism record. If a question concerns something not covered here, say so instead of guessing. Values marked *planned* are not yet implemented.

---

## Table of Contents

1. [Project Identity](#1-project-identity)
2. [Executive Summary](#2-executive-summary)
3. [Problem, Research Gap, Aim and Objectives](#3-problem-research-gap-aim-and-objectives)
4. [Dissertation Stages, Timeline and Status](#4-dissertation-stages-timeline-and-status)
5. [Key Concepts and Glossary](#5-key-concepts-and-glossary)
6. [System Architecture](#6-system-architecture)
7. [Quality Model](#7-quality-model)
8. [Weight Assignment (AHP, Entropy, Hybrid)](#8-weight-assignment-ahp-entropy-hybrid)
9. [Quality Index, Classification and Attribution](#9-quality-index-classification-and-attribution)
10. [Recommendation Engine](#10-recommendation-engine)
11. [Functional Requirements](#11-functional-requirements)
12. [Non-Functional Requirements](#12-non-functional-requirements)
13. [Implementation Details](#13-implementation-details)
14. [Configuration Reference (qaf.yaml)](#14-configuration-reference-qafyaml)
15. [Interfaces: CLI, HTTP Endpoints, Exported Metrics](#15-interfaces-cli-http-endpoints-exported-metrics)
16. [Testing](#16-testing)
17. [Experimental Setup and Protocol](#17-experimental-setup-and-protocol)
18. [Experimental Results](#18-experimental-results)
19. [Comparison with Threshold-Based Monitoring](#19-comparison-with-threshold-based-monitoring)
20. [Issues Found and Fixed](#20-issues-found-and-fixed)
21. [Limitations and Threats to Validity](#21-limitations-and-threats-to-validity)
22. [Design Decisions and Rationale](#22-design-decisions-and-rationale)
23. [Future Work (Second Half of the Semester)](#23-future-work-second-half-of-the-semester)
24. [Running, Reproducing and Troubleshooting](#24-running-reproducing-and-troubleshooting)
25. [Question-and-Answer Bank](#25-question-and-answer-bank)
26. [Repository Map](#26-repository-map)
27. [References](#27-references)
28. [Project Completion Status and How to Present It](#28-project-completion-status-and-how-to-present-it)
29. [Live Demo Script (Windows + VS Code)](#29-live-demo-script-windows--vs-code)
30. [Explaining the AHP Output to an Examiner](#30-explaining-the-ahp-output-to-an-examiner)
31. [Connecting Additional Services to the Framework](#31-connecting-additional-services-to-the-framework)
32. [Beginner's Guide: The Whole Project Explained from Zero](#32-beginners-guide-the-whole-project-explained-from-zero)
33. [Mid-Semester Submission and Plagiarism Check](#33-mid-semester-submission-and-plagiarism-check)

---

## 1. Project Identity

| Field | Value |
|---|---|
| Title | Design and Development of a Lightweight Runtime Quality Assessment Framework for Cloud-Native Microservice Applications |
| Short name | QAF (Quality Assessment Framework); the score it produces is the **QI** (Quality Index) |
| Student | Ganesh Ambadas Palve |
| BITS ID | 2024TM93686 |
| Programme | M.Tech. in Software Engineering, BITS Pilani — Work Integrated Learning Programmes (WILP) |
| Course | S1-26_SEZG628T: Dissertation (first semester of academic year 2026–27) |
| Organisation | Bajaj Finserv, Pune |
| Supervisor | Ajay Singh, Lead Architect, Bajaj Finserv, Pune |
| Additional examiner | Masawwar Ali, Tech Lead, Bajaj Finserv, Pune |
| Research area | Software architecture; runtime quality assessment of cloud-native microservices; observability; multi-criteria decision making |
| Source repository | https://github.com/Gpalve848/QFA-V1-NOD (branch `main`) |
| Status (16 Oct 2026) | Design, prototype and preliminary experiments complete; mid-semester report submitted (Turnitin similarity 4 %); second-half work pending |

---

## 2. Executive Summary

Microservice systems are monitored with tools such as **Prometheus** (metric collection) and **Grafana** (dashboards). These tools collect many runtime metrics — latency, error rate, availability, CPU, memory, throughput — but show each one separately. Engineers must interpret many charts to decide whether the system is healthy and which service is at fault.

The project builds a **lightweight framework that converts these metrics into one interpretable Quality Index (0–100)** per service and for the whole system. It:

1. collects metrics from Prometheus,
2. cleans them (noise and missing-data handling),
3. normalises each metric to a 0–100 score against *good* and *bad* thresholds,
4. groups them into **five quality dimensions** — Performance, Reliability, Availability, Resource Efficiency, Scalability,
5. weights the dimensions using the **Analytic Hierarchy Process (AHP)** (with the **Entropy Weight Method** and a hybrid also implemented),
6. computes the **QI** and classifies it as **Excellent / Good / Fair / Poor / Critical**,
7. computes each service's **share of the system's quality loss** (who is to blame), and
8. produces **rule-based recommendations** (scale out, add caching, add a circuit breaker, check for memory leaks …).

The framework was implemented in **Python** and evaluated on a **four-service e-commerce prototype** (User, Product, Order, Payment) written in **Node.js**, instrumented for Prometheus, with **fault injection**, a **Grafana** dashboard and **k6** load tests, all on **Docker Compose**.

Nine preliminary experiments (each run once) gave a system QI between **98.5** (medium load) and **49.8** (payment service stopped). In every failure scenario the framework identified the affected service. In **3 of 7 degraded scenarios** (peak load, spike load, CPU overload) typical static alert rules would **not** have fired, while the QI showed a clear drop and named the responsible service. Two important limitations were found: weighted averaging can **hide a single critical metric** (compensability), and errors that **propagate along the call chain** are partly blamed on the caller. These, plus repeated runs, weighting comparison, a structured comparison with alerting, and a Kubernetes deployment, form the second-half plan.

---

## 3. Problem, Research Gap, Aim and Objectives

### 3.1 Problem statement
Existing monitoring platforms **collect** metrics, **display** dashboards and **raise alerts** on individual thresholds, but they do not directly answer:
- Is the system healthy **overall**, considering all quality attributes together?
- Is quality improving or degrading over time or between deployments?
- **Which microservice** contributes most to the quality loss?
- Can two deployments be compared objectively with **one number**?

### 3.2 Research gap
Existing work falls into three groups:
1. **Observability methods** (Google SRE "four golden signals", Gregg's USE method, the RED method) define *what to measure* but not *how to combine* the signals into one judgement.
2. **Microservice quality metrics** mostly assess the *design* (coupling, cohesion, granularity), not *runtime behaviour*.
3. **Composite indices** with AHP/entropy weighting exist in other domains (for example, software process quality — the OSQI index), but not for runtime metrics of a running microservice system.

**Gap:** few works combine runtime microservice metrics into a **single, weighted, explainable Quality Index** that also **attributes quality loss to individual services** and **recommends corrective actions**. This is the project's contribution.

### 3.3 Aim
To develop a lightweight framework that evaluates the runtime quality of cloud-native microservices from multiple runtime metrics and computes a unified Quality Index.

### 3.4 Objectives (as approved in the outline) and status

| # | Objective | Status (Oct 2026) |
|---|---|---|
| 1 | Study runtime quality attributes of microservices | Completed |
| 2 | Identify measurable runtime metrics (Prometheus) | Completed |
| 3 | Design the Quality Assessment Framework | Completed |
| 4 | Develop the Quality Index model and weighting scheme | Completed |
| 5 | Implement the framework on a prototype (User, Product, Order, Payment) | Completed |
| 6 | Validate under low, medium, peak and failure-injected workloads | In progress (one run per scenario done) |
| 7 | Compare with traditional dashboard-based monitoring | In progress (preliminary comparison done) |

### 3.5 Scope
**In scope:** the framework (quality model, normalisation, weighting, QI, classification, attribution, recommendations) and its experimental validation on a proof-of-concept application on one machine.
**Out of scope:** a production-grade commercial monitoring product, large-scale multi-cluster deployment, security/compliance auditing of the services.

### 3.6 Expected contributions
1. A lightweight runtime quality assessment framework.
2. A Quality Index model for microservice health with principled (AHP/entropy) weights.
3. A quality classification mechanism (five levels).
4. Attribution of quality loss to services and a recommendation component.
5. Experimental validation under varying workloads and failures.

---

## 4. Dissertation Stages, Timeline and Status

### 4.1 Deliverables by stage

| Stage | Deliverable | File in repository root | Status |
|---|---|---|---|
| 1 | Project outline | `Stage1_Project-Outline.txt` | Completed |
| 2 | Abstract / outline report (with supervisor remarks) | `Stage2_Abstract_report.pdf` | Completed, approved |
| 3 | 10-slide presentation | `Stage3_Runtime_Quality_Assessment_Framework_Dissertation_10_Slides.pptx` | Completed |
| — | Prototype + experiments | `runtime-qaf/` | Completed (first half) |
| 4 | Mid-semester report (27 pages) | `Stage4_Mid-Sem_Report.docx`, `Stage4_Mid-Sem_Report.pdf` | **Submitted 27 Sep 2026**; Turnitin similarity **4 %** |
| 5 | Final dissertation report, demo, viva | — | Pending |

### 4.2 Plan of work (from the approved abstract) with status

| Phase | Dates (2026) | Work | Status |
|---|---|---|---|
| Literature review & outline | 01 Aug – 15 Aug | Quality attributes, observability literature, problem, gap | Completed |
| Framework & QI model design | 16 Aug – 30 Aug | Dimensions, metrics, normalisation, AHP/entropy, QI, levels | Completed |
| Prototype development | 01 Sep – 15 Sep | Four services, Prometheus, Grafana, all framework modules, tests | Completed |
| Experimentation & validation | 15 Sep – 04 Oct | Load tests, QI computation, comparison with dashboards | In progress (single runs done) |
| Dissertation review | 05 Oct – 19 Oct | Draft to supervisor and examiner | Pending |
| Final compilation & submission | 20 Oct – 05 Nov | Feedback, final report, demonstration | Pending |

### 4.3 Supervisor remarks from the Stage 2 approval
- Topic addresses a genuine gap (isolated dashboard metrics → single interpretable index); approved.
- AHP / Entropy weighting "adds methodological rigour".
- **Advice:** expand the literature with recent peer-reviewed work on QoS-based composite indices, and **benchmark against at least one existing monitoring approach** (addressed preliminarily in Section 19; full comparison planned).

---

## 5. Key Concepts and Glossary

| Term | Meaning in this project |
|---|---|
| Microservice | Small, independently deployable service; here User, Product, Order, Payment |
| Runtime quality | Quality observed while the system runs (speed, errors, uptime, resource use, capacity), as opposed to design-time quality |
| Prometheus | Open-source time-series database that scrapes `/metrics` endpoints |
| PromQL | Prometheus Query Language (e.g. `rate()`, `histogram_quantile()`) |
| Grafana | Dashboard tool reading from Prometheus |
| k6 | Load-testing tool; simulates *virtual users (VUs)* |
| p50 / p95 / p99 | 50th / 95th / 99th percentile of request latency (p95 = 95 % of requests are faster) |
| Tail ratio | p99 ÷ p50 latency; rises when requests queue (saturation). Used as the scalability metric |
| Quality dimension | One of five groups of metrics: Performance (P), Reliability (R), Availability (A), Resource Efficiency (E), Scalability (S) |
| Normalisation | Mapping a raw metric to a 0–100 score |
| Quality Index (QI) | Weighted sum of dimension scores, 0–100; per service and for the system |
| Quality level | Excellent ≥ 90, Good ≥ 75, Fair ≥ 60, Poor ≥ 40, Critical < 40 |
| AHP | Analytic Hierarchy Process (Saaty): weights from pairwise expert comparisons |
| CR | Consistency Ratio of an AHP matrix; acceptable if < 0.10 |
| EWM | Entropy Weight Method: objective weights from data variability (Shannon entropy) |
| Hybrid weight | α·AHP + (1 − α)·EWM, α = 0.5 by default |
| Degradation contribution / loss share | Percentage of the system's quality loss caused by a service |
| Bottleneck | Service with the largest loss share |
| Compensability | Property of weighted averages: a very bad score in one dimension can be offset by good scores in others |
| Fault injection / chaos | Deliberately adding latency, errors, CPU load or memory use to a service via its `/chaos` endpoint |
| Golden signals | Latency, traffic, errors, saturation (Google SRE) |
| USE / RED | Utilisation-Saturation-Errors (resources); Rate-Errors-Duration (requests) |

---

## 6. System Architecture

### 6.1 Overview

```
  k6 load generator (low / medium / peak / spike)        Fault injection (qaf chaos → /chaos)
             │                                                     │
             ▼                                                     ▼
  ┌──────────── Demo microservices (Node.js, Docker; 0.5 CPU / 256 MB each) ───────────┐
  │  user :3001     product :3002     order :3003 ──calls──► user, product, payment      │
  │  payment :3004          each exposes /metrics, /health, /chaos                         │
  └─────────────────────────────────────┬─────────────────────────────────────────────────┘
                                        │ scrape every 5 s
                                        ▼
                              Prometheus :9090  ◄───────────── scrapes qaf_* metrics (15 s)
                                        │ PromQL query_range (HTTP API)              │
                                        ▼                                            │
  ┌────────────────────── QAF engine (Python) ───────────────────────────────────────┴──┐
  │ M1 Metric Collector → M2 Preprocessing → M3 Quality Analyzer → Weight Assignment     │
  │ → M4 QI Calculator + Classification + Attribution → M5 Recommendation Engine          │
  └───────────────┬──────────────────────────┬──────────────────────────┬────────────────┘
                  ▼                          ▼                          ▼
     Console report / CSV           Exporter :8000 (qaf_* metrics)   Grafana :3000 dashboard
     (qaf assess / record)                                          "Runtime QAF Overview"
```

### 6.2 Components

| Component | Technology | Port | Role |
|---|---|---|---|
| user service | Node.js 22, Express, prom-client | 3001 | User catalogue (`GET /users`, `GET /users/:id`) |
| product service | same | 3002 | Product catalogue (`GET /products`, `GET /products/:id`) |
| order service | same | 3003 | Checkout (`POST /orders`) — calls user, product, payment; `GET /orders/:id` |
| payment service | same | 3004 | Payment capture (`POST /payments`) |
| Prometheus | prom/prometheus v2.53.0 | 9090 | Scrapes services every 5 s, QAF every 15 s |
| Grafana | grafana/grafana 11.1.0 | 3000 | Provisioned data source + "Runtime Quality Assessment – Overview" dashboard; anonymous admin access |
| QAF exporter | Python 3.11 (container) | 8000 | Runs `qaf serve`: assesses every 15 s and exposes `qaf_*` metrics |
| k6 | grafana/k6 0.52.0 | — | Load generator (compose profile `load`, started on demand) |

### 6.3 Data flow of one assessment
1. **Collector (M1)** sends 10 PromQL range queries to Prometheus covering the last **120 s** at a **10 s step**, with a **1-minute** rate window. Each query returns one time series per `service` label.
2. **Preprocessing (M2)** removes NaN/infinite samples, removes outliers outside `[Q1 − 1.5·IQR, Q3 + 1.5·IQR]`, aggregates each series to one value (median by default), derives the tail ratio, and — if the latest health sample is 0 — discards all metrics except availability.
3. **Quality Analyzer (M3)** normalises each metric to 0–100 and computes the five dimension scores.
4. **Weight Assignment** resolves dimension weights (AHP by default).
5. **QI Calculator (M4)** computes service QIs, levels, the system QI and loss shares.
6. **Recommendation Engine (M5)** evaluates rules per service.
7. Results are printed, written to CSV, or published as Prometheus metrics.

### 6.4 Call graph of the prototype
`order → user`, `order → product` (in parallel), then `order → payment`. A failure in any dependency makes the order request fail with HTTP 502 (or 504 on timeout, default timeout 3 s). This is intentional: it lets experiments observe **failure propagation**.

---

## 7. Quality Model

### 7.1 Dimensions, metrics, sub-weights and thresholds

| Dimension | Metric (sub-weight) | Good → score 100 | Bad → score 0 | Direction |
|---|---|---|---|---|
| Performance (P) | p95 latency `latency_p95_ms` (0.6) | ≤ 100 ms | ≥ 1000 ms | lower is better |
| | mean latency `latency_avg_ms` (0.4) | ≤ 50 ms | ≥ 500 ms | lower is better |
| Reliability (R) | 5xx error rate `error_rate_pct` (1.0) | 0 % | ≥ 5 % | lower is better |
| Availability (A) | share of successful scrapes `availability_pct` (1.0) | 100 % | ≤ 95 % | higher is better |
| Resource efficiency (E) | CPU, % of limit `cpu_pct` (0.5) | ≤ 50 % | ≥ 95 % | lower is better |
| | resident memory, % of limit `memory_pct` (0.5) | ≤ 50 % | ≥ 95 % | lower is better |
| Scalability (S) | tail ratio p99/p50 `tail_ratio` (1.0) | ≤ 3 | ≥ 15 | lower is better |

**Throughput** (`throughput_rps`) is collected and reported but **not scored**, because low traffic (e.g. at night) is not a quality problem. The thresholds are initial values based on common service-level objectives and are configurable; they are to be reviewed with the supervisor.

### 7.2 PromQL used by the collector (job = `microservices`, window w = 1m)

| Metric | PromQL (simplified) |
|---|---|
| latency_p50/p95/p99_ms | `1000 * histogram_quantile(0.50/0.95/0.99, sum by (service, le)(rate(http_request_duration_seconds_bucket[w])))` |
| latency_avg_ms | `1000 * sum by (service)(rate(..._sum[w])) / sum by (service)(rate(..._count[w]))` |
| throughput_rps | `sum by (service)(rate(http_requests_total[w]))` |
| error_rate_pct | `100 * (sum by (service)(rate(http_requests_total{status=~"5.."}[w])) or <total>*0) / <total>` (the `or … * 0` turns "no 5xx series" into an explicit 0 %) |
| availability_pct | `100 * avg by (service)(avg_over_time(up[w]))` |
| up_pct | `100 * avg by (service)(up)` — instantaneous health, used for down detection |
| cpu_pct | `100 * sum by (service)(rate(process_cpu_seconds_total[w])) / 0.5` (CPU limit in cores) |
| memory_pct | `100 * sum by (service)(process_resident_memory_bytes) / (256 MiB)` |

### 7.3 Normalisation formula
For a metric value *x* with thresholds *good* and *bad*:

```
score(x) = 100 × clamp( (x − bad) / (good − bad), 0, 1 )
```

The same formula serves both directions; the order of *good* and *bad* sets the direction. Example: p95 = 550 ms → (550 − 1000)/(100 − 1000) = 0.5 → score 50. Missing value → score `None` (not 0).

### 7.4 Dimension score
`D = Σ (sub-weight_i × score_i) / Σ sub-weight_i`, over the metrics of that dimension **that have a value** (sub-weights are renormalised over available metrics). If none is available, the dimension is `None`.

### 7.5 Why these five dimensions
They are the runtime-observable characteristics of **ISO/IEC 25010** (performance efficiency → time behaviour and resource utilisation; reliability → fault tolerance and availability; capacity → scalability) and correspond to the golden signals: latency → P, errors → R, traffic/saturation → S and E.

---

## 8. Weight Assignment (AHP, Entropy, Hybrid)

### 8.1 Methods available (`weighting.method` in config)
| Method | How weights are obtained | Nature |
|---|---|---|
| `fixed` | Configured values (outline: 0.30 / 0.25 / 0.20 / 0.15 / 0.10) | Manual |
| `ahp` (**default**) | Principal eigenvector of a pairwise comparison matrix | Subjective, expert-based, consistency-checked |
| `entropy` | Entropy Weight Method on observed dimension scores | Objective, data-driven |
| `hybrid` | α·AHP + (1 − α)·EWM, α = 0.5 | Combined |

### 8.2 AHP pairwise comparison matrix (Saaty 1–9 scale)
Order: Performance, Reliability, Availability, Efficiency, Scalability.

|  | P | R | A | E | S |
|---|---|---|---|---|---|
| **P** | 1 | 1 | 2 | 2 | 3 |
| **R** | 1 | 1 | 1 | 2 | 3 |
| **A** | 1/2 | 1 | 1 | 1 | 2 |
| **E** | 1/2 | 1/2 | 1 | 1 | 2 |
| **S** | 1/3 | 1/3 | 1/2 | 1/2 | 1 |

Reading: "Performance is moderately more important than Availability (2) and more important than Scalability (3)."

### 8.3 AHP results

| Dimension | AHP weight | Outline's fixed weight |
|---|---|---|
| Performance | **0.301** | 0.30 |
| Reliability | **0.265** | 0.25 |
| Availability | **0.186** | 0.20 |
| Efficiency | **0.159** | 0.15 |
| Scalability | **0.089** | 0.10 |

- λmax = **5.0555**; CI = (λmax − n)/(n − 1) = **0.0139**; RI(n = 5) = 1.12; **CR = CI/RI = 0.0124** (< 0.10 → consistent).
- Random Index table used: n = 1…10 → 0, 0, 0.58, 0.90, 1.12, 1.24, 1.32, 1.41, 1.45, 1.49.
- The code rejects nothing automatically but flags inconsistent matrices (`consistent = CR < 0.10`); a unit test checks that an inconsistent 3×3 matrix is detected.

### 8.4 Entropy Weight Method (implemented)
For an observation matrix X (rows = observations such as services or time windows; columns = dimensions; scores 0–100, higher is better):

```
p_ij = x_ij / Σ_i x_ij
e_j  = −(1 / ln n) · Σ_i p_ij · ln p_ij
d_j  = 1 − e_j                      (degree of diversification)
w_j  = d_j / Σ_j d_j
```
A small epsilon (1e-9) avoids ln 0. If fewer than 2 observations exist, the method falls back to AHP weights; if all criteria are identical, weights are equal. Missing values in X are filled with the column mean. Interpretation: dimensions that **vary more** across observations get **more weight**. A comparison of AHP vs entropy vs hybrid on the recorded data is **planned** (`qaf weights --csv …` already computes it).

---

## 9. Quality Index, Classification and Attribution

### 9.1 Service QI
```
QI = 0.301·P + 0.265·R + 0.186·A + 0.159·E + 0.089·S
```
Weights are **renormalised over available dimensions** (e.g. no latency when a service has no traffic), so missing data does not pull the score to zero.

### 9.2 Down-service rule
If the **most recent** `up_pct` sample is 0, the service is down *now*: all metrics except availability are discarded, so the QI equals the availability score (0 when availability ≤ 95 %) → **QI 0, Critical**. This prevents healthy samples from before the outage from inflating the score (bug found in experiment E9, see Section 20).

### 9.3 Quality levels

| QI | Level | Interpretation |
|---|---|---|
| 90–100 | Excellent | All dimensions within target |
| 75–89 | Good | Minor degradation in one dimension |
| 60–74 | Fair | Noticeable degradation; investigate |
| 40–59 | Poor | Serious degradation; action required |
| 0–39 | Critical | Service failing or unavailable |
| no data | Unknown | QI could not be computed |

### 9.4 System QI
Weighted mean of service QIs by **business criticality**: order 0.35, payment 0.30, product 0.20, user 0.15 (renormalised over services with a QI).

### 9.5 Degradation contribution (who is to blame)
```
share(s) = w_s · (100 − QI_s) / Σ_k w_k · (100 − QI_k)     (in %)
```
The service with the largest share is reported as the **bottleneck** (none if total loss is 0).

### 9.6 Worked example (E6, order latency)
Order: P = 0.0, R = 100, A = 100, E = 100, S = 99.9 →
QI = 0.301·0 + 0.265·100 + 0.186·100 + 0.159·100 + 0.089·99.9 ≈ 69.9 → **Fair**. All other services ≈ 99–100, so order has the largest loss share → bottleneck = order; rule "p95 > 1000 ms" → **critical performance** recommendation.

---

## 10. Recommendation Engine

| Condition (per service) | Severity | Dimension | Recommended action |
|---|---|---|---|
| availability < 99 % (critical < 95 %) | warning/critical | Availability | Check crash logs, add liveness/readiness probes, run more than one replica |
| error rate > 1 % (critical > 5 %) | warning/critical | Reliability | Investigate failing dependencies; add circuit breaker, timeouts, retries with back-off |
| p95 > 500 ms (critical > 1000 ms) | warning/critical | Performance | Add caching for hot reads, optimise slow queries/indexes, check downstream latency |
| CPU > 80 % of limit (critical > 95 %) | warning/critical | Efficiency | Scale out (HPA / replicas) or raise CPU limit; profile hot paths |
| memory > 80 % of limit (critical > 95 %) | warning/critical | Efficiency | Risk of OOM kill: check for leaks, unbounded caches, or raise limit |
| tail ratio > 10 | warning | Scalability | Requests queueing (saturation): scale out, review thread/connection pools |
| none of the above but weakest dimension < 75 | warning | weakest | "Monitor for further degradation" |

The engine is deliberately **rule-based and explainable** (no machine learning).

---

## 11. Functional Requirements

| ID | Requirement | Implemented in | Status |
|---|---|---|---|
| FR1 | Collect runtime metrics (latency percentiles, mean latency, throughput, error rate, availability, CPU, memory, health) per service from Prometheus | `collector.py` | Done |
| FR2 | Remove noise (IQR outliers) and handle missing data | `preprocessing.py` | Done |
| FR3 | Detect a service that is currently down and score it as unavailable | `preprocessing.is_down` | Done |
| FR4 | Normalise metrics to 0–100 with configurable good/bad thresholds | `scoring.normalize` | Done |
| FR5 | Compute five dimension scores with configurable sub-weights | `scoring.dimension_scores` | Done |
| FR6 | Assign dimension weights by fixed, AHP (with CR), entropy or hybrid methods | `weighting.py` | Done |
| FR7 | Compute service QI and system QI | `scoring`, `engine.py` | Done |
| FR8 | Classify QI into five levels | `scoring.classify` | Done |
| FR9 | Attribute quality loss to services and identify the bottleneck | `scoring.degradation_contributions` | Done |
| FR10 | Generate rule-based recommendations | `recommender.py` | Done |
| FR11 | Report results on the console and as JSON | `report.py`, `qaf assess` | Done |
| FR12 | Record assessments over time to CSV for experiments; summarise them | `qaf record`, `qaf summarize` | Done |
| FR13 | Publish results as Prometheus metrics for Grafana | `exporter.py`, `qaf serve` | Done |
| FR14 | Visualise QI, levels, dimensions, loss shares and raw metrics | Grafana dashboard JSON | Done |
| FR15 | Inject and remove faults (latency, errors, CPU burn, memory) | services `/chaos`, `qaf chaos` | Done |
| FR16 | Generate workloads (low, medium, peak, spike) | `load-tests/load.js` | Done |
| FR17 | Run the full experiment protocol automatically | `experiments/run_all.sh` | Done |
| FR18 | Generate report figures and the Word report from results | `docs/mid-sem-report/` | Done |
| FR19 | Non-compensatory cap when a dimension is critical | — | *Planned* |
| FR20 | Dependency-aware attribution | — | *Planned* |

---

## 12. Non-Functional Requirements

| ID | Quality attribute | Requirement / how it is met |
|---|---|---|
| NFR1 | **Lightweight** | Framework is a small Python package (~650 lines of code) with 4 dependencies (requests, PyYAML, numpy, prometheus-client); one assessment = 10 PromQL range queries every 15 s; no agents inside services; no database of its own |
| NFR2 | **Non-intrusive / tool-agnostic** | Needs only standard Prometheus metrics (`http_request_duration_seconds` histogram, `http_requests_total`, `process_*`, `up`). Works with services in any language; no code changes beyond a standard Prometheus client |
| NFR3 | **Configurability** | All thresholds, dimensions, sub-weights, weighting method, AHP matrix, service weights, resource limits, windows and levels in one YAML file; Prometheus URL overridable by `QAF_PROMETHEUS_URL` |
| NFR4 | **Explainability** | Linear model with published weights; per-dimension and per-metric scores; loss shares; recommendations tied to rules and metric values |
| NFR5 | **Robustness / fault tolerance** | Missing metrics renormalised instead of zeroed; NaN handling; exporter keeps running if Prometheus is unavailable (logs warning, retries next cycle); down detection |
| NFR6 | **Reproducibility** | Entire stack via `docker compose up`; experiments via one script that restarts services, cools down and records; raw CSVs and k6 logs committed; figures and report generated from data |
| NFR7 | **Testability / correctness** | 17 pytest unit tests; framework logic (`assess_metrics`) testable without Prometheus |
| NFR8 | **Maintainability / modularity** | One module per framework component; clear pipeline; PromQL templates in one dictionary |
| NFR9 | **Portability** | Docker images; runs on Windows/macOS/Linux; tested on Windows 11 + Docker Desktop; `.gitattributes` keeps shell scripts LF |
| NFR10 | **Performance / timeliness** | Prometheus scrape 5 s; assessment every 15 s; 1-min rate window + 2-min lookback → a fault is reflected within roughly 1 minute |
| NFR11 | **Usability** | Single-command CLI; human-readable console report; ready-made Grafana dashboard with colour-coded levels |
| NFR12 | **Scalability of the framework** | Query cost depends on number of services, not request volume (aggregation done inside Prometheus) |
| NFR13 | **Security (prototype scope)** | Local lab only. Grafana anonymous admin and unauthenticated `/chaos` endpoints are acceptable for the prototype but **must not** be exposed in production |

---

## 13. Implementation Details

### 13.1 Technology stack

| Layer | Technology | Version | Reason |
|---|---|---|---|
| Services | Node.js, Express, prom-client | Node 22, Express 4.21, prom-client 15 | Lightweight, fast startup, standard Prometheus client |
| Framework | Python | 3.11 | numpy for AHP eigenvectors; simple scientific tooling |
| Containers | Docker, Docker Compose | Docker 28 | One-command reproducible environment |
| Metrics | Prometheus | 2.53.0 | De-facto open-source standard |
| Dashboards | Grafana | 11.1.0 | Standard visualisation; provisioned automatically |
| Load testing | k6 | 0.52.0 | Scriptable JS load tests, Docker image |
| Tests | pytest | 8 | Unit tests |
| Report generation | matplotlib, docx (npm), WPS Office | — | Figures and Word report from data |
| Version control | Git, GitHub | — | `Gpalve848/QFA-V1-NOD` |

The outline allowed **Spring Boot or Node.js** and **Kubernetes or Docker Compose**; Node.js + Docker Compose were chosen for the first half (see Section 22). Kubernetes is planned.

### 13.2 Microservices (`runtime-qaf/services/`)
- `src/common.js` — shared bootstrap: Express app, Prometheus registry with default label `service`, histogram `http_request_duration_seconds` (buckets 5 ms … 10 s), counter `http_requests_total{method,route,status}`, default process metrics, `/health`, `/metrics`, `/chaos`, and `callService()` helper (timeout `DOWNSTREAM_TIMEOUT_MS`, default 3000 ms; unreachable → 502, timeout → 504).
- Simulated work: user 2–20 ms, product 3–30 ms, payment 20–60 ms, order +5–15 ms after downstream calls.
- Data: in-memory (50 users, 100 products; orders kept up to 10 000). No database (out of scope for the first half).
- One Docker image per service built from the same code; the `SERVICE` environment variable selects `user|product|order|payment`.
- Resource limits (docker-compose): **0.5 CPU, 256 MB** per service — must match `resources` in `qaf.yaml`.

### 13.3 Fault injection API (each service)
| Request | Effect |
|---|---|
| `GET /chaos` | Show current faults |
| `POST /chaos {"latencyMs": 800}` | Add 800 ms × (0.5–1.5 random) to every business request |
| `POST /chaos {"errorRate": 0.3}` | 30 % of requests return HTTP 500 |
| `POST /chaos {"cpuBurnMs": 30}` | Busy-loop 30 ms per request |
| `POST /chaos {"leakMb": 220}` | Allocate and hold 220 MB |
| `DELETE /chaos` | Remove all faults and free memory |
Environment variables `CHAOS_LATENCY_MS`, `CHAOS_ERROR_RATE`, `CHAOS_CPU_BURN_MS` set faults at start-up.

### 13.4 Framework package (`runtime-qaf/qaf/qaf/`)

| File | Module | Key functions |
|---|---|---|
| `config.py` | Config loader | `load_config()` (supports fractions like `1/3` in YAML; env override) |
| `collector.py` | M1 | `QUERIES` dict; `PrometheusCollector.collect()` |
| `preprocessing.py` | M2 | `clean_series()` (IQR), `aggregate()` (median/mean/EWMA), `is_down()`, `preprocess()` (adds `tail_ratio`) |
| `scoring.py` | M3/M4 | `normalize()`, `weighted_mean()`, `metric_scores()`, `dimension_scores()`, `quality_index()`, `classify()`, `degradation_contributions()` |
| `weighting.py` | Weights | `ahp_weights()`, `entropy_weights()`, `score_matrix()`, `resolve_weights()` |
| `recommender.py` | M5 | `recommend()` |
| `engine.py` | Pipeline | `assess_metrics()` (pure, testable), `assess()` (with Prometheus); dataclasses `ServiceAssessment`, `SystemAssessment` |
| `report.py` | Reporting | console table, CSV rows, `summarize()` |
| `exporter.py` | Prometheus exporter | `publish()`, `serve()` |
| `cli.py` | CLI | `assess`, `serve`, `record`, `summarize`, `weights`, `chaos` |

### 13.5 Monitoring
- `monitoring/prometheus/prometheus.yml`: global scrape 5 s; job `microservices` (4 static targets with label `service`, `honor_labels: true`); job `qaf` (15 s); job `prometheus`.
- Grafana provisioning: data source uid `prometheus`; dashboard `qaf-overview.json` (refresh 10 s, last 30 min) with 10 panels: System QI (stat), Service QI (gauges), Quality level (stat with value mapping), QI over time, Degradation contribution, Dimension scores, p95 latency, Throughput, Error rate, CPU/Memory % of limit.

### 13.6 Load tests (`load-tests/load.js`)
Traffic mix per iteration: 30 % `GET /products`, 20 % `GET /products/:id`, 15 % `GET /users/:id`, 35 % `POST /orders`; think time 0.5–1.5 s (≈ 1 request/s per VU).

| Profile | Stages |
|---|---|
| low | 30 s ramp to 5 VUs, 4 min at 5, 15 s down |
| medium | 30 s ramp to 25, 4 min at 25, 15 s down |
| peak | 1 min ramp to 100, 4 min at 100, 15 s down |
| spike | 1 min at 10 → 10 s to 150 → 1 min at 150 → 10 s to 10 → 2 min at 10 → 10 s down |

---

## 14. Configuration Reference (`qaf.yaml`)

| Key | Default | Meaning |
|---|---|---|
| `prometheus_url` | `http://localhost:9090` | Overridden by `QAF_PROMETHEUS_URL` (container uses `http://prometheus:9090`) |
| `job` | `microservices` | Prometheus job of the services |
| `collection.rate_window` | `1m` | Window inside `rate()` / `avg_over_time()` |
| `collection.lookback_seconds` | 120 | History per assessment |
| `collection.step_seconds` | 10 | Sample resolution |
| `preprocessing.outlier_iqr_k` | 1.5 | IQR outlier factor |
| `preprocessing.aggregation` | `median` | `median`, `mean` or `ewma` (`ewma_alpha` 0.3) |
| `resources.cpu_limit_cores` | 0.5 | For CPU % |
| `resources.memory_limit_mb` | 256 | For memory % |
| `services.<name>.url / weight` | user 0.15, product 0.20, order 0.35, payment 0.30 | Chaos URL and business criticality |
| `metrics.<metric>.good / bad` | see Section 7.1 | Normalisation thresholds |
| `dimensions` | see Section 7.1 | Metrics and sub-weights per dimension |
| `weighting.method` | `ahp` | `fixed`, `ahp`, `entropy`, `hybrid` |
| `weighting.ahp_matrix` | Section 8.2 | Pairwise matrix |
| `weighting.hybrid_alpha` | 0.5 | Hybrid mixing factor |
| `quality_levels` | Excellent 90, Good 75, Fair 60, Poor 40, Critical 0 | Lower bounds |

---

## 15. Interfaces: CLI, HTTP Endpoints, Exported Metrics

### 15.1 CLI (`qaf`, installed with `pip install -e ./runtime-qaf/qaf[dev]`)

| Command | Purpose |
|---|---|
| `qaf assess [--json] [--save file]` | One assessment: dimension table, QI, level, loss share, key metrics, recommendations |
| `qaf serve [--port 8000] [--interval 15]` | Continuous assessment + Prometheus exporter |
| `qaf record --scenario NAME [--duration 300] [--interval 15] [--out file]` | Record to CSV (`experiments/results/`) |
| `qaf summarize FILES…` | Mean QI, dimensions, p95, error %, CPU per scenario/service |
| `qaf weights [--csv FILES…]` | AHP weights, λmax, CI, CR; entropy and hybrid weights from recordings |
| `qaf chaos SERVICE [--latency MS] [--error-rate R] [--cpu-burn MS] [--leak-mb N] [--reset]` | Fault injection |
| global `--config PATH` | Alternative configuration file |

### 15.2 CSV columns (`qaf record`)
`timestamp, scenario, service`, the raw metrics (`latency_p50_ms … up_pct, tail_ratio`), `dim_performance … dim_scalability`, `quality_index, level, system_quality_index, system_level, weight_method`.

### 15.3 Metrics exported by the QAF exporter (`:8000/metrics`)

| Metric | Labels | Meaning |
|---|---|---|
| `qaf_system_quality_index` | — | System QI |
| `qaf_quality_index` | service | Service QI |
| `qaf_quality_level` | service | 0 Critical, 1 Poor, 2 Fair, 3 Good, 4 Excellent |
| `qaf_dimension_score` | service, dimension | Dimension scores |
| `qaf_degradation_contribution_pct` | service | Loss share |
| `qaf_dimension_weight` | dimension | Weights in use |
| `qaf_active_recommendations` | service, severity | Number of recommendations |
| `qaf_last_assessment_timestamp_seconds` | — | Time of last successful assessment |

### 15.4 URLs when running
Grafana http://localhost:3000 · Prometheus http://localhost:9090 · QAF http://localhost:8000/metrics · services http://localhost:3001–3004/health

---

## 16. Testing

17 pytest tests in `runtime-qaf/qaf/tests/test_qaf.py` (all passing):

1. Normalisation, lower-is-better (100, 0, midpoint 50, clamping)
2. Normalisation, higher-is-better and `None` handling
3. Weighted mean ignores missing values
4. Quality-level bands
5. Default AHP matrix is consistent, weights sum to 1, performance is highest
6. Inconsistent AHP matrix is detected
7. Entropy gives more weight to the discriminating criterion
8. IQR cleaning removes outliers and NaN; median aggregation
9. Tail ratio derived in preprocessing
10. Healthy service → Excellent, no recommendations
11. Degraded service → QI < 50, identified as bottleneck, correct recommendation dimensions
12. Down service (availability 0) → QI 0, Critical
13–16. All four weighting methods produce weights summing to 1 (parametrised)
17. Service down now ignores stale pre-outage samples → QI 0

Manual end-to-end checks: services return orders; with payment `errorRate=1` the order request returns 502 and the counters record `status="502"`; Prometheus shows all targets up; Grafana health 200.

---

## 17. Experimental Setup and Protocol

- **Machine:** laptop, Intel Core i5-7300HQ (4 cores, 2.5 GHz), 16 GB RAM, Windows 11, Docker Desktop (Docker VM: 4 CPUs, ~8 GB).
- **Limits:** each service 0.5 CPU, 256 MB (so saturation is reachable with moderate load).
- **Protocol per scenario** (`experiments/run_all.sh`): (1) restart all four services; (2) cool down 60 s; (3) start k6 profile; (4) inject fault after 15 s; (5) after 75 s warm-up, record one assessment every 15 s for 180 s → **12 assessments per service per scenario**; (6) wait for k6 to finish. Final reset restarts everything.
- **Each scenario was run once** (preliminary; repeated runs planned).
- Results: `runtime-qaf/experiments/results/E1-low.csv … E9-outage-payment.csv` (48 rows each); k6 logs in `runtime-qaf/load-tests/results/`.

| ID | Scenario | Load | Injected fault |
|---|---|---|---|
| E1 | low | 5 VUs | none |
| E2 | medium | 25 VUs | none |
| E3 | peak | 100 VUs | none |
| E4 | spike | 10 → 150 → 10 VUs | none |
| E5 | failure-payment-errors | 25 VUs | `qaf chaos payment --error-rate 0.3` |
| E6 | failure-order-latency | 25 VUs | `qaf chaos order --latency 800` |
| E7 | failure-product-cpu | 25 VUs | `qaf chaos product --cpu-burn 30` |
| E8 | failure-user-memory | 5 VUs | `qaf chaos user --leak-mb 220` |
| E9 | outage-payment | 25 VUs | `docker compose stop payment` |

---

## 18. Experimental Results

All values are means over the 12 assessments of each scenario (run of 26 Sep 2026, after the fixes in Section 20). Weighting: AHP.

### 18.1 System and service QI

| ID | Scenario | System QI | Level | User QI | Product QI | Order QI | Payment QI |
|---|---|---|---|---|---|---|---|
| E1 | Low | **98.0** | Excellent | 99.7 | 99.5 | 94.8 | 100.0 |
| E2 | Medium | **98.5** | Excellent | 99.7 | 99.4 | 96.1 | 100.0 |
| E3 | Peak | **90.7** | Excellent | 98.7 | 99.4 | 74.2 | 100.0 |
| E4 | Spike | **93.3** | Excellent | 99.6 | 99.4 | 81.5 | 100.0 |
| E5 | Payment errors | **82.0** | Good | 99.7 | 99.5 | 71.7 | 73.5 |
| E6 | Order latency | **89.3** | Good | 99.7 | 99.4 | 69.9 | 100.0 |
| E7 | Product CPU | **92.9** | Excellent | 99.7 | 89.3 | 86.1 | 100.0 |
| E8 | User memory | **97.3** | Excellent | 91.8 | 99.4 | 96.3 | 100.0 |
| E9 | Payment outage | **49.8** | Poor | 99.8 | 99.6 | 42.7 | 0.0 |

### 18.2 Full per-service detail (dimension scores and key metrics)

| ID | Service | QI | Perf | Rel | Avail | Eff | Scal | p95 ms | err % | CPU % | Mem % | req/s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | user | 99.7 | 100.0 | 100.0 | 100.0 | 100.0 | 96.3 | 20.7 | 0.00 | 3.9 | 28.1 | 1.9 |
| E1 | product | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 94.4 | 40.8 | 0.00 | 4.0 | 28.7 | 3.4 |
| E1 | order | 94.8 | 92.4 | 100.0 | 100.0 | 100.0 | 67.7 | 171.6 | 0.00 | 8.6 | 31.8 | 1.4 |
| E1 | payment | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 90.9 | 0.00 | 3.2 | 28.3 | 1.4 |
| E2 | user | 99.7 | 100.0 | 100.0 | 100.0 | 100.0 | 96.9 | 20.4 | 0.00 | 7.6 | 29.8 | 9.8 |
| E2 | product | 99.4 | 100.0 | 100.0 | 100.0 | 100.0 | 92.9 | 39.9 | 0.00 | 12.0 | 30.3 | 17.0 |
| E2 | order | 96.1 | 93.1 | 100.0 | 100.0 | 100.0 | 79.3 | 164.1 | 0.00 | 22.4 | 33.7 | 7.0 |
| E2 | payment | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 91.0 | 0.00 | 6.7 | 29.8 | 7.0 |
| E3 | user | 98.7 | 100.0 | 100.0 | 100.0 | 100.0 | 84.9 | 21.0 | 0.00 | 17.7 | 30.5 | 32.6 |
| E3 | product | 99.4 | 100.0 | 100.0 | 100.0 | 100.0 | 93.4 | 39.6 | 0.00 | 24.2 | 30.8 | 55.4 |
| E3 | order | 74.2 | 49.3 | 100.0 | 100.0 | 82.2 | 14.1 | 696.1 | 0.00 | 57.0 | 35.0 | 22.9 |
| E3 | payment | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 91.0 | 0.00 | 15.4 | 30.4 | 22.9 |
| E4 | user | 99.6 | 100.0 | 100.0 | 100.0 | 100.0 | 95.8 | 20.1 | 0.00 | 10.7 | 29.9 | 21.8 |
| E4 | product | 99.4 | 100.0 | 100.0 | 100.0 | 100.0 | 93.2 | 41.1 | 0.00 | 14.5 | 29.4 | 36.5 |
| E4 | order | 81.5 | 60.2 | 100.0 | 100.0 | 98.5 | 29.4 | 560.6 | 0.00 | 31.1 | 33.8 | 14.5 |
| E4 | payment | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 91.6 | 0.00 | 8.8 | 29.9 | 14.6 |
| E5 | user | 99.7 | 100.0 | 100.0 | 100.0 | 100.0 | 96.8 | 20.3 | 0.00 | 8.3 | 29.8 | 10.1 |
| E5 | product | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 94.3 | 38.5 | 0.00 | 12.0 | 30.3 | 17.2 |
| E5 | order | 71.7 | 96.3 | 0.0 | 100.0 | 100.0 | 91.7 | 138.8 | 27.69 | 23.9 | 33.7 | 7.0 |
| E5 | payment | 73.5 | 100.0 | 0.0 | 100.0 | 100.0 | 100.0 | 87.9 | 27.55 | 7.0 | 29.8 | 7.0 |
| E6 | user | 99.7 | 100.0 | 100.0 | 100.0 | 100.0 | 96.1 | 19.7 | 0.00 | 6.6 | 29.6 | 8.2 |
| E6 | product | 99.4 | 100.0 | 100.0 | 100.0 | 100.0 | 92.8 | 38.4 | 0.00 | 8.9 | 30.1 | 13.8 |
| E6 | order | 69.9 | 0.0 | 100.0 | 100.0 | 100.0 | 99.9 | 2283.5 | 0.00 | 19.2 | 33.4 | 5.6 |
| E6 | payment | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 90.9 | 0.00 | 5.5 | 29.5 | 5.6 |
| E7 | user | 99.7 | 100.0 | 100.0 | 100.0 | 100.0 | 96.4 | 20.2 | 0.00 | 7.4 | 29.7 | 9.1 |
| E7 | product | 89.3 | 84.7 | 100.0 | 100.0 | 65.5 | 93.9 | 247.8 | 0.00 | 74.6 | 30.8 | 15.0 |
| E7 | order | 86.1 | 54.9 | 100.0 | 100.0 | 100.0 | 96.1 | 514.5 | 0.00 | 20.6 | 33.7 | 6.3 |
| E7 | payment | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 89.7 | 0.00 | 6.3 | 29.6 | 6.3 |
| E8 | user | 91.8 | 100.0 | 100.0 | 100.0 | 50.0 | 96.9 | 21.2 | 0.00 | 4.3 | 114.6 | 2.1 |
| E8 | product | 99.4 | 100.0 | 100.0 | 100.0 | 100.0 | 93.1 | 39.8 | 0.00 | 4.8 | 28.6 | 3.6 |
| E8 | order | 96.3 | 95.2 | 100.0 | 100.0 | 100.0 | 74.2 | 132.0 | 0.00 | 8.8 | 31.9 | 1.6 |
| E8 | payment | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 90.5 | 0.00 | 3.7 | 28.3 | 1.6 |
| E9 | user | 99.8 | 100.0 | 100.0 | 100.0 | 100.0 | 97.5 | 21.1 | 0.00 | 6.7 | 29.5 | 5.6 |
| E9 | product | 99.6 | 100.0 | 100.0 | 100.0 | 100.0 | 95.0 | 40.4 | 0.00 | 8.7 | 30.0 | 9.4 |
| E9 | order | 42.7 | 0.0 | 0.0 | 100.0 | 100.0 | 91.7 | 4848.3 | 86.82 | 16.7 | 33.9 | 3.8 |
| E9 | payment | 0.0 | – | – | 0.0 | – | – | – | – | – | – | – |

### 18.3 Interpretation by scenario
- **E1/E2 (low, medium):** system Excellent (98.0 / 98.5). Order is slightly lower (94.8 / 96.1) because it is the slowest service (it calls three others; p95 ≈ 165–170 ms); its scalability score at low load (67.7 in E1) is affected by noisy tail ratios at very low request rates (a known limitation).
- **E3 (peak, 100 VUs):** order falls to **Fair (74.2)**: p95 696 ms, CPU 57 % of limit, scalability 14.1 (heavy queueing). System 90.7. Recommendation: performance warning. Over time, order drifts from Good to Fair and recovers when the load ramps down.
- **E4 (spike):** order **Good (81.5)**, p95 561 ms; system 93.3.
- **E5 (30 % payment errors):** payment and order reliability both **0** (error rate ≈ 27.6 %); QIs 73.5 and 71.7 (**Fair**); system 82.0 (Good). Critical reliability recommendations for both. Order gets a slightly larger loss share although payment is the root cause (see Section 21).
- **E6 (+800 ms on order):** order performance **0** (p95 2284 ms), other dimensions 100 → QI 69.9 (Fair); critical performance recommendation.
- **E7 (CPU burn on product):** product CPU 74.6 % → efficiency 65.5, performance 84.7, QI 89.3; the symptom also appears on order (p95 515 ms, QI 86.1) because order calls product.
- **E8 (220 MB leak in user):** user memory **114.6 % of limit** (the container was swapping), efficiency 50 → QI **91.8, still Excellent** → demonstrates the **compensability** problem; critical efficiency recommendation was still produced.
- **E9 (payment stopped):** payment **QI 0 (Critical)**, availability 0; order **Poor (42.7)** with 86.8 % errors and p95 4848 ms (timeouts); system **49.8 (Poor)**. Recommendations: critical availability (payment), critical reliability + performance (order).

### 18.4 Recommendations produced (from mean metrics)
| Scenario | Service: recommendation |
|---|---|
| E1 | order: scalability warning (noisy tail ratio at low load) |
| E3, E4 | order: performance warning |
| E5 | order and payment: critical reliability |
| E6 | order: critical performance |
| E7 | product: efficiency warning; order: performance warning |
| E8 | user: critical efficiency (memory); order: scalability warning |
| E9 | payment: critical availability; order: critical reliability + critical performance |

### 18.5 Figures (in `runtime-qaf/docs/mid-sem-report/figures/`)
`fig1_architecture.png`, `fig2_ahp_weights.png`, `fig3_system_qi.png` (system QI per scenario with level bands), `fig4_service_qi_heatmap.png`, `fig5_qi_timelines.png` (E3, E5, E9 over time), `fig6_dimension_scores.png`.

---

## 19. Comparison with Threshold-Based Monitoring

Baseline: typical static Prometheus alert rules — CPU > 80 % of limit, memory > 80 %, error rate > 5 %, p95 > 1 s, service down.

| Scenario | Static alerts that fire | Framework output |
|---|---|---|
| E3 Peak | **None** | Order Fair (74.2), p95 696 ms, high tail ratio |
| E4 Spike | **None** | Order Good (81.5), p95 561 ms |
| E5 Payment errors | Error rate (order, payment) | Both Fair; loss split between order and payment |
| E6 Order latency | Latency (order) | Order Fair (69.9); performance score 0 |
| E7 Product CPU | **None** | Product 89.3 (CPU 75 %); order latency 515 ms |
| E8 User memory | Memory (user) | User 91.8 — still Excellent (compensability) |
| E9 Payment outage | Service down; errors and latency (order) | Payment Critical (0); order Poor (42.7); system Poor |

**Finding:** in **3 of 7** degraded scenarios no static alert fires, because each metric stays under its threshold, while the QI drops and names the service. In E7 the cause (product CPU) and symptom (order latency) are on different services; the dimension scores show both. Conversely, E8 shows a case where a static memory alert fires but the QI stays Excellent. This is a **preliminary** comparison (one run, one alert configuration); a structured comparison (detection, time-to-detect, correct attribution) is planned.

---

## 20. Issues Found and Fixed

| Issue | Found in | Cause | Fix |
|---|---|---|---|
| k6 never ran in the first batch | first batch, E1 | Git Bash on Windows rewrote `/scripts/load.js` into a Windows path | `export MSYS_NO_PATHCONV=1` in `run_all.sh` |
| Stopped payment scored 55.8 instead of 0 | first E9 run | 2-min query window still held healthy pre-outage samples | `up_pct` query + `is_down()`; down service scored on availability only; unit test added |
| User efficiency 50 in E9 | first E9 run | Memory leaked in E8 was still held (reset only cleared the flag) | `run_all.sh` restarts all services before each scenario |
| Long scenario names broke the summary table | summary output | Fixed column width 14 | Width 24 |
| Shell script with CRLF endings | Windows editing | Python `write_text` on Windows | Converted to LF; `.gitattributes` `*.sh text eol=lf` |
All nine experiments were **re-run** after these fixes; the results above are from the clean run.

---

## 21. Limitations and Threats to Validity

1. **Compensability (open):** a linear weighted average lets perfect dimensions offset a critical one (E8: memory at 115 % → QI 91.8 Excellent; E5: 27 % errors → only Fair). Planned: cap QI (e.g. at the Poor/Critical band) when any dimension is critical; evaluate geometric aggregation.
2. **Attribution along the call chain (open):** in E5 the caller (order, weight 0.35) shares the blame for the dependency's (payment) errors. Planned: dependency-graph-aware attribution.
3. **Tail ratio at low traffic (open):** noisy when few requests (order scalability 67.7 in E1). Planned: minimum request rate before scoring scalability.
4. **Single runs:** each scenario run once; run-to-run variance unknown. Planned: ≥ 3 runs, mean ± SD.
5. **Lab environment:** one laptop, Docker Compose, synthetic in-memory services, no database, no network latency between hosts; results may differ in production Kubernetes clusters.
6. **Threshold choice:** good/bad limits are expert-chosen initial values, not calibrated per service; to be reviewed with the supervisor.
7. **Subjective AHP judgements:** weights reflect one set of judgements (consistent, CR 0.012); entropy/hybrid comparison planned.
8. **Memory limit with swap:** Docker Desktop allowed memory above the limit (swap), whereas Kubernetes would OOM-kill the container.
9. **Scalability proxy:** tail ratio approximates scalability; true elasticity tests (autoscaling) need Kubernetes.
10. **Baseline comparison:** only one static alert configuration so far.

---

## 22. Design Decisions and Rationale

| Decision | Rationale | Alternatives considered |
|---|---|---|
| Threshold-based (absolute) normalisation | Same score meaning in every run → deployments comparable over time | Min–max over observations (relative; changes when the data set changes) |
| Five dimensions from ISO/IEC 25010 + golden signals | Standard, defensible, runtime-observable | More dimensions (security, maintainability) — not runtime-measurable here |
| AHP as default weighting | Encodes expert priorities; consistency check; recommended in the outline | Fixed weights (arbitrary); entropy only (ignores business priorities) |
| Entropy + hybrid also implemented | Objective, data-driven check on the subjective weights | — |
| Median aggregation + IQR filter | Robust to scrape spikes and outliers | Mean (sensitive), EWMA (available as option) |
| Renormalise weights over available dimensions | Missing data ≠ bad quality (e.g. no traffic) | Treat missing as 0 (would falsely penalise idle services) |
| Down detection on the latest `up` sample | Avoid stale healthy data inflating a down service | Shorter lookback (noisier) |
| Tail ratio p99/p50 for scalability | Measurable at runtime without controlled load changes; rises under queueing | Throughput (low traffic is not bad quality); autoscaling metrics (need Kubernetes) |
| Throughput reported but not scored | Low traffic is not a quality defect | — |
| Business-criticality service weights for system QI | Order/payment failures matter more than user lookups | Equal weights |
| Loss-share attribution | Simple, explainable "who is to blame" | Root-cause analysis with traces (future) |
| Rule-based recommendations | Explainable, deterministic, easy to validate | ML-based (needs training data) |
| Node.js services | Small, fast startup, standard Prometheus client | Spring Boot (heavier; allowed by outline) |
| Docker Compose | Runs on one laptop; one command | Kubernetes (planned for scalability tests) |
| Pull from Prometheus (no agents) | Lightweight, non-intrusive, reuses existing monitoring | Sidecar agents |
| Publish QI back into Prometheus | QI appears in existing Grafana; enables alerting on QI | Separate UI |

---

## 23. Future Work (Second Half of the Semester)

1. **Repeated runs:** each scenario ≥ 3 times; report mean ± standard deviation.
2. **Weighting comparison:** fixed vs AHP vs entropy vs hybrid — rankings of scenarios and services.
3. **Non-compensatory rule:** cap the QI when any dimension is critical; review thresholds with the supervisor.
4. **Dependency-aware attribution:** use the service call graph to assign propagated errors to the failing dependency.
5. **Structured comparison with dashboard/alert monitoring:** detection rate, time to detect, correct identification of the responsible service.
6. **Kubernetes deployment with HPA:** evaluate scalability under real autoscaling.
7. **Literature:** add recent peer-reviewed work on QoS-based composite indices (supervisor advice).
8. Final report, demonstration and viva.

---

## 24. Running, Reproducing and Troubleshooting

### 24.1 Prerequisites
Docker Desktop, Python ≥ 3.10, Git; Node.js 22 only if running services without Docker.

### 24.2 Quick start
```bash
cd runtime-qaf
docker compose up -d --build                     # services, Prometheus, Grafana, QAF exporter
pip install -e "./qaf[dev]"                      # qaf CLI on the host
docker compose run --rm k6 run -e PROFILE=medium /scripts/load.js   # traffic (~5 min)
qaf assess                                       # in another terminal
```
Open http://localhost:3000 for the dashboard.

### 24.3 Reproduce all experiments
```bash
cd runtime-qaf
bash experiments/run_all.sh            # all E1–E9 (~55 min); or: bash experiments/run_all.sh E3 E9
qaf summarize experiments/results/E*.csv
qaf weights --csv experiments/results/E*.csv
```
Environment variables: `COOLDOWN` (60), `WARMUP` (75), `RECORD` (180), `INTERVAL` (15).

### 24.4 Regenerate report figures and report
```bash
cd runtime-qaf
python docs/mid-sem-report/make_figures.py      # figures + results_summary.json
cd docs/mid-sem-report && npm install && node build_report.js   # writes ../../../Stage4_Mid-Sem_Report.docx
```
(The submitted report additionally has its Contents page numbers filled in by WPS/Word and a title prefixed "QAF :".)

### 24.5 Tests
```bash
cd runtime-qaf/qaf && python -m pytest -q        # 17 passed
```

### 24.6 Troubleshooting
| Symptom | Fix |
|---|---|
| `docker` error "cannot find dockerDesktopLinuxEngine" | Start Docker Desktop |
| k6 "moduleSpecifier C:/Program Files/Git/scripts/load.js couldn't be found" | Use `MSYS_NO_PATHCONV=1` in Git Bash (already in `run_all.sh`) |
| `qaf assess` shows QI `-` / Unknown | No traffic yet or Prometheus not reachable; run a load test; check `QAF_PROMETHEUS_URL` |
| Script fails with `$'\r': command not found` | CRLF line endings; convert to LF |
| pytest "error during collection" | Run pytest from `runtime-qaf/qaf` (testpaths) |
| Stop everything | `docker compose down` in `runtime-qaf` |

---

## 25. Question-and-Answer Bank

**Q: What is this project in one sentence?**
A lightweight framework that converts many Prometheus runtime metrics of a microservice system into one Quality Index (0–100) per service and for the whole system, classifies it from Excellent to Critical, identifies the service causing degradation and recommends fixes.

**Q: Why is it needed if Grafana already has dashboards and alerts?**
Dashboards show metrics separately and alerts fire on single thresholds; neither gives an overall judgement, a comparable single number, or attribution. In experiments, static alerts stayed silent in 3 of 7 degraded scenarios while the QI flagged them.

**Q: What are the five dimensions and their weights?**
Performance 0.301, Reliability 0.265, Availability 0.186, Resource Efficiency 0.159, Scalability 0.089 (AHP).

**Q: Why AHP?**
It turns expert judgement into weights in a structured, checkable way (consistency ratio). CR = 0.012 < 0.10, so the judgements are consistent. It was recommended in the outline and praised in the supervisor's remarks.

**Q: How is the consistency ratio calculated?**
λmax = 5.0555 (principal eigenvalue); CI = (λmax − 5)/4 = 0.0139; CR = CI / RI = 0.0139 / 1.12 = 0.0124.

**Q: What is the Entropy Weight Method and is it used?**
An objective method that gives more weight to dimensions that vary more across observations (Shannon entropy). It is implemented (`method: entropy` and `hybrid`) and computed by `qaf weights --csv`; the formal comparison with AHP is planned.

**Q: How are different units combined?**
Each metric is normalised to 0–100 with a good and a bad threshold (linear in between, clamped). Then metrics are averaged into dimensions, and dimensions into the QI.

**Q: Why fixed thresholds instead of min–max normalisation?**
Min–max depends on the data set, so the same system could score differently in different runs. Fixed thresholds give scores a stable meaning and allow comparing deployments.

**Q: How is scalability measured?**
By the tail-latency ratio p99/p50. When a service saturates, requests queue and the slowest requests grow much faster than the median. Good ≤ 3, bad ≥ 15.

**Q: Why is throughput not part of the score?**
Low throughput (e.g. at night) is not a quality problem; it is recorded for context.

**Q: What happens with missing data?**
Missing metrics get no score and the weights are renormalised over available metrics/dimensions, so missing data does not pull the QI to zero.

**Q: What happens when a service is down?**
If its latest health (`up`) sample is 0, all other metrics are discarded and the QI equals the availability score → 0, Critical.

**Q: How does the framework decide which service is to blame?**
Loss share = w_s·(100 − QI_s) / Σ w_k·(100 − QI_k), with business weights order 0.35, payment 0.30, product 0.20, user 0.15. The largest share is the bottleneck.

**Q: How is the system QI computed?**
Business-weighted mean of service QIs (same weights as above).

**Q: What does the recommendation engine do?**
Applies explainable rules: availability < 99 % → probes/replicas; errors > 1 % → circuit breaker/retries; p95 > 500 ms → caching/query optimisation; CPU > 80 % → scale out; memory > 80 % → leak check; tail ratio > 10 → saturation, scale out.

**Q: What is the prototype?**
Four Node.js microservices (user, product, order, payment) with Prometheus instrumentation and fault injection; order calls the other three. Each runs in Docker with 0.5 CPU and 256 MB.

**Q: How were failures created?**
Through each service's `/chaos` endpoint (latency, error rate, CPU burn, memory leak) via `qaf chaos`, and by stopping a container (`docker compose stop payment`).

**Q: What were the main results?**
System QI: low 98.0, medium 98.5, peak 90.7, spike 93.3, payment errors 82.0, order latency 89.3, product CPU 92.9, user memory 97.3, payment outage 49.8. In each failure scenario the affected service had the lowest QI.

**Q: What is the most important finding?**
The QI detects degradations that single-metric alerts miss (peak, spike, CPU overload) and points to the responsible service; and it exposed real design issues (compensability, call-chain attribution).

**Q: What are the limitations?**
Compensability of weighted averages; attribution along call chains; noisy tail ratio at low traffic; single runs on one laptop; expert-chosen thresholds; Docker swap allowing memory over the limit; preliminary baseline comparison.

**Q: What is compensability and why does it matter here?**
In a weighted average, good scores can offset a very bad one. In E8 memory was 115 % of the limit, yet QI was 91.8 (Excellent). Fix planned: cap the QI when any dimension is critical.

**Q: Why did order get more blame than payment in E5?**
Order calls payment, so it shows the same error rate, and order has a higher business weight (0.35 vs 0.30). Dependency-aware attribution is planned.

**Q: Is the framework lightweight? How?**
It only queries Prometheus (10 queries per 15 s), has 4 Python dependencies, no agents inside services, no own database; it works with any service exposing standard Prometheus metrics.

**Q: Why Node.js and Docker Compose instead of Spring Boot and Kubernetes?**
Faster to build and run on one laptop; the outline allowed both. The framework is language-independent. Kubernetes with HPA is planned to test scalability properly.

**Q: How is the work validated/tested?**
17 unit tests (normalisation, weighting, consistency, entropy, outliers, classification, attribution, down detection) plus nine end-to-end experiments.

**Q: How long until a fault shows in the QI?**
About one minute (5 s scrape, 1-min rate window, assessment every 15 s, median over a 2-min lookback).

**Q: What was the plagiarism result of the mid-sem report?**
Turnitin overall similarity 4 % (no single source above 1 %), submitted 27 Sep 2026.

**Q: What remains to be done?**
Repeated runs, weighting comparison, non-compensatory rule, dependency-aware attribution, structured comparison with alerting, Kubernetes + HPA, literature extension, final report and viva (by 5 Nov 2026).

**Q: Where is the code and how do I run it?**
https://github.com/Gpalve848/QFA-V1-NOD; `cd runtime-qaf && docker compose up -d --build`, then `qaf assess` (Section 24).

**Q: What is novel compared with existing tools like Grafana SLO dashboards or APM health scores?**
The project combines (a) ISO 25010-based runtime dimensions, (b) consistency-checked AHP and entropy weighting, (c) a single explainable QI with levels, (d) service-level loss attribution and (e) rule-based recommendations, using only standard Prometheus metrics, and evaluates them experimentally with fault injection. (No commercial product was benchmarked yet.)

---

## 26. Repository Map

```
PROJECT-Main/                              (Git root; GitHub: Gpalve848/QFA-V1-NOD)
├── README.md                              this knowledge base
├── Stage1_Project-Outline.txt             Stage 1
├── Stage2_Abstract_report.pdf             Stage 2 (approved outline; student/supervisor details; plan)
├── Stage3_..._10_Slides.pptx              Stage 3 slides
├── Stage4_Mid-Sem_Report.docx / .pdf      Stage 4 mid-semester report
├── Sample_mid-sem-sample report.pdf       BITS template sample
└── runtime-qaf/
    ├── README.md                          technical quick start
    ├── docker-compose.yml                 full stack
    ├── services/                          Node.js microservices (src/common.js, user, product, order, payment)
    ├── qaf/                               Python framework
    │   ├── qaf/                           collector, preprocessing, scoring, weighting, recommender,
    │   │                                  engine, report, exporter, cli, config
    │   ├── config/qaf.yaml                model configuration
    │   └── tests/test_qaf.py              17 unit tests
    ├── monitoring/                        Prometheus config; Grafana datasource + dashboard
    ├── load-tests/load.js (+ results/)    k6 profiles and logs
    ├── experiments/                       protocol (README), run_all.sh, results/E1…E9 CSV
    └── docs/mid-sem-report/               make_figures.py, build_report.js, figures/, results_summary.json
```
Not in Git (local only): `Friend-sample-report.pdf` (another student's report, used only as a layout template) and the Turnitin similarity report PDF.

---

## 27. References

1. ISO/IEC 25010:2011, Systems and software Quality Requirements and Evaluation (SQuaRE) — System and software quality models.
2. T. L. Saaty, *The Analytic Hierarchy Process*, McGraw-Hill, 1980.
3. C. E. Shannon, "A Mathematical Theory of Communication," *Bell System Technical Journal*, 27(3), 379–423, 1948.
4. B. Beyer, C. Jones, J. Petoff, N. R. Murphy (eds.), *Site Reliability Engineering*, O'Reilly, 2016.
5. S. Newman, *Building Microservices*, 2nd ed., O'Reilly, 2021.
6. N. Dragoni et al., "Microservices: Yesterday, Today, and Tomorrow," in *Present and Ulterior Software Engineering*, Springer, 2017, 195–216.
7. B. Gregg, "Thinking Methodically about Performance," *Communications of the ACM*, 56(2), 45–51, 2013.
8. Prometheus documentation, https://prometheus.io/docs/
9. Grafana k6 documentation, https://grafana.com/docs/k6/
10. OECD & EC-JRC, *Handbook on Constructing Composite Indicators*, OECD Publishing, 2008.
11. T. Wilkie, "The RED Method: Key Metrics for Microservices Architecture," Grafana Labs blog, 2018.
12. J. Soldani, D. A. Tamburri, W.-J. van den Heuvel, "The Pains and Gains of Microservices: A Systematic Grey Literature Review," *JSS*, 146, 215–232, 2018.
13. O. Al-Debagy, P. Martinek, "A Metrics Framework for Evaluating Microservices Architecture Designs," *Journal of Web Engineering*, 19(3–4), 341–370, 2020.
14. V. C. Tapia, C. M. Gaona, "Research Opportunities in Microservices Quality Assessment: A Systematic Literature Review," *JAIT*, 14(5), 991–1002, 2023.
15. A. S. Abdelfattah, "Fostering Microservice Maintainability Assurance through a Comprehensive Framework," ICSME 2024 Doctoral Symposium, arXiv:2407.16873.
16. D. Taibi, K. Systä, "A Decomposition and Metric-Based Evaluation Framework for Microservices," arXiv:1908.08513, 2019.
17. Z. Zou, Y. Yun, J. Sun, "Entropy method for determination of weight of evaluating indicators in fuzzy synthetic evaluation for water quality assessment," *Journal of Environmental Sciences*, 18(5), 1020–1023, 2006.
18. N. Canbaz Horozlu, T. Serif, "A Multidimensional Decision-Support Framework for Software Quality Assessment in Agile Projects," *Information*, 17(7), 624, 2026, doi:10.3390/info17070624.

---

## 28. Project Completion Status and How to Present It

### 28.1 Is the project complete?
**No — and that is expected at mid-semester.** The approved plan runs until 5 November 2026. The first half (research, design, prototype, preliminary experiments) is complete; the second half (rigorous validation and improvements) remains.

| Part | Status | Approx. completion |
|---|---|---|
| Research (problem, gap, literature, objectives) | Done | 100 % |
| Framework design (model, formulas, AHP, levels) | Done | 100 % |
| Implementation (prototype, engine, dashboard, tests) | Done | ~90 % |
| Experiments | One run per scenario done | ~40 % |
| Comparison with traditional monitoring | Preliminary | ~30 % |
| Improvements found in testing | Planned | 0 % |
| Final report and viva | Pending | 0 % |
| **Overall** | | **≈ 60–65 %** |

By objectives: **5 of 7 completed, 2 in progress** (Section 3.4).

### 28.2 Recommended 15-minute presentation: "Done → Found → Next"
1. **Problem and idea (2 min):** monitoring shows dozens of separate metrics; nobody can tell at a glance if the system is healthy or which service is at fault. The framework combines them into one Quality Index 0–100.
2. **What has been done (5–6 min):** five completed deliverables — (1) quality model: 5 dimensions, 7 metrics, thresholds; (2) weighting: AHP, CR = 0.012, entropy and hybrid implemented; (3) working framework: all 5 modules, 17 tests passing; (4) prototype: 4 microservices, Prometheus, Grafana, fault injection, load tests on Docker; (5) preliminary experiments: 9 scenarios. Then the live demo (Section 29), or Grafana screenshot + `qaf assess` output as backup.
3. **What was found (3 min):** in every failure the right service was identified; in 3 of 7 degraded scenarios static alerts did not fire while the QI did. Then the self-found weaknesses: averaging hides emergencies (memory 115 % still "Excellent"), blame goes partly to the caller (E5), and the stale-data bug that was found and fixed (stopped service scored 55.8 instead of 0). Showing self-discovered problems demonstrates genuine research.
4. **What is left and the plan (3 min):**

| Remaining work | Why | When |
|---|---|---|
| Repeat each experiment ≥ 3 times | Statistical reliability | October, weeks 1–2 |
| Compare AHP vs entropy vs hybrid | Validate the weighting choice (objective 4) | October, week 2 |
| Fix "averaging hides emergencies" | Weakness found in E8 | October, week 2 |
| Dependency-aware blame | Weakness found in E5 | October, week 3 |
| Structured comparison with Grafana alerts | Objective 7; supervisor's request | October, week 3 |
| Kubernetes with autoscaling | Proper scalability testing | October, week 4 |
| Final report and viva | Submission | 20 Oct – 5 Nov |

Closing line: *"The framework is built and working; the second half is about validating it rigorously and improving the weaknesses my experiments revealed."*

### 28.3 Phrases to use and avoid

| Say | Avoid |
|---|---|
| "As per my plan, the design and prototype phases are complete." | "I haven't finished." |
| "These are **preliminary** results from single runs." | Presenting single-run numbers as final proof |
| "My experiments **revealed** two limitations, which I'll address next." | Hiding the weaknesses |
| "Experimentation is **in progress**." | "I didn't have time." |
| "This is a planned next step." | Claiming features that do not exist yet |

**If asked "Why isn't it complete?":** "According to the approved plan, mid-semester covers design and prototype development, which are complete. Experimentation is in progress, and the remaining work — repeated runs, comparisons and improvements — is scheduled for the second half, finishing by 5 November."

**Timeline caution:** the abstract's plan ends experimentation on 4 October. If asked: "Preliminary experiments were completed on schedule; they revealed design issues, so I extended validation to include improvements and repeated runs, still within the 5 November deadline." Agree the revised timeline with the supervisor.

---

## 29. Live Demo Script (Windows + VS Code)

### 29.1 One-time preparation (the day before)
- **Docker Desktop** installed and able to start.
- **Python** with the `qaf` CLI: `pip install -e ".\qaf[dev]"` from `runtime-qaf` (once).
- **VS Code** installed.
- Internet for the **first** build only (Docker downloads Prometheus, Grafana, k6 images, ~1 GB).
- Build everything once before demo day (first build 5–10 min; later starts take seconds).
- Rehearse the full demo once, timing each step.

### 29.2 Starting up on demo day
1. **Start Docker Desktop** (Start menu → Docker Desktop) and wait for **"Engine running"** (~1 min).
   - If you see `error during connect … open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`, Docker Desktop is **not running** — start it, wait, and repeat the command.
2. **Open VS Code → File → Open Folder…** → `C:\Users\ganes\OneDrive\Desktop\Mtech-project\PROJECT-Main`.
3. **Terminal → New Terminal** (Ctrl + `) — PowerShell.
4. Start the stack:
   ```powershell
   cd runtime-qaf
   docker compose up -d --build
   docker compose ps          # 7 containers Up: user, product, order, payment, prometheus, grafana, qaf
   ```
5. Open browser tabs: **Grafana** http://localhost:3000 (dashboard "Runtime Quality Assessment – Overview" opens directly, no login) and **Prometheus** http://localhost:9090/targets (all services UP).
6. Start traffic in a **second terminal** (click **+** in the terminal panel), 25 users for 20 minutes:
   ```powershell
   cd runtime-qaf
   docker compose run --rm k6 run -e PROFILE=medium --stage 30s:25 --stage 20m:25 /scripts/load.js
   ```
   Wait ~1 minute; Grafana fills in and everything shows **Excellent** (QI ≈ 98).

### 29.3 Demo storyline (10–12 minutes)
| # | Step | Command / action | Expected result |
|---|---|---|---|
| 1 | The problem (1 min) | Show Grafana's lower panels (latency, errors, CPU, memory) | "Many separate numbers — is it healthy? who is at fault?" |
| 2 | The solution (1 min) | Grafana top panels; `qaf assess` | One QI ≈ 98, Excellent; table with dimensions, QI, level, loss share, recommendations |
| 3 | AHP weights (1 min) | `qaf weights` | 0.301 / 0.265 / 0.186 / 0.159 / 0.089; CR 0.0124 → consistent |
| 4 | Payment errors (3 min) | `qaf chaos payment --error-rate 0.3`, wait ~60 s, `qaf assess` | Payment and Order ≈ 72 (Fair), reliability 0, CRITICAL reliability → circuit breaker; Grafana turns yellow/orange. Reset: `qaf chaos payment --reset` |
| 5 | Slow service (2 min) | `qaf chaos order --latency 800`, wait, `qaf assess` | Order performance 0, QI ≈ 70 (Fair), caching recommendation. Reset: `qaf chaos order --reset` |
| 6 | Service crash (2 min) | `docker compose stop payment`, wait 30–60 s, `qaf assess` | Payment **0, Critical**; Order Poor; system ≈ 50 (Poor); Grafana red. Restore: `docker compose start payment` |
| 7 | Key result (1 min) | Open `Stage4_Mid-Sem_Report.pdf`, Section 5.6 | 3 of 7 degraded scenarios: no static alert, but QI caught it and named the service |
| 8 | Code quality (1 min) | `cd qaf`, `python -m pytest -q`, `cd ..`; show folders in Explorer | 17 passed; `services/`, `qaf/qaf/`, `qaf/config/qaf.yaml` |

### 29.4 Shutting down
Second terminal: **Ctrl + C** (stops k6). First terminal: `docker compose down`.

### 29.5 Demo tips
- **Expect ~1 minute delay** after injecting a fault (1-min rate window, 2-min median lookback). Say: "It averages over a window so short spikes don't cause false alarms."
- **Always reset faults** between demos.
- **Backup plan:** if Docker fails, show the report figures and the real CSV results in `experiments/results/`.
- **Close heavy apps** before the demo; Docker plus load testing uses a lot of CPU on this laptop.

---

## 30. Explaining the AHP Output to an Examiner

### 30.1 The output
```
  performance  0.301
  reliability  0.265
  availability 0.186
  efficiency   0.159
  scalability  0.089
  lambda_max=5.0555  CI=0.0139  CR=0.0124  -> consistent (CR < 0.10)
```

### 30.2 One-line answer
> "These are the weights of the five quality dimensions in my Quality Index formula. I derived them with AHP from pairwise comparisons, and the consistency ratio of 0.012 shows my comparisons are logically consistent, because it is well below Saaty's limit of 0.10."

### 30.3 What each line means
| Output | Meaning |
|---|---|
| performance 0.301 | Performance contributes 30.1 % of the QI |
| reliability 0.265 | Reliability (error rate) 26.5 % |
| availability 0.186 | Availability (uptime) 18.6 % |
| efficiency 0.159 | CPU and memory use 15.9 % |
| scalability 0.089 | Scalability (queueing) 8.9 % |
| weights sum to 1.0 | So the QI stays between 0 and 100 |

They are used directly in **QI = 0.301·P + 0.265·R + 0.186·A + 0.159·E + 0.089·S**.

### 30.4 How AHP produced them
**Step 1 — pairwise comparisons** on Saaty's 1–9 scale (1 = equal, 3 = moderately more important, 9 = extremely more important); matrix in Section 8.2. The lower half holds reciprocals (Availability vs Performance = 1/2).

**Step 2 — weights.** The program uses the **principal eigenvector** (normalised). Hand check with the **geometric-mean method**:

| Row | Product of row | 5th root | Weight (÷ 5.434) |
|---|---|---|---|
| Performance | 1·1·2·2·3 = 12 | 1.644 | 0.303 |
| Reliability | 1·1·1·2·3 = 6 | 1.431 | 0.263 |
| Availability | ½·1·1·1·2 = 1 | 1.000 | 0.184 |
| Efficiency | ½·½·1·1·2 = 0.5 | 0.871 | 0.160 |
| Scalability | ⅓·⅓·½·½·1 = 1/36 | 0.488 | 0.090 |
| | | sum = 5.434 | |

These match the program's eigenvector weights; small differences are expected.

**Step 3 — consistency.**

| Value | Formula | Result | Meaning |
|---|---|---|---|
| λmax | Largest eigenvalue | 5.0555 | Perfectly consistent 5×5 matrix would give exactly 5 |
| CI | (λmax − n)/(n − 1) = (5.0555 − 5)/4 | 0.0139 | Distance from perfect consistency |
| RI | Saaty's random index, n = 5 | 1.12 | Average CI of random matrices |
| CR | CI / RI = 0.0139 / 1.12 | 0.0124 | ≈ 1.2 % as inconsistent as random judgements |

Rule: **CR < 0.10 is acceptable**; 0.0124 is far below. Quick λmax check with the Performance row: (1·0.301 + 1·0.265 + 2·0.186 + 2·0.159 + 3·0.089) ÷ 0.301 = 1.523 ÷ 0.301 ≈ 5.06.

### 30.5 Why this order of importance
| Rank | Dimension | Justification |
|---|---|---|
| 1 | Performance | Users notice slowness first; latency is the first golden signal |
| 2 | Reliability | Failed requests (e.g. failed payment) lose business directly |
| 3 | Availability | Critical, but outages are rarer and overlap with reliability |
| 4 | Efficiency | High CPU/memory is a warning sign, not yet a user-visible failure |
| 5 | Scalability | Predictor of future problems under load |

Close to the outline's intuitive 30/25/20/15/10 split; AHP made it consistent and justifiable.

### 30.6 Follow-up questions
- **"Aren't the weights subjective?"** — Yes, expert-based; that is why consistency is checked. The Entropy Weight Method (objective) and a hybrid are implemented; their comparison is second-half work.
- **"What if CR > 0.10?"** — The judgements would be inconsistent and must be revised until CR < 0.10; a unit test checks detection of an inconsistent matrix.
- **"Why not equal weights?"** — Equal weights would treat a CPU warning like failed payments; AHP encodes business priorities.
- **"Can weights be changed?"** — Yes; edit `ahp_matrix` in `qaf.yaml`; weights and CR are recomputed automatically.
- **"What is RI?"** — Saaty's Random Index, the average CI of randomly generated matrices of the same size; 1.12 for n = 5.

Tip: show `runtime-qaf/qaf/config/qaf.yaml` (`ahp_matrix`) in VS Code to prove the weights come from a visible, editable matrix.

---

## 31. Connecting Additional Services to the Framework

### 31.1 Principle
The framework never talks to services directly; it reads everything from Prometheus:
```
Your service ──/metrics──► Prometheus ──PromQL──► QAF engine ──► QI, level, blame, recommendations
```
Adding a service needs **no framework code change** — three things: the service exposes metrics, Prometheus scrapes it, QAF config lists it.

### 31.2 Step 1 — the service exposes the expected metrics
| Metric | Type | Labels | Used for |
|---|---|---|---|
| `http_request_duration_seconds` | histogram (with buckets) | service, status, route, method | p50/p95/p99 and mean latency |
| `http_requests_total` | counter | service, status | throughput, 5xx error rate |
| `process_cpu_seconds_total` | counter | service | CPU % |
| `process_resident_memory_bytes` | gauge | service | memory % |

For Node.js, reuse `services/src/common.js`:
```js
const { createService } = require('./common');
const { app, start } = createService('inventory');   // sets label service="inventory"
app.get('/stock/:id', (req, res) => res.json({ id: req.params.id, qty: 42 }));
start(3005);
```
Other languages: standard Prometheus client libraries (prom-client, prometheus_client for Python, Micrometer for Java — see limitations).

### 31.3 Step 2 — Prometheus scrapes it (`monitoring/prometheus/prometheus.yml`)
```yaml
  - job_name: microservices
    honor_labels: true
    static_configs:
      # ...existing user/product/order/payment...
      - targets: ["inventory:3005"]
        labels: { service: inventory }
```
The `service` label is what QAF groups by; it also gives the `up` series (availability) its service name.

### 31.4 Step 3 — QAF knows about it (`qaf/config/qaf.yaml`)
```yaml
services:
  inventory: { url: http://localhost:3005, weight: 0.10 }
```
`weight` = business importance in the system QI (renormalised, need not sum to 1); `url` only for `qaf chaos`.

### 31.5 Step 4 — run and verify
Add it to `docker-compose.yml` (same 0.5 CPU / 256 MB limits), then:
```bash
docker compose up -d --build inventory
docker compose restart prometheus qaf
qaf assess
```
http://localhost:9090/targets must show it **UP**; after a minute of traffic it appears in `qaf assess` and Grafana.

### 31.6 Monitoring existing services (e.g. at the organisation)
If services are already scraped by an existing Prometheus, skip steps 1–2: set `QAF_PROMETHEUS_URL=http://your-prometheus:9090`, set `job:` in `qaf.yaml`, and make sure each series has a `service` label (rename e.g. `app` with a relabel rule). On Kubernetes, replace static targets with `kubernetes_sd_configs` so new pods are discovered automatically.

### 31.7 Current limitations for arbitrary services (candidate second-half improvements)
1. **Metric names are hard-coded** in `collector.py`. Spring Boot (Micrometer) uses `http_server_requests_seconds_bucket` and `process_cpu_usage` (a ratio), so a Spring Boot service would currently get no latency/CPU scores. Fix: query presets per technology (nodejs, spring-boot, python) in `qaf.yaml`.
2. **Resource limits are global** (`resources`: 0.5 CPU / 256 MB for all). Fix: per-service limits or read from `kube_pod_container_resource_limits`.
3. **Unlisted services get weight 1.0** in the system QI (≈ 3× order's 0.35), distorting it. Fix: default to the mean weight or score only listed services.
4. **Static targets** must be edited by hand. Fix: Kubernetes service discovery.

---

## 32. Beginner's Guide: The Whole Project Explained from Zero

### 32.1 The world this project lives in
**Microservice.** Instead of one big program, a company splits its application into many small programs, each doing one job. Our demo shop has User (customers), Product (prices), Payment (charging) and Order (checkout, which calls the other three). If any one is slow or broken, a purchase suffers.

**Metric.** A measurement taken repeatedly while the program runs — like a hospital patient's vital signs:

| Hospital patient | Microservice |
|---|---|
| Heart rate | Response time |
| Blood pressure | CPU usage |
| Temperature | Memory usage |
| Is the patient conscious? | Is the service up (available)? |
| Failed breaths | Failed requests (errors) |

### 32.2 What already existed vs what we built
**Existing free tools (used, not built):**

| Tool | What it is | Analogy |
|---|---|---|
| Prometheus | Visits every service every 5 s, collects its numbers, stores them with timestamps | Machine recording vital signs |
| Grafana | Draws charts from Prometheus data | Screens showing the graphs |
| Docker | Runs each service in an isolated container with limits (0.5 CPU, 256 MB) | Separate hospital rooms |
| k6 | Creates fake customers (5 to 150) to load the system | Treadmill stress test |
| prom-client | Library inside each service that counts and times requests | Sensors on the patient |

The gap: Grafana shows dozens of separate graphs, Prometheus has the data, but **nobody says what it means** — a hospital screen full of numbers with **no doctor**.

**What we built:**

| Built by us | Language | Purpose |
|---|---|---|
| 4 demo services | Node.js | Realistic test system that can be made "sick" on purpose (fault injection) |
| **QAF framework** (research contribution) | Python | **The doctor**: reads Prometheus, judges the data, gives one health score (QI) |
| Grafana dashboard | Configuration | Shows the QI in green/yellow/red |
| Experiments | Script | 9 scenarios: normal, busy, and different "illnesses" |

### 32.3 The journey of the data
```
 4 services ──► Prometheus ──► OUR FRAMEWORK: collect → clean → score → combine → recommend ──► QI + advice
 (produce        (collects,                                                                        (terminal,
  numbers)        stores)                                                                           Grafana, CSV)
```
- **Step 0 — services produce numbers** (existing library): each request's duration and success; CPU and memory; exposed at e.g. `http://localhost:3001/metrics`.
- **Step 1 — collection:** Prometheus scrapes every 5 s; our **M1 Collector** asks Prometheus every 15 s for the last 2 minutes per service using **PromQL** (e.g. "the time below which 95 % of requests finish").
- **Step 2 — cleaning (M2):** throw away crazy spikes (outliers); take the **median** of the 2 minutes; treat missing data as "unknown", not 0; if a service is down *right now*, ignore its old healthy numbers.
- **Step 3 — scoring (M3):** each of the **7 metrics** becomes a 0–100 score; grouped into **5 dimensions**.
- **Step 4 — combining (M4):** weighted sum → **QI**; level; system QI; blame.
- **Step 5 — advice (M5):** rules → recommendations.

### 32.4 The 7 metrics and 5 dimensions in plain words
| # | Metric | Plain meaning |
|---|---|---|
| 1 | p95 response time | 95 % of customers got an answer faster than this — captures the slow experiences |
| 2 | Average response time | Typical speed |
| 3 | Error rate | % of requests that failed |
| 4 | Availability | % of time the service was alive |
| 5 | CPU usage | % of allowed processor power used |
| 6 | Memory usage | % of allowed memory used |
| 7 | Tail ratio | Slowest ÷ typical requests; growing = requests waiting in a queue (overload) |

| Dimension | Question it answers | Metrics |
|---|---|---|
| Performance | Is it fast? | #1 (60 %) + #2 (40 %) |
| Reliability | Does it work correctly? | #3 |
| Availability | Is it alive? | #4 |
| Efficiency | Does it use resources sensibly? | #5 (50 %) + #6 (50 %) |
| Scalability | Can it handle more load? | #7 |

**Normalisation** works like exam marks: different subjects are converted to marks out of 100 so they can be added. Between the good and bad limits (Section 7.1) the score falls in a straight line — e.g. p95 = 550 ms is halfway between 100 and 1000 ms → score 50.

### 32.5 Worked example from the experiments (E3, 100 users, Order service)
| Dimension | Score | × Weight | = Points |
|---|---|---|---|
| Performance | 49.3 (p95 696 ms) | × 0.301 | 14.8 |
| Reliability | 100 (no errors) | × 0.265 | 26.5 |
| Availability | 100 | × 0.186 | 18.6 |
| Efficiency | 82.2 (CPU 57 %) | × 0.159 | 13.1 |
| Scalability | 14.1 (heavy queueing) | × 0.089 | 1.3 |
| **QI** | | | **74.2 → Fair** |

### 32.6 AHP, entropy and hybrid in plain words
- **AHP — "ask an expert, in pairs".** Ranking five things at once is hard; comparing two at a time is easy ("Performance vs Scalability? Performance, 3 times"). The 5×5 table of answers is turned into weights by an eigenvector. The **consistency ratio** checks for self-contradiction (A > B, B > C, but C > A); it must be < 0.10, ours is 0.012. Strength: reflects business priorities. Weakness: based on human opinion.
- **Entropy Weight Method — "let the data decide".** A dimension that changes a lot between services or situations carries more information and gets more weight; one that is always the same gets little weight (e.g. availability always 100 % → low weight; performance varying a lot → high weight). Strength: objective. Weakness: ignores business importance (availability could get a tiny weight just because nothing crashed during the test).
- **Hybrid — "best of both".** Weight = 50 % AHP + 50 % entropy.

| Method | Who decides | Status |
|---|---|---|
| AHP | Expert | Implemented, **used for all results** |
| Entropy | Data | Implemented; comparison planned |
| Hybrid | Both | Implemented; comparison planned |

### 32.7 What the index is used for
| Use | Example |
|---|---|
| Instant health check | "System 98, Excellent" instead of reading 40 graphs |
| Find the culprit | "Payment QI 0, Critical; it causes most of the loss" |
| Catch hidden problems | Under 100 users no alarm fired, yet QI dropped to Fair (3 of 7 degraded scenarios) |
| Compare deployments | "Version 2 has QI 91, version 1 had 96 — the release made things worse" |
| Track trends | Daily/weekly QI shows improvement or degradation |
| Simpler alerting | One rule "QI < 60" instead of dozens of metric rules |
| Guide the fix | Recommendations point to the likely type of fix |
| Management reporting | "Quality 95/100" understood without technical knowledge |

The QI is visible in three places: the terminal (`qaf assess`), the Grafana dashboard (the framework publishes the QI back into Prometheus), and CSV files (`qaf record`).

### 32.8 The whole project in 30 seconds
> "Companies run software as many small services. Tools like Prometheus collect dozens of numbers about them, and Grafana draws graphs — but nobody combines them into an answer. I built a framework that acts like a doctor: it collects 7 metrics from Prometheus, cleans them, converts each to a 0–100 score, groups them into 5 dimensions — performance, reliability, availability, efficiency, scalability — and combines them with weights decided by AHP into one Quality Index. It labels health from Excellent to Critical, finds which service is to blame, and suggests fixes. I tested it on 4 demo services with 9 scenarios, and it caught problems that normal alerts missed."

---

## 33. Mid-Semester Submission and Plagiarism Check

- **Submission:** the mid-semester report was uploaded on the BITS portal (S1-26_DISSERTATION – MID SEM) on **27 Sep 2026, 12:56 AM IST**: 27 pages, 6,022 words, title prefixed "QAF :".
- **Turnitin similarity: 4 % overall** — 3 % internet sources, 1 % publications, 1 % student papers; 17 sources, **none above 1 %**; bibliography and quoted text excluded. Matches are scattered standard phrases (e.g. "Analytic Hierarchy Process"), no copied passages. The report contains no AI-writing score.
- **Is a plagiarism report mandatory at mid-semester?** Not found as a requirement in BITS guidelines; the **Originality Similarity Index (OSI) report is required with the final report** before the final presentation. BITS provides **DrillBit** (via the library/supervisor). Confirm current-semester rules in the SEZG628T course handout or with the supervisor.
- **Mid-semester evaluation sheet:** usually filled and signed by the supervisor and uploaded with the report — check the course page.
- The Turnitin PDF is kept locally (`2024tm93686_Mid.pdf`) and excluded from Git (contains the submission ID).
- **Note on authorship:** report text was drafted with AI assistance from the student's own design, code and results; check the programme's policy on AI-assisted writing and be able to explain every part in the viva.
