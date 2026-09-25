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

## Grafana

Set `observability_grafana_domain` and `observability_grafana_admin_password`
in `group_vars/all.yml` and the role deploys Grafana as the Dokku app
`grafana`:

- `git:from-image grafana/grafana:<observability_grafana_version>`. Bumping
  the version redeploys it.
- Data in `/var/lib/dokku/data/storage/grafana`, so users and settings
  survive rebuilds and upgrades.
- Datasources (Prometheus as the default, Loki) and dashboards come from
  `/opt/observability/grafana`, mounted read-only. They can't be edited in
  the UI; change them here and re-run. Dashboards are in two folders:

  | Folder | Dashboard | Shows |
  |---|---|---|
  | Overview | Server (the home page) | CPU, memory, disk and load at a glance, then host graphs and the busiest containers |
  | Overview | Apps | Per app: health check, certificate, traffic, errors, response time, containers, logs |
  | Details | Server details (Node Exporter Full) | Every host metric, from grafana.com |

  Each has a Dashboards link to the others. The overviews' JSON is in
  `roles/observability/files/dashboards/Overview/`.
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
