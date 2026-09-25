# Design

## Run flow

```
bootstrap.yml
  play 1: ssh as root (or bootstrap_user) -> preflight -> admin_user
  play 2: import site.yml

site.yml
  ssh as admin_user -> preflight -> admin_user -> ssh_hardening
                    -> base -> firewall -> docker -> dokku
```

Play 2 opens a new SSH connection as the admin. That's the "can I log in
as the new user and sudo?" test the manual checklist has you do in a
second terminal. If it fails, the run stops before anything touches root
login.

Each play sets `ansible_user` itself, so the inventory only needs the
address. Play variables override inventory ones, so an `ansible_user` in
the inventory would be ignored anyway.

SSH hardening runs straight after the admin user so the window with root
and password login open stays short.

## Decisions

**Key-only admin with passwordless sudo.** The admin account has no
password, so there's nothing for `sudo` to prompt for. Cloud images'
default users work the same way. Anyone holding the private key has root,
so keep it passphrase-protected. To require a sudo password instead, run
`sudo passwd deploy`, delete `/etc/sudoers.d/90-deploy` and the task that
writes it, and use `--ask-become-pass` from then on.

**SSH policy goes in a drop-in, not `sshd_config`.** Ubuntu's `sshd_config`
includes `sshd_config.d/*.conf` at the top, and sshd keeps the first value
it reads. Edits further down the main file lose to cloud-init's
`50-cloud-init.conf`, which sets `PasswordAuthentication yes` on many VPS
images. See [ssh-hardening.md](ssh-hardening.md).

**SSH stays on its current port.** A different port adds little security,
and on Ubuntu 24.04 sshd is socket-activated, so a port change also means
reconfiguring the systemd socket. The firewall reads the port from
`sshd -T`, so a port you've already changed stays open.

**Docker and Dokku come from their apt repositories, not install
scripts.** Both are declared as a signed deb822 repository plus a package,
instead of piping `get.docker.com` or Dokku's `bootstrap.sh` into a shell.
Re-runs converge, and bumping `dokku_version` upgrades. Docker is
installed first so Dokku's package uses `docker-ce` rather than pulling in
Ubuntu's `docker.io`.

**Dokku plugins are pinned to release tags.** `plugin:install` without a
tag clones whatever the plugin's default branch holds that day, so two
servers built a week apart could differ. The role installs the tag in
`dokku_plugins` and runs `plugin:update` when the installed version
differs, so bumping a tag upgrades the plugin.

**uv comes from a pinned release, not `curl | sh`.** Ubuntu 22.04/24.04
package no uv, and Astral's installer is a piped shell script. The base role
downloads the `base_uv_version` release, verifies it against the checksum
published beside it, and unpacks `uv` and `uvx` into `/usr/local/bin`.
Bumping the variable upgrades it. Ubuntu's `python3`, `python3-venv` and
`python3-pip` stay for anything that expects the system interpreter.

**The admin is in the `docker` group.** That's root-equivalent, but so is
passwordless sudo. It adds convenience, not risk. Remove that task in
`roles/docker` if you want every Docker call to go through sudo and its
audit log.

**The firewall only adds rules.** Existing ufw rules are kept, so a host
that was configured before may still have other ports open. Check
`sudo ufw status`.

**No automatic reboot.** The base role warns when
`/var/run/reboot-required` exists. unattended-upgrades is left at its
default of not rebooting.

**The observability stack runs in Compose, not as Dokku apps.** The
collectors need host mounts, the host PID namespace and the Docker socket,
and nothing in the stack serves the public. Grafana, which does, runs as a
Dokku app instead, so it gets its domain, nginx vhost and Let's Encrypt
certificate the same way the apps do. Prometheus, Alloy and cAdvisor can
read the Docker socket, and cAdvisor runs privileged, which makes all three
root-equivalent; none is reachable from outside the host.

**node-exporter uses host networking.** Inside a container it would report
the container's network, not the host's. It listens only on the
observability network's gateway, never a public address.

**Ubuntu 22.04 and 24.04 only.** Those are Dokku's supported releases.
Preflight refuses anything else.
