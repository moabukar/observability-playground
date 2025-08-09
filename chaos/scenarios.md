# Chaos scenarios

## Kill app for 30s
docker run --rm -it --network host gaiaadm/pumba:0.8.0 pumba --log-level info kill --signal SIGKILL --duration 30s re2:^app$

## Add 500ms latency on egress
docker run --rm -it --network host --privileged gaiaadm/pumba:0.8.0 pumba netem --duration 60s delay --time 500 re2:^app$

(then watch alerts/dashboards recover)
