"""
Role: one place for secrets and safety limits. Every limit here is a guardrail you can tune.
"""

import os

# Secrets and credentials (with defaults/fallbacks for test safety)
APP_ID = os.environ.get('GITHUB_APP_ID', '123456')
PRIVATE_KEY = os.environ.get('GITHUB_PRIVATE_KEY', '')
WEBHOOK_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET', 'test-secret')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
MODEL = os.environ.get('MODEL', 'claude-3-5-sonnet-20241022')

# Safety Limits and Guardrails
MAX_FILES = 5
MAX_LINES = 150
MAX_ATTEMPTS = 3
MAX_LLM_STEPS = 12
SANDBOX_TIMEOUT = 600
BRANCH_PREFIX = 'agent/'
BLOCKED_PATHS = ('.github/', 'migrations/', 'infra/', 'auth/', '.env')
DB_PATH = os.environ.get('DB_PATH', 'agent.db')

# Sandbox execution controls
USE_DOCKER = os.environ.get('USE_DOCKER', 'true').lower() in ('true', '1', 'yes')
