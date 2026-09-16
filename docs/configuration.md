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
| `base_packages` | build-essential, ca-certificates, curl, git, pipx, python3-dev, python3-pip, python3-venv, unattended-upgrades | Packages installed on every host |
| `base_timezone` | `Etc/UTC` | IANA timezone, for example `Africa/Nairobi` |
| `base_swap_size_mb` | `0` | Creates `/swapfile` of this size if the host has no swap. `0` skips it |
| `firewall_allowed_tcp_ports` | `[80, 443]` | TCP ports opened besides SSH. SSH is always allowed |
| `firewall_fail2ban` | `true` | Install and run fail2ban (default sshd jail) |
| `dokku_version` | `0.38.27` | Dokku apt package version. See [dokku.md](dokku.md) before bumping |
| `dokku_global_domain` | `""` | Global app domain, for example `apps.example.com`. Empty skips it |

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
| `admin_user`, `ssh_hardening`, `base`, `firewall`, `docker`, `dokku` | That role only (preflight always runs) |
| `upgrade` | The apt upgrade in `base`. Use `--skip-tags upgrade` to leave packages alone |

`dokku` needs `docker` to have run first on that host.
