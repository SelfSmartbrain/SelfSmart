# 🚀 SmartShelf AI Chat Service - Production Deployment Guide

## 📋 Overview

This guide covers deploying the SmartShelf AI Chat Service to production environments with enterprise-grade configuration, monitoring, and security.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │────│  SmartShelf AI  │────│   Redis Cache   │
│   (Port 80/443) │    │  (Port 8001)    │    │  (Port 6379)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                    ┌─────────────────┐
                    │ Persistent Data │
                    │   (Volumes)     │
                    └─────────────────┘
```

## 🎯 Deployment Options

### Option 1: Docker Compose (Recommended for Single Server)

**Quick Start:**
```bash
# 1. Clone and setup
git clone <your-repo>
cd smartshelf-ai

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Deploy
./scripts/deploy-production.sh
```

### Option 2: Cloud Platform Deployment

#### Render (Easiest)
1. Connect your GitHub repository to Render
2. Set environment variables in Render dashboard
3. Deploy automatically

#### AWS ECS/Fargate
```bash
# Build and push to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-west-2.amazonaws.com
docker build -f Dockerfile.prod -t smartshelf-chat .
docker tag smartshelf-chat:latest <account-id>.dkr.ecr.us-west-2.amazonaws.com/smartshelf-chat:latest
docker push <account-id>.dkr.ecr.us-west-2.amazonaws.com/smartshelf-chat:latest

# Deploy with ECS
aws ecs create-service --cluster smartshelf --service-name chat-service --task-definition smartshelf-chat
```

#### Google Cloud Run
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT-ID/smartshelf-chat
gcloud run deploy smartshelf-chat --image gcr.io/PROJECT-ID/smartshelf-chat --platform managed
```

#### Azure Container Instances
```bash
# Create resource group and deploy
az group create --name smartshelf-rg --location eastus
az container create \
  --resource-group smartshelf-rg \
  --name smartshelf-chat \
  --image smartshelf-chat:latest \
  --ports 8001 \
  --environment-variables OPENAI_API_KEY=$OPENAI_API_KEY DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY
```

## 🔧 Configuration

### Required Environment Variables

```bash
# API Keys (Required - use one)
OPENAI_API_KEY=sk-your-openai-key
DEEPSEEK_API_KEY=sk-your-deepseek-key

# Service Configuration
DEBUG=false
LOG_LEVEL=info
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
CORS_ORIGINS=https://yourdomain.com
RATE_LIMIT_PER_MINUTE=60
```

## 📦 Docker Deployment

### Build Production Image
```bash
docker build -f Dockerfile.prod -t smartshelf-chat:latest .
```

### Run with Docker Compose
```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Manual Docker Run
```bash
docker run -d \
  --name smartshelf-chat \
  -p 8001:8001 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY \
  -v $(pwd)/data:/app/data \
  smartshelf-chat:latest
```

## 🔒 Security Configuration

### SSL/TLS Setup

1. **Generate SSL certificates:**
```bash
# Using Let's Encrypt
certbot certonly --standalone -d yourdomain.com

# Copy certificates to nginx directory
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/key.pem
```

2. **Self-signed certificates (for development):**
```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/key.pem \
  -out nginx/cert.pem
```

### Security Headers

The Nginx configuration includes:
- HTTPS enforcement with HSTS
- XSS protection
- Content type protection
- Frame protection
- Referrer policy

### Rate Limiting

- Chat endpoints: 5 requests/second
- API endpoints: 10 requests/second
- Configurable per IP address

## 📊 Monitoring & Health Checks

### Health Endpoints

- **Service Health**: `GET /health`
- **Nginx Health**: `GET /health` (port 80/443)
- **Docker Health**: Built-in container health checks

### Monitoring Setup

#### Prometheus Metrics (Optional)
```yaml
# Add to docker-compose.prod.yml
prometheus:
  image: prom/prometheus
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

#### Log Aggregation
```bash
# View application logs
docker-compose -f docker-compose.prod.yml logs smartshelf-chat

# View nginx logs
docker-compose -f docker-compose.prod.yml logs nginx
```

## 🚀 Performance Optimization

### Resource Allocation

```yaml
# In docker-compose.prod.yml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '0.5'
      memory: 1G
```

### Scaling

#### Horizontal Scaling
```bash
# Scale to multiple instances
docker-compose -f docker-compose.prod.yml up -d --scale smartshelf-chat=3
```

#### Load Balancing
Nginx automatically load balances between multiple instances.

### Caching

Redis cache is included for:
- Session storage
- Response caching
- Rate limiting data

## 🔄 CI/CD Pipeline

### GitHub Actions Example

```yaml
name: Deploy Production
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Build and push Docker image
        run: |
          docker build -f Dockerfile.prod -t smartshelf-chat .
          docker push ${{ secrets.DOCKER_REGISTRY }}/smartshelf-chat

      - name: Deploy to production
        run: |
          curl -X POST ${{ secrets.DEPLOY_WEBHOOK }}
```

## 🛠️ Troubleshooting

### Common Issues

1. **Import Errors**
   - Check Python dependencies in requirements.txt
   - Verify all files are copied correctly

2. **API Key Issues**
   - Ensure OPENAI_API_KEY or DEEPSEEK_API_KEY is set
   - Check for typos in environment variables

3. **Network Issues**
   - Check firewall settings
   - Verify proxy configuration
   - Test with curl: `curl http://localhost:8001/health`

4. **Memory Issues**
   - Increase memory limits in docker-compose
   - Monitor with `docker stats`

### Debug Commands

```bash
# Check container status
docker ps

# View logs
docker logs smartshelf-chat

# Enter container for debugging
docker exec -it smartshelf-chat bash

# Test API endpoints
curl http://localhost:8001/health
curl -X POST http://localhost:8001/chat -H "Content-Type: application/json" -d '{"query":"test"}'
```

## 📱 API Access

Once deployed, your service will be available at:

- **Main API**: `https://yourdomain.com`
- **Health Check**: `https://yourdomain.com/health`
- **API Docs**: `https://yourdomain.com/docs`
- **Direct Chat**: `https://yourdomain.com/chat`

### API Usage Examples

```bash
# Health check
curl https://yourdomain.com/health

# Chat with AI
curl -X POST "https://yourdomain.com/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "What products do you recommend?"}'

# Product suggestions
curl -X POST "https://yourdomain.com/products/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "Recommend electronics"}'
```

## 🎯 Best Practices

1. **Environment Management**
   - Use separate .env files for each environment
   - Never commit API keys to version control

2. **Security**
   - Always use HTTPS in production
   - Implement rate limiting
   - Monitor logs for suspicious activity

3. **Performance**
   - Monitor resource usage
   - Implement caching strategies
   - Use CDN for static assets

4. **Reliability**
   - Set up health checks
   - Configure automatic restarts
   - Implement backup strategies

## 📞 Support

For deployment issues:
1. Check the troubleshooting section
2. Review container logs
3. Verify environment configuration
4. Test API endpoints manually

---

**🎉 Your SmartShelf AI Chat Service is now ready for global production deployment!**
