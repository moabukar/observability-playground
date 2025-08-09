SHELL := /bin/bash

.PHONY: up down reset logs open fault-ok fault-err fault-latency load alerts demo

up:
	docker compose up -d --build
	@echo "Grafana: http://localhost:3000  • Prometheus: http://localhost:9090  • Loki: http://localhost:3100  • AM: http://localhost:9093"

down:
	docker compose down -v

reset: down
	rm -rf data/logs/* || true

logs:
	docker compose logs -f app

open:
	open http://localhost:3000 || xdg-open http://localhost:3000 || true

# Fault toggles
fault-ok:
	curl -sS -XPOST "http://localhost:8080/faults/reset" | jq .

fault-err:
	# set error rate to 0.5 (50%)
	curl -sS -XPOST "http://localhost:8080/faults/error?rate=0.5" | jq .

fault-latency:
	# add 500ms latency
	curl -sS -XPOST "http://localhost:8080/faults/latency?ms=500" | jq .

# quick synthetic load (curl loop)
load:
	@echo "Hitting /work 50x…"
	for i in $$(seq 1 50); do curl -sS -o /dev/null -w "%{http_code}\n" http://localhost:8080/work; sleep 0.1; done

alerts:
	@echo "Reloading Prometheus config…"
	curl -s -X POST http://localhost:9090/-/reload || true

demo: up fault-err load
