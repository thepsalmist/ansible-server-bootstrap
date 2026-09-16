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
5. Installs each `dokku_plugins` entry at its pinned release tag, and runs
   `plugin:update` when the installed version doesn't match the tag.

## Deploying an app

Create the app first — every method below needs it to exist:

```bash
dokku apps:create myapp
```

Then populate its repository from a prebuilt image, an archive, or a remote
git repository:

```bash
dokku git:from-image myapp registry.example.com/myapp:v1 "Your Name" you@example.com
dokku git:from-archive myapp https://example.com/myapp.tar.gz "Your Name" you@example.com
dokku git:sync --build myapp https://github.com/you/myapp.git main
```

Check <https://dokku.com/docs/deployment/methods/git/> for when each of
these builds and deploys on its own and when you have to trigger it, for
example with `dokku ps:rebuild myapp`.

Pushing to the server also works, if you'd rather:

```bash
git remote add dokku dokku@SERVER:myapp
git push dokku main
```

The keys the role registers cover both: they authorise git pushes and
running the CLI remotely, as in `ssh dokku@SERVER apps:list`.

## Domains and TLS

Set `dokku_global_domain: apps.example.com`, point both `apps.example.com`
and `*.apps.example.com` at the server, then run
`ansible-playbook site.yml --tags dokku`. Apps are served at
`myapp.apps.example.com`.

The role installs the letsencrypt plugin. TLS is per app, once DNS
resolves and the app is deployed:

```bash
sudo dokku letsencrypt:set --global email you@example.com
sudo dokku letsencrypt:cron-job --add
sudo dokku letsencrypt:enable myapp
```

## Plugins

The role installs Dokku's postgres, redis and letsencrypt plugins. To add
or drop one, set the whole list in `group_vars/all.yml`. Official plugins
are listed at <https://dokku.com/docs/community/plugins/>.

```yaml
dokku_plugins:
  - name: postgres
    url: https://github.com/dokku/dokku-postgres.git
    version: "1.48.0"
  - name: mysql
    url: https://github.com/dokku/dokku-mysql.git
    version: "<release tag>"
```

`version` must be a release tag. The role compares it with the version
`dokku plugin:list` reports, which Dokku's own plugins keep equal to the
tag. A branch or commit would never match, so every run would update the
plugin again.

If an install or update fails part-way, for example on a Docker Hub pull
limit, the plugin already reports its pinned version and later runs skip
it. Once the cause is fixed, run `sudo dokku plugin:install` with no
arguments to finish setting up every installed plugin.

Removing a plugin from the list doesn't uninstall it. Delete its services,
then run `sudo dokku plugin:uninstall <name>`.

The role only installs plugins. Each app creates and links its own
services:

```bash
dokku postgres:create myapp-db
dokku postgres:link myapp-db myapp     # sets DATABASE_URL on myapp
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

To upgrade a plugin, bump its `version` and run `--tags dokku`. Existing
services keep the image version they were created with until you run, for
example, `dokku postgres:upgrade myapp-db`. Check the new tag's
`Dockerfile` first. Postgres doesn't migrate data across major versions,
so if the major version changed, use the export and import described in
the plugin's README instead.

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

`postgres:expose` and `redis:expose` publish ports the same way. Expose
on loopback only (`dokku postgres:expose myapp-db 127.0.0.1:5432`) and
reach it through an SSH tunnel
(`ssh -L 5432:127.0.0.1:5432 <admin_user>@SERVER`).

## Out of scope

Off-server backups (with a tested restore), monitoring, and alerting.
Set these up before the server holds production data.
