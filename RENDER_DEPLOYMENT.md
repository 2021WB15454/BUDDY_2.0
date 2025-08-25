# 🚀 BUDDY 2.0 Render Deployment Guide

## Quick Render Deployment

### Step 1: Prerequisites
- GitHub repository with BUDDY 2.0 code
- Render account (https://render.com)
- MongoDB Atlas cluster
- Pinecone account

### Step 2: Environment Variables Setup
In your Render dashboard, set these environment variables:

```bash
# Core Configuration
BUDDY_ENV=production
BUDDY_DEBUG=0
NODE_ENV=production
PORT=10000

# Database Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/buddy_production
USE_MONGODB=1
MONGODB_DATABASE=buddy_production

# Vector Database
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX=buddy-production
USE_VECTOR_MEMORY=1

# Security
BUDDY_JWT_SECRET=your-secure-jwt-secret
ACCESS_TOKEN_EXPIRY=15m
REFRESH_TOKEN_EXPIRY=7d

# APIs
WEATHER_API_KEY=ff2cbe677bbfc325d2b615c86a20daef
OPENAI_API_KEY=your_openai_api_key
```

### Step 3: Deploy to Render

#### Option A: Using Render Dashboard
1. Go to https://render.com/dashboard
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: buddy-2-0-api
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn enhanced_backend:app --host 0.0.0.0 --port $PORT --worker-class uvicorn.workers.UvicornWorker`
   - **Instance Type**: Starter (or higher for production)

#### Option B: Using render.yaml (Infrastructure as Code)
1. The `render.yaml` file is already configured
2. Connect your repository to Render
3. Render will automatically detect and deploy using the configuration

### Step 4: Health Check
After deployment, verify the service is running:
```bash
curl https://your-app-name.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "message": "BUDDY Backend API with MongoDB is running",
  "database": {
    "status": "connected",
    "ping": true
  }
}
```

### Step 5: Test API Endpoints
```bash
# Test conversation endpoint
curl -X POST https://your-app-name.onrender.com/conversation \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello BUDDY!"}'

# Test voice endpoint
curl https://your-app-name.onrender.com/voice/status
```

## Troubleshooting

### Common Issues

1. **Build fails with "Could not open requirements file"**
   - Solution: Ensure `requirements.txt` exists in root directory ✅ (Fixed)

2. **MongoDB connection fails**
   - Check MONGODB_URI environment variable
   - Ensure MongoDB Atlas allows connections from Render IPs (0.0.0.0/0)
   - Verify database credentials

3. **Application won't start**
   - Check Start Command: `gunicorn enhanced_backend:app --host 0.0.0.0 --port $PORT --worker-class uvicorn.workers.UvicornWorker`
   - Verify `app` variable is defined in enhanced_backend.py ✅

4. **Health check fails**
   - Ensure `/health` endpoint is accessible
   - Check if MongoDB connection is working

### Performance Optimization

For production deployment, consider:

1. **Instance Type**: Upgrade from Starter to Professional
2. **Database**: Use MongoDB Atlas M10+ cluster
3. **Caching**: Enable Redis for session storage
4. **CDN**: Use Render's static site for frontend assets

### Monitoring

Monitor your deployment:
- **Render Dashboard**: Check logs and metrics
- **Health Endpoint**: `GET /health` for service status  
- **MongoDB Atlas**: Monitor database performance
- **Pinecone**: Track vector database usage

## Production Checklist

- [ ] MongoDB Atlas cluster configured with proper security
- [ ] Environment variables set in Render dashboard
- [ ] Health check endpoint responding
- [ ] API endpoints tested and working
- [ ] Database connections verified
- [ ] Security headers configured
- [ ] CORS settings updated for production domain
- [ ] Monitoring and alerts set up

## Next Steps

After successful deployment:
1. Configure custom domain in Render
2. Set up SSL certificate (automatic with custom domain)
3. Configure MongoDB backups
4. Set up application monitoring
5. Deploy frontend applications

## Support

If you encounter issues:
1. Check Render deployment logs
2. Verify environment variables
3. Test MongoDB connection separately
4. Check Pinecone API status
5. Review GitHub repository structure

**Deployment URL**: https://your-app-name.onrender.com  
**Health Check**: https://your-app-name.onrender.com/health  
**API Docs**: https://your-app-name.onrender.com/docs
