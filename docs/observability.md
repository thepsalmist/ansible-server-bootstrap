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
   | Tempo | Traces, kept for `observability_tempo_retention` |
   | Alloy | Ships container logs, Dokku's nginx access logs, `/var/log/fail2ban.log` and the journal units in `observability_journal_units`. Receives apps' OTLP traces and metrics and forwards them to Tempo and Prometheus |
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
lets the network reach it. Alloy's OTLP ports, 4317 (gRPC) and 4318 (HTTP),
are only reachable on the `observability` network.

## Grafana

Set `observability_grafana_domain` and `observability_grafana_admin_password`
in `group_vars/all.yml` and the role deploys Grafana as the Dokku app
`grafana`:

- `git:from-image grafana/grafana:<observability_grafana_version>`. Bumping
  the version redeploys it.
- Data in `/var/lib/dokku/data/storage/grafana`, so users and settings
  survive rebuilds and upgrades.
- Datasources (Prometheus as the default, Loki, Tempo) and dashboards come
  from `/opt/observability/grafana`, mounted read-only. They can't be edited in
  the UI; change them here and re-run. Dashboards are in two folders:

  | Folder | Dashboard | Shows |
  |---|---|---|
  | Overview | Server (the home page) | CPU, memory, disk and load at a glance, then host graphs and the busiest containers |
  | Overview | Apps | Per app: health check, certificate, requests and server errors, processes reporting; requests and p95 response time by page, and other requests, from the app's metrics; requests by status and response time from nginx; containers; log lines by level and logs. nginx figures exclude health-check probes |
  | Details | Server details (Node Exporter Full) | Every host metric, from grafana.com |

  Each has a Dashboards link to the others. The overviews' JSON is in
  `roles/observability/files/dashboards/Overview/`.
- A JSON log line with a `trace_id` field gets a View trace link to Tempo,
  and a trace links to its logs: the `app` matching the trace's
  `service.name`, filtered on the trace ID.
- The domain, `http:80:3000`, and Let's Encrypt when
  `dokku_letsencrypt_email` is set. The DNS record has to point at the
  server before the first run, or the certificate request fails.
- Sign-up and anonymous access off. After five wrong passwords in a row,
  Grafana blocks that user for five minutes, and a fail2ban jail bans an
  address after five failed logins in ten minutes, for an hour.

Keep the password out of plain text with
`ansible-vault encrypt_string --name observability_grafana_admin_password`
and run with `--ask-vault-pass`.

The admin password only applies when Grafana first creates its database.
To change it afterwards:

```bash
dokku enter grafana web grafana cli admin reset-admin-password '<new password>'
```

then update the variable to match.

## Labels

Logs:

| Label | Value |
|---|---|
| `job` | `docker`, `nginx`, `journal` or `fail2ban` |
| `app`, `process_type` | From Dokku's container labels, and `app` from the nginx log's file name |
| `container`, `stream` | Container name, `stdout` or `stderr` |
| `unit` | systemd unit, for journal entries |

Metrics pushed over OTLP:

| Label | Value |
|---|---|
| `app` | The resource's `service.name` |
| `process_type`, `deployment_environment` | The `process_type` and `deployment.environment` resource attributes |
| `job`, `instance` | `service.name` (prefixed with `service.namespace/` when set) and `service.instance.id`, Prometheus's defaults |

Paths, IDs and users stay in the log line. Parse the JSON at query time:

```logql
{job="nginx", app="myapp"} | json | status >= 500
```

## Sending an app's traces and metrics

Apps push traces and metrics over OTLP to Alloy, with the OpenTelemetry SDK.
Logs stay on stdout. Set `OTEL_SERVICE_NAME` to the Dokku app name: it
becomes the `app` label on metrics and links traces to the app's logs.

```bash
dokku network:set myapp attach-post-create observability
dokku config:set myapp \
  OTEL_EXPORTER_OTLP_ENDPOINT=http://alloy:4318 \
  OTEL_SERVICE_NAME=myapp \
  OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production
```

Set these resource attributes in the app, since one config applies to all
its processes:

- `process_type`: `web` or `worker`.
- `service.instance.id`: unique per process, for example the hostname and
  PID. Without it, every worker of an app pushes the same series and their
  counters overwrite each other.

Use `attach-post-create`, not `attach-post-deploy`: post-deploy only attaches
the deployed web and worker containers, so `dokku run` commands can't reach
`alloy`, and a container starts before it's attached, so it loses what it
sends until then.

The Apps dashboard's Pages row (requests and p95 response time by page)
comes from the standard `http.server.request.duration` histogram, with
`http.route`, which the OpenTelemetry HTTP instrumentations record. Requests
answered before URL routing have no `http.route`; Other requests groups them
by status into static files, redirects, not found and other. The row is
hidden for apps that don't push metrics.

Prometheus writes a zero at each counter's start time, so a process's first
increment, or a `dokku run` command's only one, counts in `increase()`.

Plain `increase()` estimates: it stretches the rise out to the edges of the
range, so a counter that went up once can read 1.5. To count rare events
exactly, such as payments, write `increase(<counter>[<range>] anchored)`, as
the Pages row does.

Log `trace_id` as a field of each JSON log line so Grafana can link the line
to its trace. Alloy doesn't accept OTLP logs; set `OTEL_LOGS_EXPORTER=none`
if the SDK exports logs by default.

### Scraping a metrics port instead

Prometheus scrapes any container on the `observability` network that has an
`observability.metrics.port` label, at `http://<container>:<port>/metrics`,
and labels its series with `app` and `process_type`. Don't map that port
with `ports:add`: Dokku's nginx would make it public.

```bash
dokku docker-options:add myapp deploy "--label observability.metrics.port=9000"
dokku network:set myapp attach-post-create observability
dokku ps:rebuild myapp
```

## Looking at it before Grafana

On the server:

```bash
docker run --rm --network observability curlimages/curl -s http://prometheus:9090/api/v1/targets
docker run --rm --network observability curlimages/curl -s http://loki:3100/loki/api/v1/labels
```

To send a test trace and metric through Alloy:

```bash
tg=ghcr.io/open-telemetry/opentelemetry-collector-contrib/telemetrygen
docker run --rm --network observability $tg traces --traces 1 --otlp-http --otlp-endpoint alloy:4318 --otlp-insecure --service otlptest
docker run --rm --network observability $tg metrics --metrics 1 --otlp-http --otlp-endpoint alloy:4318 --otlp-insecure --service otlptest
docker run --rm --network observability curlimages/curl -s -G http://tempo:3200/api/search --data-urlencode 'q={}'
docker run --rm --network observability curlimages/curl -s -G http://prometheus:9090/api/v1/series --data-urlencode 'match[]={app="otlptest"}'
```
