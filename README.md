# Sticky-Net

Sticky-Net is an AI honeypot API for SMS and chat scams aimed at Indian users.
It decides whether an incoming message is a scam, replies as a believable victim persona to keep the scammer talking, and pulls out the payment details the scammer reveals.
Those details are bank accounts, UPI IDs, phone numbers, phishing links, emails and case or order numbers.

It was built for the GUVI hackathon honeypot track.
The evaluator sends one scammer message per turn to `POST /api/v1/analyze`, and Sticky-Net answers within its 30 second limit.
The original submission write-up, with the evaluation results, lives in [docs/HACKATHON_SUBMISSION.md](docs/HACKATHON_SUBMISSION.md).

[![CI](https://github.com/heyitsgautham/sticky-net/actions/workflows/ci.yml/badge.svg)](https://github.com/heyitsgautham/sticky-net/actions/workflows/ci.yml)

## What it does on each turn

1. A regex pre-filter in `src/detection/detector.py` catches obvious scams (OTP requests, account threats, lottery wins) in a few milliseconds.
2. When the regex finds nothing, a Gemini Flash classifier in `src/detection/classifier.py` scores the message.
   A session that was ever flagged stays flagged, and confidence never goes down.
   If both say "not a scam", the agent still engages cautiously.
3. The honeypot agent in `src/agents/honeypot_agent.py` writes the reply as a persona with seeded fake card, bank and Aadhaar details.
   One Gemini call returns the reply and the intelligence it spotted as a single JSON object.
4. `src/intelligence/` validates that intelligence and runs a regex pass over the whole conversation as a backup.
5. `src/api/session_store.py` accumulates intelligence per session in memory and writes it through to Firestore when Firestore is reachable.
   The in-memory caches keep at most `SESSION_CACHE_MAX_ENTRIES` sessions, so a flood of new session IDs cannot exhaust memory.
6. A background task posts the accumulated intelligence to the GUVI callback URL.

When the evaluator sends `[CONVERSATION_END]`, the API returns the session summary.
That summary has the scam verdict, scam type, confidence, message count, engagement time and every piece of intelligence collected.

Each Gemini call has a 12 second timeout and falls back to a second model.
The whole request has a 26 second budget, after which the agent returns a stalling reply.
With no Google credentials, the regex detector still works and the agent answers with canned replies.

## Repository layout

| Path | What it holds |
|---|---|
| `src/main.py` | FastAPI app, CORS, `/health`, the static test UI at `/` |
| `src/api/` | Routes, request and response schemas, API key and security header middleware, session store, GUVI callback |
| `src/services/` | `TurnPipeline`, the detect, engage and extract steps both analyze routes share |
| `src/detection/` | Regex pre-filter and Gemini classifier |
| `src/agents/` | Honeypot agent, personas, engagement policy, prompts, fake data, reply parser |
| `src/intelligence/` | Regex extractor, validators, patterns and word lists |
| `src/llm/` | Helpers for reading Gemini responses |
| `src/logging_config.py`, `src/log_redaction.py` | structlog and stdlib logging setup, and the processor that masks keys and tokens |
| `src/metrics.py` | Prometheus counters and histograms for `/metrics` |
| `config/settings.py` | Every setting, loaded from the environment by pydantic-settings |
| `config/secret_files.py` | Reads the `API_KEY_FILE` secret mount |
| `tests/`, `final-testing/` | The default pytest suites, all offline |
| `frontend/` | React 19 dashboard (Create React App with craco, Tailwind, shadcn/ui) |
| `gk-testing/eval_framework/` | Scoring engine and scammer simulator for multi-model evaluation runs |
| `multi-turn-testing/`, `simulated-testing/`, `tester/` | Older evaluation harnesses and their saved runs |
| `india-map/` | Standalone map widget prototype |
| `docs/` | Design notes, the problem statement and hackathon reports |

## Requirements

- Python 3.11 and [uv](https://docs.astral.sh/uv/)
- Node 20 and Yarn 1.22 for the frontend
- A Google Cloud project with Vertex AI enabled for real Gemini replies (optional for tests)

## Install

```bash
git clone https://github.com/heyitsgautham/sticky-net.git
cd sticky-net
uv sync --extra dev
cp .env.example .env
```

`uv sync` installs the exact versions in `uv.lock`.
`requirements.txt` is the same pinned set exported for pip users.

Edit `.env` and set at least `API_KEY` and `GOOGLE_CLOUD_PROJECT`.
For real Gemini calls, either run `gcloud auth application-default login` or point `GOOGLE_APPLICATION_CREDENTIALS` at a service account key in `secrets/`.

## Run

```bash
uv run uvicorn src.main:app --reload --port 8080
```

The API listens on http://localhost:8080.
`/health` answers without a key, and `/docs` serves Swagger UI while `DEBUG=true`.

```bash
curl -s -X POST http://localhost:8080/api/v1/analyze \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"sessionId": "demo-1",
       "message": {"sender": "scammer", "text": "Your SBI account will be blocked today. Verify immediately.", "timestamp": "2026-01-21T10:15:30Z"},
       "conversationHistory": [],
       "metadata": {"channel": "SMS", "language": "English", "locale": "IN"}}'
```

The reply is `{"status": "success", "reply": "..."}`.
Send `[CONVERSATION_END]` as the message text with the same `sessionId` to get the summary.

### Frontend

```bash
cd frontend
cp .env.example .env.development.local
yarn install --frozen-lockfile
yarn start
```

The dashboard runs on http://localhost:3000 and calls `REACT_APP_API_URL`.
CRA bakes `REACT_APP_*` values into the bundle, so never put a real secret there.

### Docker

```bash
docker compose up --build
```

This builds and starts the API on port 8080 and the dashboard on port 3000.
`.env` is optional for compose, and a key in `./secrets/service-account.json` enables real Gemini replies.
`docker compose --profile emulator up` adds a local Firestore emulator on port 8085.

## Test

```bash
uv run pytest
```

This runs `tests/` and `final-testing/`, about 450 tests in a few seconds.
A root `conftest.py` replaces the Gemini client with a fake that raises, disables Firestore and turns the GUVI callback off.
No test reaches the network.

Coverage, lint and types run the same way CI runs them.

```bash
uv run pytest --cov
uv run ruff check src config tests final-testing conftest.py
uv run ruff format --check src config tests final-testing conftest.py
uv run mypy
```

`--cov` fails below 85 percent branch coverage.
mypy runs in strict mode over `src/` and `config/`.

The dashboard has its own lint and Jest suite, which CI also runs.

```bash
cd frontend
yarn lint
yarn test:coverage
```

`yarn test:coverage` renders the dashboard components with Testing Library against a mocked `fetch`, and fails below 85 percent line coverage of `src/lib/` and the chat components.

The tests marked `integration` drive a live server backed by real Gemini credentials, so they cost money and are skipped by default.
Start the server on port 8000 and run them with `uv run pytest -m integration`.
They send `TEST_API_KEY` as `x-api-key`, falling back to the evaluator's public key.

## API

| Method and path | Auth | Purpose |
|---|---|---|
| `POST /api/v1/analyze` | `x-api-key` | One evaluator turn, returns `status` and `reply`, or the summary on `[CONVERSATION_END]` |
| `POST /api/v1/analyze/detailed` | `x-api-key` | Full analysis for the dashboard, with verdict, scam type, confidence, intelligence and agent notes |
| `GET /health` | none | `{"status": "healthy"}` |
| `GET /metrics` | `x-api-key` | Prometheus metrics, see below |
| `GET /` | none | Static test UI from `src/static/index.html` |

The request body is `AnalyzeRequest` in `src/api/schemas.py`.
Malformed bodies get HTTP 200 with a "sorry, say again" reply instead of 422, because the evaluator scores a non-200 turn as zero.
The same reply goes to oversized bodies, meaning a message over 10,000 characters or more than 100 history entries.

### Metrics

`GET /metrics` serves Prometheus text from `src/metrics.py`, behind the same key check as the analyze routes.

| Metric | Labels | Counts |
|---|---|---|
| `sticky_net_http_requests_total` | `method`, `route`, `status` | Every request, including 401 and 403 replies |
| `sticky_net_http_request_duration_seconds` | `route` | Latency, with buckets up to the 30 second limit |
| `sticky_net_scam_verdicts_total` | `endpoint`, `scam_detected`, `scam_type` | Detector verdicts |
| `sticky_net_auth_failures_total` | `reason` | `missing` or `invalid` keys |
| `sticky_net_fallback_replies_total` | `reason` | Canned replies for malformed bodies, agent timeouts, empty replies and errors |
| `sticky_net_guvi_callbacks_total` | `outcome` | GUVI callbacks `sent`, `rejected` or `error` |

`route` holds the route template, and requests no route handled share `unrouted`, so odd URLs cannot add series.
Auth rejections and malformed bodies also log a warning with a `security_event` field.

### Error tracking

Set `ERROR_TRACKING_DSN` to a Sentry DSN to report errors from `src/error_tracking.py`.
The routes answer most failures with a canned 200 reply, so they report the exception themselves before replying.
Events go through the same credential masking as the logs, and without a DSN nothing is sent.

Scam types are `banking_fraud`, `job_offer`, `lottery_reward`, `impersonation` and `others`.

With `DEBUG=true`, requests without a key pass and CORS allows every origin.
The app refuses to start with `DEBUG=true` and `ENVIRONMENT=production`, so a stray flag cannot open a production deploy.
With `DEBUG=false`, the API requires `x-api-key` to match `API_KEY`.
The shared `test-api-key` the GUVI evaluator used is no longer accepted, since the hackathon has ended.
The middleware compares keys with `hmac.compare_digest`, so timing does not leak how much of a guess was right.

## Configuration

`config/settings.py` reads every setting from the environment or `.env`, case-insensitively.
[.env.example](.env.example) lists each variable with its default and what it does.
[frontend/.env.example](frontend/.env.example) does the same for the dashboard.

| Variable | Default | Notes |
|---|---|---|
| `API_KEY` | required | Shared key clients send as `x-api-key` |
| `API_KEY_FILE` | unset | Read the key from a mounted secret file, used when the plain variable is unset |
| `GOOGLE_CLOUD_PROJECT` | required | Vertex AI and Firestore project |
| `DEBUG` | `false` | Opens `/docs`, allows keyless requests and any CORS origin |
| `FLASH_MODEL`, `PRO_MODEL` | `gemini-3-flash-preview` | Classifier and agent models |
| `API_TIMEOUT_SECONDS` | `12` | Per-model Gemini timeout |
| `LOG_LEVEL`, `LOG_FORMAT` | `INFO`, `json` | `console` gives coloured local output |
| `GUVI_CALLBACK_ENABLED` | `true` | Set `false` locally so runs never post to the evaluator |
| `SESSION_CACHE_MAX_ENTRIES` | `10000` | Sessions kept in memory before the least recently used is dropped |
| `ERROR_TRACKING_DSN` | unset | Sentry DSN; caught route and callback errors are reported with route and session tags |

## Deployment

`cloudbuild.yaml` runs the tests, builds the image and deploys it to Cloud Run with `API_KEY` from Secret Manager.
`deploy-quick.sh` and `scripts/deploy-manual.sh` deploy an already-built image.
The dashboard deploys to Firebase Hosting from `frontend/build` per `firebase.json`.
Set `REACT_APP_API_URL` to the Cloud Run URL in `frontend/.env.production.local` before `yarn build`.

## Security

[SECURITY.md](SECURITY.md) covers how to report a vulnerability, where each secret lives and which controls the code has.
[docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) maps the trust boundaries, threats and residual risks.
The security tests live in `tests/security/`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
