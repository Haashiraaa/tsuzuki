# Putting Tsuzuki on a server

This puts the web app on a cheap VPS so you can reach it from your phone or laptop.

**The recommendation: Caddy with a password.** Caddy gives you HTTPS on your own domain with no
setup, asks for a username and password, serves the web app, and passes `/api` to the Tsuzuki
server. It is one small file. The other sensible choice is Tailscale (see the end); use that
instead if you do not want to buy a domain or leave anything open to the internet.

Why Caddy first: the Tsuzuki server has **no login of its own yet**. Anyone who can reach it can
queue downloads and take files. Caddy's password is what protects it, so never expose the
server's port directly.

```
phone / laptop --HTTPS + password--> Caddy (ports 80/443)
                                       |-- /api/*  -> Tsuzuki server on 127.0.0.1:8000
                                       `-- the rest -> the built web app (static files)
```

## 1. The server

Any small Debian or Ubuntu VPS will do. As root, once:

```bash
apt update && apt install -y python3-venv aria2 ffmpeg ufw git
adduser --system --group --home /var/lib/tsuzuki tsuzuki

ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable   # 8000 stays closed
```

`aria2` makes downloads faster, and `ffmpeg` is there for the video streams that need joining.

## 2. Install Tsuzuki

```bash
git clone https://github.com/Haashiraaa/tsuzuki /opt/tsuzuki
cd /opt/tsuzuki
python3 -m venv venv
venv/bin/pip install ".[server]"
```

Build the web app on your own computer (or on the server if it has Node 22). **Set
`VITE_USE_SAMPLE=false`**, or the app shows its built-in sample data instead of the real server:

```bash
cd frontend
npm ci
VITE_USE_SAMPLE=false npm run build      # makes frontend/dist
```

Copy `frontend/dist` to `/srv/tsuzuki/` on the server (`scp -r dist/* you@server:/srv/tsuzuki/`).

## 3. Run the Tsuzuki server all the time

`/etc/systemd/system/tsuzuki.service`:

```ini
[Unit]
Description=Tsuzuki server
After=network.target

[Service]
User=tsuzuki
ExecStart=/opt/tsuzuki/venv/bin/python -m tsuzuki.api -o /var/lib/tsuzuki --keep-hours 24
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable --now tsuzuki
journalctl -u tsuzuki -f        # to watch it
```

It listens on `127.0.0.1:8000` only, which is exactly what you want. Downloads and the database
live in `/var/lib/tsuzuki`. Finished files are deleted from there once they are saved to your
device (or after `--keep-hours`), so disk use stays small.

## 4. Caddy

Buy a domain and point an `A` record for it (say `tsuzuki.example.com`) at the server's IP.
If the domain is on Cloudflare, set the record to **DNS only** (grey cloud), not proxied:
Cloudflare's proxy is not meant for large video files.

```bash
apt install -y caddy
caddy hash-password          # type a password; copy the long result
```

`/etc/caddy/Caddyfile`:

```
tsuzuki.example.com {
    basic_auth {
        terry PASTE_THE_HASH_HERE
    }

    handle /api/* {
        reverse_proxy 127.0.0.1:8000
    }

    handle {
        root * /srv/tsuzuki
        try_files {path} /index.html
        file_server
    }
}
```

```bash
systemctl reload caddy
```

Open `https://tsuzuki.example.com`, sign in, and you are in. Caddy gets and renews the HTTPS
certificate by itself. "Save to this device" works through it, because the browser already holds
the password for that address.

### Visitors, cookies and a big disk

Each browser is recognised by a cookie the server sets on first use. Caddy's `reverse_proxy`
passes `X-Forwarded-Proto: https` to the server, which is how it knows to mark the cookie
`Secure`; no setting is needed while Caddy runs on the same machine. If you later add a second
proxy in front, make sure it passes that header too.

Per-person limits are `--max-open` (default 12 episodes at once) and `--max-series` (default 60)
and can be added to `ExecStart`. With a larger disk, also raise `--max-waiting-gb` (the point at
which new downloads pause until people save what is waiting), for example
`--max-waiting-gb 2000` on a 3 TB disk. Files are deleted once everyone who asked for them has
saved them, or after `--keep-hours`, so disk use follows how much is waiting, not how many
people there are.

## Updating

```bash
cd /opt/tsuzuki && git pull && venv/bin/pip install ".[server]" && systemctl restart tsuzuki
```

Rebuild and copy `frontend/dist` again when the web app changes. The database upgrades itself on
start.

## Backups

Everything worth keeping is one file, `/var/lib/tsuzuki/tsuzuki.db` (your library and what was
downloaded). Copy it now and then; the video files are disposable.

## The other option: Tailscale

[Tailscale](https://tailscale.com) makes a private network between your own devices. Install it
on the server and on your phone and laptop, start the server with
`--host <the server's Tailscale address>`, and open that address from your devices. Nothing is
open to the public internet, so there is no password to manage and no domain to buy.

It loses on convenience: every device needs the Tailscale app, and you cannot open Tsuzuki from
a friend's phone or a browser you do not control. For a personal tool that is a fair trade, and
it is the safer one. If you pick it, skip the Caddy step and keep ports 80 and 443 closed.
