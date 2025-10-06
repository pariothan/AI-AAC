# AI Operator Playbook: Host AAC Demo Externally and Embed via `<iframe>`

Use this guide to deploy the AAC Communication Builder to a standalone hosting provider (Render/Fly.io/Railway/VPS) and embed it on the main website through an iframe. Visitors still supply their own OpenAI API keys within the iframe.

## 0. Mission Inputs
- Repository source code.
- External hosting account (choose one: Render, Fly.io, Railway, or VPS with public IP).
- DNS and HTTPS handled by the external host (no reverse proxy on the main site).
- Main website under your control where the iframe will live.

## 1. Prepare the App for Root Deployment
- Ensure `APP_BASE_PATH` is unset or empty so routes resolve at `/`.
- Confirm environment requirements: Python 3.10+, `requirements.txt`, `en_core_web_sm` spaCy model.
- Disable Flask debug (`FLASK_ENV=production`).

## 2. Deploy to Hosting Platform
### Option A: Render (example)
1. Commit code to a Git repo accessible by Render.
2. In Render dashboard: create a new Web Service.
3. Build command: `pip install -r requirements.txt && python -m spacy download en_core_web_sm`.
4. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`.
5. Environment variables:
   - `FLASK_ENV=production`
   - `HOST=0.0.0.0`
   - `PORT=10000` (Render sets this dynamically via `$PORT`)
   - Leave `APP_BASE_PATH` blank or remove it.
6. Deploy and wait for the health check to pass.

### Option B: Fly.io (example)
1. Install `flyctl` and run `fly launch` in the repo.
2. Select Python builder, set internal port to `8080`.
3. Edit `Dockerfile` or `fly.toml` to run `gunicorn app:app --bind 0.0.0.0:8080`.
4. Add release command to download spaCy model: `python -m spacy download en_core_web_sm`.
5. Deploy with `fly deploy`.

### Option C: VPS
1. Provision a VM and follow local setup instructions (virtualenv, `pip install -r requirements.txt`, download spaCy model).
2. Run `gunicorn` on port 8000 and front it with the host’s load balancer or platform-provided HTTPS.

## 3. Configure Security Headers for Embedding
- Remove or override `X-Frame-Options` (set to `ALLOW-FROM https://your-site.com` or omit).
- Add CSP header allowing your site to embed the demo:
  `Content-Security-Policy: frame-ancestors https://your-site.com;`
- On managed platforms, set these headers via dashboard; on VPS, configure the web server or add response middleware.

## 4. Verify Standalone Deployment
- Visit `https://demo-host.example.com/` and confirm the UI loads.
- Open browser dev tools: all API calls should hit `https://demo-host.example.com/*` and return 200.
- Complete AI flows with a test OpenAI API key to ensure success.

## 5. Embed on Main Website
1. On the main site’s page template, insert:
   ```html
   <iframe
       src="https://demo-host.example.com/"
       title="AAC Communication Builder"
       width="100%"
       height="900"
       loading="lazy"
       style="border: 0; background: transparent;"
       allow="clipboard-write"
   ></iframe>
   ```
2. Adjust `height` or add responsive CSS as needed.
3. If the main site uses a strict Content-Security-Policy, append the external host to `frame-src` or `child-src` directives.
4. Publish the page and test on desktop/mobile.

## 6. Optional: Custom Domain for Demo
- Point a subdomain (e.g., `aac-demo.yourdomain.com`) to the hosting provider.
- Ensure certificates cover that subdomain.
- Update the iframe `src` accordingly.

## 7. Monitoring & Maintenance
- Use the hosting provider’s logging/metrics to monitor uptime and errors.
- Redeploy when repository changes are made (depending on provider, push to main triggers redeploy).
- Validate periodically that embedding headers remain in place after platform updates.

## 8. Handoff Summary
After deployment and embedding:
1. Confirm the page renders inside the main site.
2. Note where the app is hosted, process to redeploy, and any credentials needed.
3. Provide the owner with the live iframe URL and assurance that visitors still supply their own API keys.
