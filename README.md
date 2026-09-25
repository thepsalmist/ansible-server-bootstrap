# ansible-server-bootstrap

Takes a fresh Ubuntu 22.04/24.04 server to a hardened Docker + Dokku host:
a key-only sudo admin, root and password SSH disabled (verified, with
rollback), ufw + fail2ban, unattended security upgrades, Python tooling,
Docker Engine, Dokku with its postgres, redis and letsencrypt
plugins, and Prometheus, Loki and Alloy collecting its metrics and logs. Safe to re-run; every run converges.

## Setup (on your workstation)

```bash
uv tool install ansible-core       # 2.15+, tested with 2.21
ansible-galaxy collection install -r requirements.yml
cp inventory.ini.example inventory.ini              # server address
cp group_vars/all.yml.example group_vars/all.yml    # admin_user, admin_ssh_keys
```

If `ansible-playbook` isn't found afterwards, run `uv tool update-shell` and
open a new shell.

## Usage

First run on a new server. It logs in as root, creates the admin, then
reconnects as the admin for everything else:

```bash
ansible-playbook bootstrap.yml                      # --ask-pass if root uses a password (needs sshpass)
ansible-playbook bootstrap.yml -e bootstrap_user=ubuntu   # images with a sudo user instead of root
```

Every run after that (root login is now off):

```bash
ansible-playbook site.yml
ansible-playbook site.yml --tags dokku              # one role
ansible-playbook site.yml --skip-tags upgrade       # skip the apt upgrade
```

Keep a root session or the provider's console open during the first run.

## Layout

| Path | Purpose |
|---|---|
| `bootstrap.yml` | First run: creates the admin as root, then imports `site.yml` |
| `site.yml` | Every run: all roles, connected as the admin |
| `tasks/preflight.yml` | Refuses unsupported OSes and bad `admin_*` settings |
| `roles/admin_user` | Admin account, SSH keys, passwordless sudo |
| `roles/ssh_hardening` | sshd drop-in, checked against the effective config, rolled back on failure |
| `roles/base` | Packages, uv, apt upgrade, unattended-upgrades, timezone, optional swap |
| `roles/firewall` | ufw (SSH + 80/443, deny the rest) and fail2ban |
| `roles/docker` | Docker Engine from Docker's apt repository |
| `roles/dokku` | Dokku from its apt repository, deploy keys, global domain, plugins |
| `roles/observability` | Prometheus, Loki, Alloy and exporters in Compose; Grafana as a Dokku app; JSON nginx access logs |

## Docs

- [Design and decisions](docs/design.md)
- [Configuration](docs/configuration.md): every variable and tag
- [SSH hardening](docs/ssh-hardening.md): lockout protection and recovery
- [Dokku](docs/dokku.md): deploying, domains, TLS, plugins, upgrades
- [Observability](docs/observability.md): metrics, logs, labels, adding an app
- [Testing](docs/testing.md): linting and checking a server
