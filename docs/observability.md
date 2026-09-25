# Observability

## What the role does

1. Creates the `observability` Docker network (`observability_subnet`),
   outside Compose, so Dokku apps can join it and `docker compose down`
   can't remove it while they're attached.
2. Writes a Compose project to `/opt/observability` and starts it:

   | Service | Purpose |
   |---|---|
   | Prometheus | Metrics, kept for `observability_prometheus_retention` |
   | Loki | Logs, kept for `observability_loki_retention` |
   | Alloy | Ships container logs, Dokku's nginx access logs, `/var/log/fail2ban.log` and the journal units in `observability_journal_units` |
   | node-exporter | Host metrics |
   | cAdvisor | Per-container CPU, memory and network |
   | blackbox-exporter | Probes `https://<domain>/healthz` for every Dokku app domain |

   A service restarts when its config file changes.
3. Reads the Dokku apps and their domains on every run and writes them
   to the probe list. Run the role again after adding an app or a domain.
4. Defines a `dokku_json` nginx log format and makes it Dokku's global
   access log format, so every app's access log is one JSON object per
   request: status, path (without the query string), `request_time` and
   upstream time.

Nothing is published on the host except node-exporter, which listens on
the network's gateway address (`observability_gateway:9100`). One ufw rule
lets the network reach it.

## Labels

Logs:

| Label | Value |
|---|---|
| `job` | `docker`, `nginx`, `journal` or `fail2ban` |
| `app`, `process_type` | From Dokku's container labels, and `app` from the nginx log's file name |
| `container`, `stream` | Container name, `stdout` or `stderr` |
| `unit` | systemd unit, for journal entries |

Paths, IDs and users stay in the log line. Parse the JSON at query time:

```logql
{job="nginx", app="myapp"} | json | status >= 500
```

## Adding an app's metrics

Prometheus scrapes any container on the `observability` network that has an
`observability.metrics.port` label, at `http://<container>:<port>/metrics`,
and labels its series with `app` and `process_type`. Don't map that port
with `ports:add`: Dokku's nginx would make it public.

```bash
dokku docker-options:add myapp deploy "--label observability.metrics.port=9000"
dokku network:set myapp attach-post-deploy observability
dokku ps:rebuild myapp
```

## Looking at it before Grafana

On the server:

```bash
docker run --rm --network observability curlimages/curl -s http://prometheus:9090/api/v1/targets
docker run --rm --network observability curlimages/curl -s http://loki:3100/loki/api/v1/labels
```
