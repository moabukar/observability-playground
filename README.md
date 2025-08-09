# Observability Playground (o11y)

Stack: Prometheus, Grafana, Loki, Alertmanager, Tempo, OTEL Collector and a FastAPI app with metrics/logs/traces.

## Run

```bash
make up
make load                 # generate some traffic
make open                 # open Grafana (no auth)

## Fault drills
make fault-err            # introduce 50% errors
make load
make fault-latency        # +500ms latency
make load
make fault-ok             # reset faults
```

- Prometheus: http://localhost:9090

- Grafana: http://localhost:3000 (dashboards auto-provisioned)

- Alerts: Alertmanager http://localhost:9093

- Logs: Loki via Grafana Explore

- Traces: Tempo via Grafana Explore

## What to do next

```bash
curl -s http://localhost:8080/health           # {"ok":true}
curl -s http://localhost:8080/work | jq .       # should return {"ok":true,...}


## Metrics visible?

# Prom targets UP?
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job:.labels.job, health:.health}'
# App metrics endpoint (scraped by Prometheus):
curl -s http://localhost:8080/metrics | head

```

## Incident tickets (examples)

- HighErrorRate firing. Find culprit, link logs + traces, propose a rollback.

- HighLatencyP95 firing. Identify endpoint /work, show trace waterfall & histograms.

- AppDown fired during chaos kill. Validate SLO impact, build runbook step.

## Clean

```bash
make down
make reset
```
---

### Notes / edge cases covered

- Logs are **explicitly written** to `./data/logs/*.log` -> Promtail scrapes reliably on Docker Desktop (no `/var/lib/docker/containers` mount drama).
- Traces use **OTLP → Collector → Tempo** (Grafana can Explore traces immediately).
- Metrics are native Prometheus client; histogram supports pXX queries.
- Faults are toggled **at runtime** via HTTP; no restarts needed.
- Dashboards & datasources are **pre-provisioned** (no clicking around).
- Alerts are simple but actionable; `make alerts` hot-reloads Prometheus.

