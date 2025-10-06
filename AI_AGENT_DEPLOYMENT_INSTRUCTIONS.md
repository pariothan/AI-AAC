# AI Operator Playbook: Publish AAC Communication Builder at `/aac-demo`

This document guides an autonomous agent through publishing the AAC Communication Builder web app onto the owner's production website, exposed at the `/aac-demo` path. The demo requires visitors to supply their own OpenAI API keys through the UI.

## 0. Mission Inputs
- Repository location: provided by operator (current working tree).
- Deployment host: Linux server already running the primary website.
- Reverse proxy: Nginx (adapt instructions if another proxy is used).
- Python 3.10+ available on host.
- No server-side OpenAI API key required; users enter their own.

## 1. Prepare Application Environment
1. Create working directory if not already present:
   ```bash
   cd /srv/aac-demo
   ```
2. Ensure required system packages are installed (Python headers, pip, virtualenv, build tools):
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3 python3-venv python3-pip build-essential
   ```
3. Create and activate virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```
5. Optional (production server):
   ```bash
   pip install gunicorn
   ```

## 2. Runtime Configuration
Set environment variables so the Flask app binds correctly and understands the subpath mount.
```bash
export HOST=0.0.0.0
export PORT=5001
export APP_BASE_PATH=/aac-demo
export FLASK_ENV=production
```
These values must also be provided to any process manager (systemd, supervisor, container runtime).

## 3. Launch Application Service
### Option A: Ephemeral test run
```bash
source /srv/aac-demo/.venv/bin/activate
python app.py
```
Confirm the service responds at `http://localhost:5001/aac-demo/` before daemonizing.

### Option B: Gunicorn (recommended for production)
```bash
source /srv/aac-demo/.venv/bin/activate
gunicorn --bind 0.0.0.0:5001 --env APP_BASE_PATH=/aac-demo --env FLASK_ENV=production app:app
```
Wrap this command in a systemd unit for persistence:
```
[Unit]
Description=AAC Communication Builder
After=network.target

[Service]
WorkingDirectory=/srv/aac-demo
Environment="APP_BASE_PATH=/aac-demo" "FLASK_ENV=production"
ExecStart=/srv/aac-demo/.venv/bin/gunicorn --bind 0.0.0.0:5001 app:app
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```
Reload systemd and enable the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now aac-demo.service
```

## 4. Configure Reverse Proxy
Add a location block to the existing Nginx server configuration that serves the main website:
```nginx
location /aac-demo/ {
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Prefix /aac-demo;
    proxy_pass http://127.0.0.1:5001/;
    proxy_redirect off;
}
```
Reload Nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 5. Validation Checklist
- `curl -I https://<primary-domain>/aac-demo/` returns HTTP 200.
- Browser loads the UI, static assets render correctly, and all `fetch` calls resolve under `/aac-demo/*` (verify via dev tools).
- Enter a valid OpenAI API key in the modal and generate vocabulary; requests should succeed and never send the key to logs (inspect server logs for confirmation).
- Upload an image to confirm the `/analyze-image` endpoint works through the proxy.
- Ensure HTTPS warning does not appear when accessing via HTTPS.

## 6. Site Integration Tasks
- Add a navigation link or CTA from the main site pointing to `https://<primary-domain>/aac-demo/`.
- Provide short copy explaining that visitors must bring their own OpenAI API key to use AI-powered features.
- Optionally embed within an `<iframe>`: set the iframe `src` to `/aac-demo/` and adjust CSP rules if necessary.

## 7. Monitoring and Maintenance
- Logs: `journalctl -u aac-demo.service -f` (if using systemd) or Gunicorn logs.
- Restart procedure: `sudo systemctl restart aac-demo.service`.
- Rate limiting is in-memory; if the app restarts rate counters reset. For horizontal scaling, introduce a shared store (Redis) before adding more replicas.
- Keep `requirements.txt` patched and rerun `pip install -r requirements.txt` when dependencies change.

## 8. Security Notes
- TLS terminates at the reverse proxy; keep Flask in production mode.
- No API keys are stored server-side; the UI keeps them in local/session storage.
- Enforce strong firewall rules so port `5001` is accessible only internally (loopback).
- Maintain OS patches and monitor `gunicorn` and `flask` CVEs.

## 9. Handoff Summary
After completing the steps above, notify the human owner that:
1. The app is reachable at `/aac-demo/` on the production site.
2. Visitors must supply their own OpenAI key to unlock AI features.
3. The service is running under systemd (if applicable) and monitored via logs noted above.
