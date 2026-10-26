# Contributing to Sticky-Net

## Set up

```bash
uv sync --extra dev
cp .env.example .env
```

For the dashboard, run `yarn install --frozen-lockfile` inside `frontend/`.

## Before you push

Run the same checks CI runs.

```bash
uv run ruff check src config tests final-testing conftest.py
uv run ruff format --check src config tests final-testing conftest.py
uv run mypy
uv run pytest --cov
```

For the dashboard, run these inside `frontend/`.

```bash
yarn lint
yarn format:check
yarn test:coverage
```

`yarn format` rewrites files with Prettier.
ESLint and Prettier skip `src/components/ui/` and `src/hooks/use-toast.js`, which the shadcn/ui CLI generates.

CI also builds the frontend, runs `pip-audit` and `yarn audit`, scans history with gitleaks and builds the Docker image.
The workflow is `.github/workflows/ci.yml`.

## Tests

- Every behaviour change lands with a test that fails without it.
- Tests stay offline.
  The root `conftest.py` swaps in a fake Gemini client and disables Firestore and the GUVI callback.
  To script an LLM reply, set `offline_services.models.generate_content` in your test, as `tests/test_classifier.py` does.
- Route tests patch `src.api.routes.get_detector` and `src.api.routes.get_agent`, since the routes call those getters.
- Anything that needs a live server or real credentials gets `@pytest.mark.integration` and stays out of the default run.
- Branch coverage must stay at or above 85 percent.

## Dependencies

- Python dependencies live in `pyproject.toml` and are locked in `uv.lock`.
  After changing them, run `uv lock`, then regenerate `requirements.txt`.

  ```bash
  uv export --frozen --no-hashes --no-emit-project --extra dev -o requirements.txt
  ```

  CI fails if `requirements.txt` and `uv.lock` disagree.
- Frontend dependencies use Yarn 1 and `frontend/yarn.lock` only.
  Do not add a `package-lock.json`.

## Code style

- ruff handles lint and formatting, with a 100 character line limit.
- `src/` and `config/` pass `mypy --strict`, and new code should too.
- Log through `structlog.get_logger()` with key-value fields, not f-strings, so JSON logs stay queryable.
- Keep files under 500 lines.
  Split by responsibility, as `src/intelligence/patterns.py` and `src/api/final_output.py` do.

## Commits

- Write [Conventional Commits](https://www.conventionalcommits.org/) subjects, such as `fix(api): keep sessionId on the final turn`.
- Keep one change per commit, with its tests in the same commit.
- Keep formatting-only changes in their own commit.

## Secrets

- Never commit `.env` files, service account keys or tokens.
  `.gitignore` covers `.env`, `.env.*` and `secrets/`.
- Add every new environment variable to `.env.example` or `frontend/.env.example` with a placeholder.
