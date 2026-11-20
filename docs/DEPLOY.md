# Deploying to Ubuntu on AWS

Replace `example.com`, `ubuntu`, and `/srv/oquv-markazlar` below with your
domain, server user, and project directory. Point your domain's DNS at the
EC2 server first. PostgreSQL can run on the server or be an AWS RDS instance;
use its connection details in `DATABASE_URL`.

## Install packages and the application

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip nginx postgresql postgresql-contrib certbot python3-certbot-nginx
cd /srv/oquv-markazlar
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
nano .env
```

Set a unique, long `SECRET_KEY`, `DEBUG=False`, your domain in
`ALLOWED_HOSTS`, and `https://` origins for `CSRF_TRUSTED_ORIGINS`. Set
`DATABASE_URL` to your PostgreSQL connection URL, `HTTPS=true`, and
`MEDIA_DIR=/srv/oquv-markazlar/media`. Keep `.env` private.

With the virtual environment active and `.env` configured, initialize Django:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## Run Gunicorn with systemd

Create `/etc/systemd/system/oquv-markazlar.service` (change the user and
directory if needed):

```ini
[Unit]
Description=oquv-markazlar Django application
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/srv/oquv-markazlar
EnvironmentFile=/srv/oquv-markazlar/.env
ExecStart=/srv/oquv-markazlar/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 config.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now oquv-markazlar
sudo systemctl status oquv-markazlar
```

## Configure nginx and HTTPS

Create `/etc/nginx/sites-available/oquv-markazlar` and replace the example
domain and media directory:

```nginx
server {
    listen 80;
    server_name example.com www.example.com;

    client_max_body_size 10M;

    location /media/ {
        alias /srv/oquv-markazlar/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site and request a certificate (Certbot updates the nginx HTTPS
configuration):

```bash
sudo ln -s /etc/nginx/sites-available/oquv-markazlar /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d example.com -d www.example.com
```

In production Django only serves uploaded photos through nginx's `/media/`
alias; Django's own media serving remains enabled only with `DEBUG=True` for
local development. Ensure nginx can read the configured media directory.

In the Yandex Developer Dashboard, restrict the Maps API key to your site's
HTTP referrers (the HTTPS domain and, if used, `www` domain), remove unrelated
referrers, and enable only the APIs this site uses. Copy that restricted key
into the server's `YANDEX_MAPS_API_KEY`.

## Deploy updates

From the project directory, after pulling your changes:

```bash
git pull
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart oquv-markazlar
```
