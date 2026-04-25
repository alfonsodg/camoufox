# Camoufox Solver Service — Documentación

Fork: `alfonsodg/camoufox` | Branch: `feat/solver-service`

## Qué es

Microservicio HTTP que resuelve captchas y bypasses anti-bot usando browsers reales. Diseñado para integrarse con Obscura y Devourex.

## Arquitectura

```
Cliente (Obscura/Devourex/curl)     Solver Service (FastAPI)
POST /solve ──────────────────>    Browser pool
{type, url, sitekey}               ├── Chromium (reCAPTCHA v3)
              <────────────────    └── Camoufox (Cloudflare)
{token, cookies, user_agent}
```

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | /solve | Resolver challenge |
| GET | /health | Estado del pool |

## Challenges soportados

| Tipo | Browser | Tiempo | Probado |
|------|---------|--------|---------|
| `recaptcha_v3` | Chromium | ~11s | ✅ SEACE (90 licitaciones) |
| `turnstile` | Camoufox | ~5s | Implementado |
| `cloudflare_waf` | Camoufox | ~8s | Implementado |

## Hallazgo técnico importante

**Camoufox (Firefox patcheado) bloquea `grecaptcha.execute()`** por sus patches de privacidad a nivel C++. El script `recaptcha__en.js` de Google se carga pero no registra la función `execute`.

**Solución**: Usar Chromium para reCAPTCHA v3, Camoufox para Cloudflare. Cada browser es superior en su dominio:
- Chromium: compatible con Google reCAPTCHA
- Camoufox: 0% detección para Cloudflare/DataDome

## Componentes

```
service/
├── app.py              # FastAPI — POST /solve, GET /health
├── pool.py             # Browser pool (instancias reutilizables)
├── solvers/
│   ├── recaptcha_v3.py # Chromium → grecaptcha.execute() → token
│   └── cloudflare.py   # Camoufox → Turnstile/WAF → cookies
├── Dockerfile
├── requirements.txt
├── test.sh             # Test del servicio HTTP
└── test_seace.sh       # Test E2E contra SEACE
```

## Prueba contra SEACE

```
1. Loading SEACE...
2. Getting reCAPTCHA token... 2148 chars
3. Searching 24/04/2025...
   Página 1: 15 registros (total: 15)
   Página 2: 15 registros (total: 30)
   ...
   Página 6: 15 registros (total: 90)

✅ 90 licitaciones guardadas en seace_24042025.json
⏱  Tiempo total: 18779ms
```

## Configuración

| Variable | Default | Descripción |
|----------|---------|-------------|
| POOL_SIZE | 2 | Instancias de browser |
| MAX_USES_PER_INSTANCE | 50 | Reciclar después de N usos |

## Integración con Devourex

El solver service reemplaza la necesidad de que cada instancia del extractor resuelva su propio captcha. Flujo propuesto:

```
Devourex Extractor → POST solver:8888/solve → token
                   → Usa token para buscar en SEACE
                   → Extrae datos con Obscura (HTTP puro, sin browser)
```
