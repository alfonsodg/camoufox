# Camoufox Solver Service

HTTP API for solving captchas and anti-bot challenges using Camoufox (0% detection Firefox).

## Quick Start

```bash
pip install -r service/requirements.txt
python -m camoufox fetch
uvicorn service.app:app --port 8888
```

## API

### POST /solve

```bash
# reCAPTCHA v3
curl -X POST http://localhost:8888/solve \
  -H "Content-Type: application/json" \
  -d '{"type": "recaptcha_v3", "url": "https://example.com", "sitekey": "6Lf..."}'

# Cloudflare WAF
curl -X POST http://localhost:8888/solve \
  -H "Content-Type: application/json" \
  -d '{"type": "cloudflare_waf", "url": "https://protected-site.com"}'

# Cloudflare Turnstile
curl -X POST http://localhost:8888/solve \
  -H "Content-Type: application/json" \
  -d '{"type": "turnstile", "url": "https://site-with-turnstile.com"}'
```

### GET /health

```bash
curl http://localhost:8888/health
```

## Obscura Integration

```bash
obscura fetch https://seace.gob.pe/... \
  --challenge-solver http://localhost:8888 \
  --eval "document.title"
```

## Docker

```bash
docker build -f service/Dockerfile -t camoufox-solver .
docker run -p 8888:8888 camoufox-solver
```

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `POOL_SIZE` | 2 | Number of browser instances |
| `MAX_USES_PER_INSTANCE` | 50 | Recycle after N solves |
