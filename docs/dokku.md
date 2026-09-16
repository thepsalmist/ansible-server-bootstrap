# Dokku

## What the role does

1. Preseeds `dokku/skip_key_file`, so the package doesn't import root's
   key.
2. Adds Dokku's packagecloud repository (deb822, signed), installs
   `dokku=<dokku_version>`, and runs
   `dokku plugin:install-dependencies --core` after an install or
   upgrade. These are the same steps Dokku's `bootstrap.sh` runs, without
   executing a downloaded script.
3. Registers each `admin_ssh_keys` entry as `<admin_user>-<hash>` and
   skips keys Dokku already has.
4. Sets `dokku_global_domain`, if you gave one.

## Deploying an app

```bash
git remote add dokku dokku@SERVER:myapp
git push dokku main
```

## Domains and TLS

Set `dokku_global_domain: apps.example.com`, point both `apps.example.com`
and `*.apps.example.com` at the server, then run
`ansible-playbook site.yml --tags dokku`. Apps are served at
`myapp.apps.example.com`.

TLS is per app, once DNS resolves and the app is deployed:

```bash
sudo dokku plugin:install https://github.com/dokku/dokku-letsencrypt.git
sudo dokku letsencrypt:set --global email you@example.com
sudo dokku letsencrypt:cron-job --add
sudo dokku letsencrypt:enable myapp
```

## Upgrading

Read the migration guide for every release between your version and the
target: <https://dokku.com/docs/getting-started/upgrading/>. Then bump
`dokku_version` and run `--tags dokku`. That upgrades the `dokku` package
only. Upgrade its companion packages and rebuild apps as that guide
describes:

```bash
sudo apt-get --no-install-recommends install dokku herokuish sshcommand plugn gliderlabs-sigil dokku-update dokku-event-listener
sudo dokku ps:rebuild --all
```

unattended-upgrades only applies Ubuntu security updates, so Docker and
Dokku change only when you upgrade them.

## Docker bypasses ufw

Ports published with `docker run -p` or a compose `ports:` entry go
through Docker's own iptables rules. They're reachable from the internet
even though `ufw status` doesn't list them. Dokku apps aren't affected,
because nginx on 80/443 proxies to containers on internal addresses. For
anything else, don't publish database ports, bind to loopback when you
need to (`-p 127.0.0.1:5432:5432`), and use the provider's firewall as a
second layer.

## Out of scope

Off-server backups (with a tested restore), monitoring, and alerting.
Set these up before the server holds production data.
