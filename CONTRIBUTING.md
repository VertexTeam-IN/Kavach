# Contributing to Kavach

## Workflow

1. Branch from `develop`: `git switch develop && git pull && git switch -c feat/short-description`
2. Commit with [Conventional Commits](https://www.conventionalcommits.org/):
   `feat:` new feature · `fix:` bug fix · `docs:` docs only · `test:` tests · `refactor:` · `chore:` · `ci:`
3. Run the security tests: `cd backend && python -m pytest -v`
4. Push and open a Pull Request into `develop`. At least one approving review is required.
5. `develop` is merged into `main` for releases / submission builds.

## Branch names

`feat/…`, `fix/…`, `docs/…`, `test/…`, `chore/…`

## Rules

- Never commit `.env`, `.env.local` or `*.pem` files — use the `.env.example` templates.
- Keep passkey URLs on `http://localhost:3000` (not `127.0.0.1`).
- Security-relevant changes need a matching test in `backend/tests/test_security.py`.
