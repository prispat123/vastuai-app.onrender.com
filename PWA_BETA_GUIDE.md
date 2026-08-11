# VastuAI Mobile Beta — PWA

This build adds installable-web metadata and assets to the shared VastuAI v5.7.1 responsive codebase.

## What changed

- Web App Manifest with VastuAI name, sage theme and standalone display mode.
- 192 px and 512 px VastuAI app icons.
- Mobile/Apple web-app metadata injected into the Streamlit host page.
- Static asset serving enabled through Streamlit.
- A conservative service worker caches only PWA branding assets. VastuAI assessment pages remain network-first because Streamlit needs a live WebSocket session and assessment data must not become stale.

## Important: HTTPS is required for real PWA installation

Running VastuAI from `http://192.168.x.x:8501` is excellent for responsive testing, but Android Chrome normally needs a secure HTTPS origin for full PWA installation. `localhost` is treated specially by browsers, but a LAN IP is not.

For other testers, deploy this build to an HTTPS URL such as `https://app.example.com`. After deployment, open the URL in Android Chrome and use **Install app** / **Add to Home screen**.

## Local run

```powershell
streamlit run app.py --server.address 0.0.0.0
```

## PWA assets

Streamlit serves the `static/` directory at `/app/static/` because `.streamlit/config.toml` enables `server.enableStaticServing`.
