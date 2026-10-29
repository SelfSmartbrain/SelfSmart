# 🤖 junior-engineer-bot

**Autonomous Junior Engineering Agent**

An end-to-end autonomous agent that handles failing CI builds, parses error logs, reproduces bugs in a sandbox, generates fixes (deterministic rule fixers or LLM fallback), verifies passes, checks strict safety guardrails, and opens clean Pull Requests.

---

## 🚀 Easy Ways to Run

### 🌟 Way 1: Zero-Server GitHub Actions (Simplest!)
No server to host, no ports to open, and no private keys to generate. 

Just copy the workflow template from [`workflows/agent-fix.yml`](workflows/agent-fix.yml) to your repository's `.github/workflows/` directory. Whenever a test or CI build fails, GitHub Actions automatically runs the Junior Engineer in the cloud, diagnoses the error, writes a fix, and opens a Pull Request!

---

### 🔑 Way 2: Local CLI with Standard `GITHUB_TOKEN`
No need for a complex GitHub App setup. Use a standard GitHub Personal Access Token (`ghp_...`):

```bash
export GITHUB_TOKEN="ghp_your_token_here"
export ANTHROPIC_API_KEY="your_anthropic_key"

# Automatically fix a failed CI run directly from your terminal:
junior-engineer-bot fix --repo "owner/repo" --run-id 123456789
```

---

### 💻 Way 3: 100% Local Audit (No GitHub Needed)
Scan any folder or project on your computer for vulnerabilities, bugs, and missing tests:

```bash
junior-engineer-bot audit /path/to/any/repo -o AUDIT_REPORT.md
```

---

### 🌐 Way 4: Webhook Server (GitHub App Mode)
For real-time webhook events on an external server:

```bash
export GITHUB_APP_ID="123456"
export GITHUB_PRIVATE_KEY="$(cat key.pem)"
export GITHUB_WEBHOOK_SECRET="your-secret"
export ANTHROPIC_API_KEY="your-key"

junior-engineer-bot serve --port 8000
```
