# Security policy

Sticky-Net talks to scammers on purpose.
Every message it receives is hostile input, and every reply it sends goes to an attacker.
This file says how to report a problem and which controls the code has.
[docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) has the full threat model.

## Reporting a vulnerability

Open a private advisory at https://github.com/heyitsgautham/sticky-net/security/advisories/new, or email heyitsgautham@gmail.com.
Please do not open a public issue for anything that exposes keys, intelligence data or a way to run up Gemini costs.
Include the request you sent, the response you got and the commit you tested.

## Supported versions

Only the latest release and `main` get fixes.
The deployed API runs from `main`.

## Secrets

| Secret | Where it lives in production | Where it lives locally |
|---|---|---|
| `API_KEY` | Secret Manager secret `sticky-net-api-key`, injected by `--set-secrets` in `cloudbuild.yaml` and `deploy-quick.sh` | `.env`, which git ignores |
| Google credentials | The Cloud Run service account, through application default credentials | `gcloud auth application-default login`, or a key file under `secrets/`, which git ignores |
| `ERROR_TRACKING_DSN` | A Cloud Run environment variable | `.env` |

`API_KEY_FILE` reads the key from a mounted file instead of an environment variable.
`config/secret_files.py` implements this, and a missing or empty file stops startup with an error that names the path but not the contents.

The API used to accept a second, public key, `test-api-key`, for the GUVI evaluator.
The hackathon has ended, so the API accepts only `API_KEY`, and the dashboard sends a key only when its build sets `REACT_APP_API_KEY`.
Rotate `API_KEY` if it was ever shared with the evaluator.

`REACT_APP_*` values are compiled into the dashboard's JavaScript, so anything placed there is public.

## Controls in the code

| Control | Where | Test |
|---|---|---|
| API key check with `hmac.compare_digest` on every accepted key | `src/api/auth.py`, `src/api/middleware.py` | `tests/security/test_auth.py` |
| Startup fails on `DEBUG=true` with `ENVIRONMENT=production` | `config/settings.py` | `tests/security/test_debug_guard.py` |
| Request size limits, 10,000 characters per message and 100 history entries | `src/api/schemas.py` | `tests/test_request_limits.py` |
| No exception text in any response body | `src/main.py`, `src/api/routes.py` | `tests/security/test_error_disclosure.py` |
| `nosniff`, `DENY` framing, `no-referrer`, and `no-store` plus a deny-all CSP on JSON routes | `SecurityHeadersMiddleware` in `src/api/middleware.py` | `tests/security/test_security_headers.py` |
| Keys, tokens and `Authorization` values masked in logs and error reports | `src/log_redaction.py`, `src/error_tracking.py` | `tests/security/test_log_redaction.py`, `tests/test_error_tracking.py` |
| Extraction regexes run in linear time on hostile input | `src/intelligence/extractor.py` | `tests/security/test_regex_performance.py` |
| Per-client rate limit with 429 and `Retry-After`, keyed by valid API key or address | `RateLimitMiddleware` in `src/api/middleware.py`, `src/api/rate_limit.py` | `tests/security/test_rate_limit.py` |
| Session caches capped with LRU eviction | `src/api/bounded_cache.py` | `tests/security/test_session_memory.py` |
| LLM output parsed into a pydantic model and each value re-checked by regex validators | `src/agents/reply_parser.py`, `src/intelligence/` | `tests/test_reply_parser.py`, `tests/test_validators.py` |
| Auth failures and malformed bodies counted and logged with a `security_event` field | `src/metrics.py`, `src/api/middleware.py`, `src/main.py` | `tests/test_metrics.py` |

CI runs gitleaks over the full history, `pip-audit` on the locked Python dependencies and `yarn audit` on the dashboard on every push and pull request.
Dependabot opens weekly updates for uv, Yarn, GitHub Actions and the Docker base image.

## Deliberate trade-offs

The GUVI evaluator scored any non-200 reply as zero.
These choices date from the hackathon and are not bugs.

- Malformed and oversized bodies get HTTP 200 with a "say again" reply instead of 422.
  The `sticky_net_fallback_replies_total{reason="malformed_request"}` counter and a `security_event=malformed_request` log line keep them visible.
- Gemini safety filters are set to `BLOCK_NONE` in `src/agents/honeypot_agent.py`, because the persona must keep talking to someone describing fraud.
  The agent has no tools and can only return text, so a prompt injection can change what the persona says but cannot reach any other system.
