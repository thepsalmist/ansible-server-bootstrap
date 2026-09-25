# Configuration

Required settings go in `group_vars/all.yml`. Override any role default
there too.

## Variables

| Variable | Default | Meaning |
|---|---|---|
| `admin_user` | required | Admin account to create and connect as |
| `admin_ssh_keys` | required | List of public keys for the admin. Also registered with Dokku |
| `bootstrap_user` | `root` | Account `bootstrap.yml` first connects as. Pass with `-e` |
| `ssh_hardening_options` | see below | sshd directives written to the drop-in and verified |
| `base_packages` | build-essential, ca-certificates, curl, git, python3-dev, python3-pip, python3-venv, unattended-upgrades | Packages installed on every host |
| `base_uv_version` | `0.12.15` | uv release installed to `/usr/local/bin`. Bump it to upgrade |
| `base_timezone` | `Etc/UTC` | IANA timezone, for example `Africa/Nairobi` |
| `base_swap_size_mb` | `0` | Creates `/swapfile` of this size if the host has no swap. `0` skips it |
| `firewall_allowed_tcp_ports` | `[80, 443]` | TCP ports opened besides SSH. SSH is always allowed |
| `firewall_fail2ban` | `true` | Install and run fail2ban (default sshd jail) |
| `firewall_fail2ban_ignoreip` | `[]` | Extra addresses fail2ban never bans. Loopback and the address you deploy from are always included |
| `docker_log_max_size` | `10m` | Size a container's log reaches before Docker rotates it |
| `docker_log_max_file` | `3` | Rotated log files Docker keeps per container |
| `dokku_version` | `0.38.27` | Dokku apt package version. See [dokku.md](dokku.md) before bumping |
| `dokku_global_domain` | `""` | Global app domain, for example `apps.example.com`. Empty skips it |
| `dokku_letsencrypt_email` | `""` | Email Let's Encrypt certificates are requested with, for every app. Empty skips it |
| `dokku_plugins` | postgres, redis, letsencrypt | Dokku plugins, each pinned to a release tag. See [dokku.md](dokku.md#plugins) |
| `observability_subnet` | `172.30.0.0/24` | Subnet of the `observability` Docker network. Pick one no other network uses |
| `observability_gateway` | `172.30.0.1` | That subnet's gateway, where node-exporter listens |
| `observability_prometheus_retention` | `15d` | How long Prometheus keeps metrics |
| `observability_loki_retention` | `720h` | How long Loki keeps logs |
| `observability_journal_units` | ssh, docker | systemd units whose journal goes to Loki |
| `observability_*_version` | see `roles/observability/defaults` | Image tag for each service. Bump to upgrade |

`ssh_hardening_options` defaults to:

```yaml
ssh_hardening_options:
  PermitRootLogin: "no"
  PasswordAuthentication: "no"
  KbdInteractiveAuthentication: "no"
  X11Forwarding: "no"
```

Overriding it replaces the whole dict, so list every option you want. Use
the names `sshd -T` prints and quote `yes`/`no`.

## Tags

| Tag | Runs |
|---|---|
| `admin_user`, `ssh_hardening`, `base`, `firewall`, `docker`, `dokku`, `observability` | That role only (preflight always runs) |
| `upgrade` | The apt upgrade in `base`. Use `--skip-tags upgrade` to leave packages alone |

`dokku` needs `docker` to have run first on that host, and `observability`
needs `dokku`.
