# 🤖 junior-engineer-bot

**Autonomous Junior Engineering Agent**

An end-to-end autonomous agent that handles failing CI builds, parses error logs, reproduces bugs in a sandbox, generates fixes (deterministic rule fixers or LLM fallback), verifies passes, checks strict safety guardrails, and opens clean Pull Requests.

## 🚀 Quick Install

### Method 1: Install with pip
```bash
# Direct local installation
pip install -e ./junior-agent

# Or directly from your GitHub repository
pip install git+https://github.com/your-username/junior-engineer-bot.git
```

### Method 2: Run directly with pipx
```bash
pipx run junior-engineer-bot --help
```

---

## 💻 Commands

### 1. Audit Any Project Path
```bash
junior-engineer-bot audit /path/to/any/repo -o AUDIT_REPORT.md
```

### 2. Start Webhook Listener (GitHub App)
```bash
export GITHUB_APP_ID="123456"
export GITHUB_PRIVATE_KEY="$(cat key.pem)"
export GITHUB_WEBHOOK_SECRET="your-secret"
export ANTHROPIC_API_KEY="your-key"

junior-engineer-bot serve --port 8000
```
