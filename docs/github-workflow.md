# Publishing Kavach on GitHub — step-by-step

Everything below runs in **Git Bash** on Windows (or any macOS/Linux terminal).
Names used throughout (already filled in):

| What | Value |
|---|---|
| Organization | `Vertexx1-SIH2026` |
| Repository | `kavach` → `https://github.com/Vertexx1-SIH2026/Kavach` |
| Org owner | `RohaanAhmadQuadri` (your GitHub username) |

> Want a different repo name (e.g. `kavach-passwordless-idp`)? Replace `/kavach` after `Vertexx1-SIH2026` in
> `README.md` (CI badge + clone URL) and in this file.

> **The repository root is the inner `kavach/` folder** (the one containing `backend/`, `frontend/`, `README.md`).
> The outer folder's `Kavach-Project-Report.pdf` and `kavach-with-attack-lab.zip` are **not** part of the repo.
> To publish the report, copy it to `docs/Kavach-Project-Report.pdf` first. Never commit the zip.

---

## 1. GitHub Organization setup

### 1.1 Create the organization (free)

> Already created **Vertexx1-SIH2026**? Skip to 1.2.

1. Sign in as **RohaanAhmadQuadri** → open <https://github.com/account/organizations/new?plan=free>.
2. **Organization name:** `Vertexx1-SIH2026`.
3. **Contact email:** your email → **This organization belongs to: My personal account** → **Next**.
4. Skip "Add members" for now → **Complete setup**.
5. **Settings → Profile:** upload a logo (`docs/assets/banner.svg` exported as PNG works), add a description and website.

### 1.2 Harden member defaults

**Org → Settings → Member privileges**

| Setting | Value | Why |
|---|---|---|
| Base permissions | **Read** | Members get write access only through teams |
| Repository creation | Public + Private ✅ (or off) | Your call |
| Allow forking of private repositories | ❌ | Keep code inside the org |
| Repository deletion and transfer | ❌ | Only owners can delete |

**Org → Settings → Authentication security** → ✅ **Require two-factor authentication** (ask everyone to enable 2FA first, or they are removed).

### 1.3 Invite members

**Org → People → Invite member** → enter each teammate's GitHub username → role **Member** (keep yourself as the only **Owner**, plus one backup owner).

### 1.4 Create teams

**Org → Teams → New team** (visibility: *Visible*).

**Option A — 3-member team**

| Team | Members | Repo permission |
|---|---|---|
| `maintainers` | Lead (you) | **Admin** |
| `developers` | The other 2 | **Write** |

**Option B — 6-member team**

| Team | Members | Repo permission |
|---|---|---|
| `maintainers` | Lead + 1 co-lead | **Admin** / **Maintain** |
| `backend` | 2 (FastAPI, security tests) | **Write** |
| `frontend` | 2 (Next.js UI, portals) | **Write** |
| `docs-demo` | 1 (README, report, demo) | **Triage** |

Use a parent team `core` with the others as child teams if you want one `@Vertexx1-SIH2026/core` mention for everyone.

### 1.5 Create the repository

**Org → Repositories → New repository**

- Owner: **Vertexx1-SIH2026** · Name: **`kavach`**
- Description: *Passwordless sign-in for every website — FIDO2 passkeys + OpenID Connect, with safe assisted sign-in.*
- Visibility: **Public** *(see the note in section 4 — branch protection on private repos needs a paid plan)*
- ❗ **Do NOT** tick "Add a README", ".gitignore" or "license" — the project already has them, and an empty repo avoids a merge conflict on the first push.

Then **Repo → Settings → Collaborators and teams → Add teams** and give each team the permission from the table above.

### 1.6 (Optional) `gh` CLI equivalent

```bash
gh auth login
gh repo create Vertexx1-SIH2026/Kavach --public \
  --description "Passwordless sign-in for every website — FIDO2 passkeys + OpenID Connect"
gh api -X PUT orgs/Vertexx1-SIH2026/teams/developers/repos/Vertexx1-SIH2026/Kavach -f permission=push
gh api -X PUT orgs/Vertexx1-SIH2026/teams/maintainers/repos/Vertexx1-SIH2026/Kavach -f permission=admin
```

(`push` = Write, `maintain`, `admin`, `triage`, `pull` = Read. Teams must already exist.)

---

## 2. Local cleanup & `.gitignore`

The repo already has a root [`.gitignore`](../.gitignore) that excludes `.env` / `.env.local`, `*.pem` signing keys,
`.venv*/`, `node_modules/`, `.next/`, caches and OS files, while keeping every `.env.example`.

```bash
cd "/c/Users/rohaa/OneDrive/Desktop/kavach/kavach"

# Optional: free disk space and remove build caches (all regenerable)
rm -rf frontend/.next portals/college-portal/.next
find . -name "__pycache__" -type d -prune -exec rm -rf {} +
rm -rf backend/.pytest_cache

# Old, unused virtual environment in the citizen portal (setup.bat uses .venv)
rm -rf portals/citizen-portal/.venv-new
```

Make sure the `.env.example` templates exist (they do) and real `.env` files stay local:

```bash
ls backend/.env.example frontend/.env.example \
   portals/college-portal/.env.example portals/citizen-portal/.env.example
```

> `backend/seed_clients.json` contains the **demo** client secrets (`*-dev-secret`) that the portals
> use. They are intentionally public and only valid on localhost. Rotate them with
> `python -m app.cli register-client` for any real deployment.

---

## 3. Git initialization & first commit

### 3.1 One-time Git identity

```bash
git config --global user.name  "Rohaan Ahmad Quadri"
git config --global user.email "you@example.com"     # the email on your GitHub account
git config --global init.defaultBranch main
git config --global core.autocrlf true               # Windows: LF in repo, CRLF on disk
```

### 3.2 Fill in the Team table

The org name is already set in `README.md`. Edit the **Team** table there with your teammates' names,
roles and GitHub usernames (the rows marked `Member Name` / `@USERNAME`) before the first commit.

### 3.3 Initialize and verify nothing secret is staged

```bash
git init -b main
git add .

# Must print NOTHING — if it lists a file, run: git rm --cached <file>
git diff --cached --name-only | grep -E '(^|/)\.env$|\.env\.local$|\.pem$|node_modules/|\.venv|\.next/'

git status --short | head -50       # review what will be committed (~120 files)
```

### 3.4 Commit (Conventional Commits)

```bash
git commit -m "feat: initial project setup" \
  -m "Kavach passwordless identity provider: FastAPI + PostgreSQL backend, Next.js UI,
two OIDC demo portals, assisted sign-in, recovery, attack lab, security test suite and CI."
```

### 3.5 Link the remote and push

```bash
git remote add origin https://github.com/Vertexx1-SIH2026/Kavach.git
git push -u origin main

# Integration branch for day-to-day work
git switch -c develop
git push -u origin develop
git switch main
```

If Git asks for a password, sign in through the browser window Git Credential Manager opens
(or run `gh auth login` first). GitHub no longer accepts account passwords over HTTPS.

### 3.6 Polish the repo page

**Repo → ⚙ (About)** → add description, website, and topics:
`passkeys` `webauthn` `fido2` `openid-connect` `oidc` `identity-provider` `fastapi` `nextjs` `passwordless` `cybersecurity` `hackathon`

**Repo → Settings → General**
- Features: ✅ Issues, ✅ Projects (for the roadmap), ❌ Wiki
- Pull Requests: ✅ Allow squash merging only, ✅ Always suggest updating PR branches, ✅ Automatically delete head branches

### 3.7 Daily team workflow

```bash
git switch develop && git pull
git switch -c feat/sms-gateway
# ...work...
git add -A && git commit -m "feat(recovery): send OTP through SMS gateway"
git push -u origin feat/sms-gateway
gh pr create --base develop --fill        # or open the PR on github.com
```

Release / submission: open a PR **`develop` → `main`**, merge it, then tag:

```bash
git switch main && git pull
git tag -a v1.0.0 -m "CyberCup 6.0 submission"
git push origin v1.0.0
gh release create v1.0.0 --title "Kavach v1.0.0" --notes "Hackathon submission build"
```

---

## 4. Branch protection

> **Plan note:** branch protection and rulesets are free on **public** repositories. On a **private**
> repo in a Free organization they are not enforced — upgrade to GitHub Team, or apply for the free
> [GitHub Education / Team for students](https://education.github.com/) benefit.

Push once and let the **CI** workflow run (Actions tab) so its checks appear in the dropdowns below.

**Repo → Settings → Rules → Rulesets → New ruleset → New branch ruleset**

### Ruleset `protect-main`

- Enforcement status: **Active** · Target branches: **Include default branch** (`main`)
- Bypass list: `maintainers` team (*for PRs only*) — keep it empty for strictest setup
- ✅ Restrict deletions
- ✅ Block force pushes
- ✅ Require linear history
- ✅ **Require a pull request before merging**
  - Required approvals: **1** (3-member team) / **2** (6-member team)
  - ✅ Dismiss stale pull request approvals when new commits are pushed
  - ✅ Require approval of the most recent reviewable push
  - ✅ Require conversation resolution before merging
  - Allowed merge methods: **Squash**
- ✅ **Require status checks to pass** → ✅ *Require branches to be up to date* → add:
  - `Backend security tests`
  - `Build frontend`
  - `Build portals/college-portal`

### Ruleset `protect-develop`

- Target branches: **Include by pattern** → `develop`
- ✅ Restrict deletions · ✅ Block force pushes
- ✅ Require a pull request before merging → approvals: **1**, dismiss stale approvals ✅
- ✅ Require status checks to pass → `Backend security tests`

### (Optional) Code owners

Create `.github/CODEOWNERS` once the teams exist, then tick **Require review from Code Owners** in `protect-main`:

```
*               @Vertexx1-SIH2026/maintainers
/backend/       @Vertexx1-SIH2026/backend
/frontend/      @Vertexx1-SIH2026/frontend
/portals/       @Vertexx1-SIH2026/frontend
/docs/          @Vertexx1-SIH2026/docs-demo
```

### (Optional) Classic branch protection via `gh`

```bash
gh api -X PUT repos/Vertexx1-SIH2026/Kavach/branches/main/protection --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["Backend security tests", "Build frontend", "Build portals/college-portal"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
JSON
```

### Extra security toggles (Repo → Settings → Code security)

- ✅ Dependabot alerts and security updates
- ✅ Secret scanning + **Push protection** (blocks accidental key/token pushes)
- ✅ Private vulnerability reporting
