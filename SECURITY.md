# 🔐 BUDDY 2.0 Security Configuration Guide

## JWT Secret Management

### Development Environment
- **File**: `.env`
- **Secret**: Secure 64-byte token generated locally
- **Usage**: Local development and testing

### Production Environment
- **File**: `.env.production` (for reference only - DO NOT commit to git)
- **Secret**: Different secure 64-byte token for production
- **Usage**: Set in Render environment variables

## Generating Secure JWT Secrets

### Method 1: Python (Recommended)
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Method 2: OpenSSL
```bash
openssl rand -base64 64
```

### Method 3: Node.js
```bash
node -e "console.log(require('crypto').randomBytes(64).toString('base64url'))"
```

## Security Best Practices

### ✅ DO:
- Use different JWT secrets for development and production
- Generate cryptographically secure random tokens (64+ bytes)
- Store production secrets in environment variables only
- Rotate JWT secrets periodically (every 90 days recommended)
- Use HTTPS in production
- Enable CORS restrictions for production domains

### ❌ DON'T:
- Commit production secrets to version control
- Use simple passwords or predictable patterns
- Share JWT secrets between environments
- Use the same secret across multiple applications
- Store secrets in configuration files in production

## Environment Variable Security

### Development (.env file)
```bash
# Local development - committed to git
BUDDY_JWT_SECRET=QVyyMZGy9Pf1R_Y3lOJjRFjZMFCGfoC_ygVgS2nY0-HZ9l0bGqiTaToylOIc0vL48JbC-wWKqfbXVdmcdBDo1w
```

### Production (Render Environment Variables)
```bash
# Production - set in Render dashboard, NOT committed to git
BUDDY_JWT_SECRET=OOF4DZRRk6ZX1P2xxTJTlQlfBU5Lqsg79ZI0K8sIAaEQY1jqX1nOi80FdtmcOdQZwRs1pn19XwdNQIWsz6wA
```

## Render Deployment Security Checklist

- [ ] Set unique JWT secret in Render environment variables
- [ ] Use production MongoDB database (not development)
- [ ] Configure CORS for your production domain only
- [ ] Enable HTTPS (automatic with Render)
- [ ] Set `BUDDY_ENV=production` and `BUDDY_DEBUG=0`
- [ ] Use strong, unique API keys for all services
- [ ] Enable MongoDB Atlas IP whitelisting for production
- [ ] Set up monitoring and alerting
- [ ] Configure rate limiting for API endpoints
- [ ] Regular security audits and dependency updates

## JWT Token Configuration

### Token Expiry Settings
```bash
ACCESS_TOKEN_EXPIRY=15m     # Short-lived access tokens
REFRESH_TOKEN_EXPIRY=7d     # Longer-lived refresh tokens
```

### Security Headers (Automatic in FastAPI)
- `Content-Security-Policy`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Strict-Transport-Security` (HTTPS only)

## Monitoring and Alerting

### Security Events to Monitor
- Failed authentication attempts
- Invalid JWT tokens
- Unusual API usage patterns
- Database connection failures
- Rate limit violations

### Logging Configuration
```python
# Security-focused logging
logging.config = {
    "security": {
        "level": "INFO",
        "handlers": ["file", "console"],
        "capture_failed_auth": True,
        "capture_api_errors": True
    }
}
```

## Incident Response

### If JWT Secret is Compromised
1. **Immediate**: Generate new JWT secret
2. **Deploy**: Update production environment with new secret
3. **Invalidate**: All existing tokens become invalid
4. **Notify**: Users will need to re-authenticate
5. **Audit**: Review access logs for suspicious activity

### Security Contact
- **Security Issues**: security@buddy.ai
- **Emergency**: Use GitHub Security Advisories
- **Documentation**: This security guide

---

**🔒 Security is a continuous process. Regular reviews and updates are essential for maintaining a secure BUDDY 2.0 deployment.**
