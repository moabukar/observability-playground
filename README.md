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

## Service URLs

- App: http://localhost:8080
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (dashboards auto-provisioned)
- Alertmanager: http://localhost:9093
- Tempo: http://localhost:3200
- Logs: Loki via Grafana Explore
- Traces: Tempo via Grafana Explore

## Testing workflow

```bash
# Check service status
docker compose ps
# Expected: All services should show "Up" status

# Check service health
curl -s http://localhost:8080/health | jq .
# Expected: {"ok":true}

# Check Prometheus targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job:.labels.job, health:.health}'
# Expected: Both "app" and "prometheus" jobs should show "health": "up"

# Check Grafana datasources
curl -s http://localhost:3000/api/datasources | jq '.[].name'
# Expected: ["Loki", "Prometheus", "Tempo"]

# Verify app metrics endpoint
curl -s http://localhost:8080/metrics | head -10
# Expected: Prometheus metrics output starting with "# HELP"
```

## Gen traffic

```bash
make load

### or 

# Create some baseline requests for comparison
for i in {1..20}; do 
  curl -s http://localhost:8080/work > /dev/null
  sleep 0.1
done

# Check baseline metrics
curl -s http://localhost:8080/metrics | grep "app_requests_total"
# Expected: Should show counters for route="/work" status="200"
```

## 🚨 Test Scenario 1: High Error Rate Alert

```bash
# Set 50% error rate
curl -sS -XPOST "http://localhost:8080/faults/error?rate=0.5" | jq .
# Expected: {"ERROR_RATE": 0.5}

# Generate traffic to trigger errors
echo "Generating requests with 50% error rate..."
for i in {1..50}; do 
  curl -s http://localhost:8080/work
  sleep 0.1
done
```

## Step 2: Verify Metrics Show Errors

```bash
# Check error metrics
curl -s http://localhost:8080/metrics | grep "app_requests_total.*500"
# Expected: Should show non-zero counter for status="500"

# Check error rate in Prometheus
curl -s 'http://localhost:9090/api/v1/query?query=rate(app_requests_total{status="500"}[1m])' | jq '.data.result[0].value[1]'
# Expected: Should show error rate > 0
```

## Check logs for error messages

```bash
# Check recent error logs
tail -20 data/logs/app.log | grep ERROR
# Expected: Multiple "processing failed" error messages

# Or check in Grafana:
echo "🔍 In Grafana Explore:"
echo "1. Go to http://localhost:3000/explore"
echo "2. Select 'Loki' datasource"
echo "3. Query: {service=\"app\"} |= \"ERROR\""
echo "4. Should see error log entries"
```

## Check Error Traces

```bash
# Check OTEL collector is processing traces
docker compose logs otel-collector --tail=10 | grep TracesExporter
# Expected: Should see recent trace exports

echo "🔍 In Grafana Explore - Traces:"
echo "1. Go to http://localhost:3000/explore"
echo "2. Select 'Tempo' datasource"
echo "3. Search by: Service Name = 'app'"
echo "4. Look for traces with error status (red indicators)"
echo "5. Click on error traces to see span details"
```

## Check alertmanager

```bash
# Check if alert is firing (may take 1-2 minutes)
curl -s http://localhost:9093/api/v1/alerts | jq '.data[] | select(.labels.alertname=="HighErrorRate")'
# Expected: Should show firing alert when error rate threshold exceeded

echo "🔍 In Alertmanager UI:"
echo "1. Go to http://localhost:9093"
echo "2. Should see 'HighErrorRate' alert in firing state"
echo "3. Check alert details and labels"
```

## Reset and Verify Recovery

```bash
# Reset faults
curl -sS -XPOST "http://localhost:8080/faults/reset" | jq .
# Expected: {"ERROR_RATE": 0.0, "EXTRA_LATENCY_MS": 0}

# Generate healthy traffic
for i in {1..20}; do 
  curl -s http://localhost:8080/work > /dev/null
  sleep 0.1
done

# Verify error rate dropped
curl -s 'http://localhost:9090/api/v1/query?query=rate(app_requests_total{status="500"}[1m])' | jq '.'
# Expected: Error rate should approach 0
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
