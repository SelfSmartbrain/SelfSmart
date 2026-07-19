# 🚀 SelfSmart AI - Production Deployment Guide

## 📋 Overview

This guide covers deploying the SelfSmart AI platform to production environments with enterprise-grade configuration, monitoring, and security.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx/Ingress │────│  SelfSmart API  │────│   PostgreSQL    │
│   (Port 80/443) │    │  (Port 8000)    │    │   (Port 5432)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                    ┌─────────────────┐    ┌─────────────────┐
                    │     Redis       │    │     Qdrant      │
                    │   (Port 6379)   │    │   (Port 6333)   │
                    └─────────────────┘    └─────────────────┘
                              │
                    ┌─────────────────┐
                    │   Frontend      │
                    │  (Next.js 3000) │
                    └─────────────────┘
```

## 🎯 Deployment Options

### Option 1: Docker Compose (Recommended for Single Server)

**Quick Start:**
```bash
# 1. Clone and setup
git clone <your-repo>
cd selfsmart

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys and strong passwords

# 3. Deploy
docker compose up -d
```

### Option 2: Kubernetes (Production)

```bash
# Apply manifests
kubectl apply -f infrastructure/kubernetes/

# Check status
kubectl get pods -n selfsmart
kubectl get svc -n selfsmart
```

### Option 3: Cloud Platform Deployment

#### Render / Fly.io / Railway
1. Connect your GitHub repository
2. Set environment variables in dashboard
3. Deploy automatically

#### AWS ECS / Google Cloud Run / Azure Container Apps
```bash
# Build and push
docker build -t selfsmart-ai .
docker tag selfsmart-ai:latest <registry>/selfsmart-ai:latest
docker push <registry>/selfsmart-ai:latest

# Deploy via platform CLI
```

## 🔧 Configuration

### Required Environment Variables

```bash
# Application
APP_NAME="SelfSmart AI"
ENV=production
DEBUG=false
JSON_LOGS=true
SECRET_KEY=<generate-with-python3-c-import-secrets-print-secrets-token-hex-32>

# LLM Provider (choose one)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key
# DEEPSEEK_API_KEY=your_deepseek_key
# OPENROUTER_API_KEY=your_openrouter_key

# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Cache
REDIS_URL=redis://localhost:6379/0

# Security
CORS_ORIGINS=https://yourdomain.com
```

### Optional Configuration

```bash
# Proxy Settings (if needed)
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=https://proxy.company.com:8080

# Performance
MAX_WORKERS=4
REQUEST_TIMEOUT=60

# Security
RATE_LIMIT_PER_MINUTE=60

# Monitoring
PROMETHEUS_ENABLED=true
SENTRY_DSN=
```

## 📦 Docker Deployment

### Build Production Image
```bash
docker build -t selfsmart-ai:latest .
```

### Run with Docker Compose
```bash
# Production deployment
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f api
```

### Manual Docker Run
```bash
docker run -d \
  --name selfsmart-api \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db \
  -e SECRET_KEY=your-secret-key \
  -e GEMINI_API_KEY=your-key \
  -v $(pwd)/data:/app/data \
  selfsmart-ai:latest
```

## 🔒 Security Configuration

### SSL/TLS Setup

1. **Let's Encrypt (recommended):**
```bash
certbot certonly --standalone -d yourdomain.com

# Copy to nginx
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/key.pem
```

2. **Self-signed (development):**
```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/key.pem \
  -out nginx/cert.pem
```

### Security Headers (configured in nginx/ingress)
- HTTPS enforcement with HSTS
- XSS protection
- Content type protection
- Frame protection
- Referrer policy

### Rate Limiting
- Auth endpoints: 3-5 requests/minute
- Chat endpoints: 20 requests/minute
- Configurable per IP address

## 📊 Monitoring & Health Checks

### Health Endpoints
- **Liveness**: `GET /health` - basic service status
- **Readiness**: `GET /health/ready` - dependency connectivity
- **Detailed**: `GET /health/detailed` - component status

### Monitoring Setup

#### Prometheus + Grafana (included in docker-compose)
```bash
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (admin / GRAFANA_PASSWORD)
```

#### Metrics Available
- HTTP request rate, latency, errors
- Database connection pool
- Redis memory/operations
- Celery queue depth
- LLM API call metrics

#### Log Aggregation
```bash
# View application logs
docker compose logs -f api

# Structured JSON logs (when JSON_LOGS=true)
docker compose logs api | jq .
```

## 🚀 Performance Optimization

### Resource Allocation (Docker Compose)
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '0.5'
      memory: 1G
```

### Kubernetes Resources
```yaml
resources:
  requests:
    cpu: 250m
    memory: 512Mi
  limits:
    cpu: "1"
    memory: 1Gi
```

### Horizontal Scaling
```bash
# Docker Compose
docker compose up -d --scale api=3

# Kubernetes (HPA configured)
kubectl autoscale deployment selfsmart-backend --cpu-percent=70 --min=2 --max=10
```

### Caching
- Redis: Session storage, rate limiting, response caching
- Application-level: In-memory LLM response cache

## 🔄 CI/CD Pipeline

### GitHub Actions (`.github/workflows/ci.yml`)
```yaml
name: CI
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python: ["3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - run: pip install -e ".[dev]"
      - run: ruff check src/ modelx_voice/
      - run: black --check src/ modelx_voice/
      - run: mypy src/ --ignore-missing-imports
      - run: pytest tests/ -v --cov=src --cov=modelx_voice

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm run build

  build:
    needs: [test, frontend]
    runs-on: ubuntu-latest
    if: github.event_name == 'release' || github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t selfsmart-ai .
      - run: docker push registry/selfsmart-ai:latest
```

## 🛠️ Troubleshooting

### Common Issues

1. **Import Errors**
   - Check Python dependencies in `pyproject.toml`
   - Verify all files copied correctly in Docker

2. **API Key Issues**
   - Ensure `SECRET_KEY`, `GEMINI_API_KEY` (or `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`) are set
   - Check for typos in environment variables

3. **Network Issues**
   - Check firewall settings
   - Verify proxy configuration
   - Test with: `curl http://localhost:8000/health`

4. **Database Connection**
   - Verify `DATABASE_URL` format: `postgresql+asyncpg://user:pass@host:5432/db`
   - Run migrations: `alembic upgrade head`

5. **Memory Issues**
   - Increase memory limits in docker-compose/k8s
   - Monitor with `docker stats` or `kubectl top pods`

### Debug Commands

```bash
# Check container status
docker ps
kubectl get pods -n selfsmart

# View logs
docker logs selfsmart-api
kubectl logs -n selfsmart deployment/selfsmart-backend

# Enter container for debugging
docker exec -it selfsmart-api bash
kubectl exec -it -n selfsmart deployment/selfsmart-backend -- bash

# Test API endpoints
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"email":"test@test.com","password":"pass"}'
```

## 📱 API Access

Once deployed, your service will be available at:

- **Main API**: `https://yourdomain.com`
- **Health Check**: `https://yourdomain.com/health`
- **API Docs**: `https://yourdomain.com/docs` (disabled in production)
- **Frontend**: `https://yourdomain.com` (served by Next.js)

### API Usage Examples

```bash
# Health check
curl https://yourdomain.com/health

# Register user
curl -X POST "https://yourdomain.com/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecureP@ss123"}'

# Login
curl -X POST "https://yourdomain.com/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecureP@ss123"}'

# Chat (requires Bearer token)
curl -X POST "https://yourdomain.com/api/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"message": "Hello, SelfSmart AI!"}'
```

## 🎯 Best Practices

1. **Environment Management**
   - Use separate `.env` files for each environment
   - Never commit API keys to version control
   - Rotate secrets periodically

2. **Security**
   - Always use HTTPS in production
   - Implement rate limiting
   - Monitor logs for suspicious activity
   - Keep dependencies updated

3. **Performance**
   - Monitor resource usage (CPU, memory, disk)
   - Implement caching strategies
   - Use CDN for static assets (Next.js handles this)

4. **Reliability**
   - Set up health checks and alerts
   - Configure automatic restarts
   - Implement backup strategies for PostgreSQL/Qdrant

5. **Observability**
   - Enable structured JSON logging
   - Set up Prometheus + Grafana dashboards
   - Configure alerting for error rates, latency, resource usage

---

**🎉 Your SelfSmart AI platform is now ready for production deployment!**