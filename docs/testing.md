# Testing

## Before changing a server

```bash
ansible-lint                                   # production profile, see .ansible-lint
ansible-playbook site.yml --syntax-check
ansible-playbook site.yml --check --diff       # shows drift on a host that's already set up
```

`--check` fails partway on a fresh host. Tasks like authorising the
admin's key need the user that an earlier task would have created. Try
first-run changes on a throwaway server instead, for example a new VPS or
`multipass launch 24.04`.

A second `site.yml` run should report `changed=0`, apart from the apt
upgrade when new packages have been published.

## Checking a server

```bash
sudo sshd -T | grep -E '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication) '
sudo ufw status verbose
sudo fail2ban-client status sshd
uv --version
systemctl is-active docker fail2ban
docker run --rm hello-world
sudo dokku version
sudo dokku ssh-keys:list
sudo dokku plugin:list
cat /etc/apt/apt.conf.d/20auto-upgrades
```
