# SSH hardening

## What changes

The role writes `/etc/ssh/sshd_config.d/00-hardening.conf` from
`ssh_hardening_options`. By default that turns off root login, password
and keyboard-interactive login, and X11 forwarding. sshd is reloaded, not
restarted, so open sessions stay up.

## Why a drop-in

Ubuntu's `/etc/ssh/sshd_config` starts with
`Include /etc/ssh/sshd_config.d/*.conf`, and for each setting sshd keeps
the first value it reads. On a typical VPS image:

```
sshd_config.d/50-cloud-init.conf   PasswordAuthentication yes   <- read first, wins
sshd_config (line 66)              PasswordAuthentication no    <- ignored
```

Editing the main file looks like it worked but changes nothing. Files in
`sshd_config.d/` are read in name order, so `00-hardening.conf` comes
before cloud-init's `50-` file.

## How lockout is prevented

1. `site.yml` connects as `admin_user`. By the time this role runs, a
   fresh key login and sudo as the admin have already worked. The admin has
   no password, so that login can only have used a key.
2. `validate: sshd -t` rejects a drop-in with syntax errors before it is
   written.
3. `sshd -T -C user=root,...` prints the settings sshd would actually apply
   to a root login, `Match` blocks included. Every option has to show up
   there with the expected value, or the run fails.
4. After the reload, Ansible drops its connection and opens a new one.
5. If step 3 or 4 fails, the rescue removes the drop-in, reloads sshd and
   stops the run.

Rollback needs a working connection. If the reload cut off new logins
entirely, the rescue can't reach the host either, so keep a root session
or the provider's console open during the first run.

## Recovery

From an open session or the provider's VNC/rescue console:

```bash
rm /etc/ssh/sshd_config.d/00-hardening.conf
sshd -t && systemctl reload ssh
```

## Checking by hand

```bash
ssh root@SERVER                                   # should fail: Permission denied (publickey)
ssh -o PubkeyAuthentication=no deploy@SERVER      # should fail: no password prompt
sudo sshd -T | grep -E '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication) '
```

## fail2ban

The firewall role writes `/etc/fail2ban/jail.d/00-ignoreip.local` with
loopback, the address Ansible connects from, and anything in
`firewall_fail2ban_ignoreip`, *before* installing the package. That order
matters: apt starts fail2ban on install and it scans the existing
`auth.log`, so a few earlier failed logins from your own address are enough
for it to ban you mid-run. A ban also drops established connections,
because fail2ban's rule sits above ufw's rule that accepts them.

A ban looks like `Connection refused` (fail2ban rejects, where ufw would
silently drop). Default bans last 10 minutes. To clear one from the
provider's console:

```bash
fail2ban-client set sshd unbanip YOUR_ADDRESS
fail2ban-client status sshd
```

## Adding options

Add entries to `ssh_hardening_options`. The same assertion checks them.
Don't add `AllowUsers`: Dokku's git pushes log in as the `dokku` user.
