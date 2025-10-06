# Security Improvements

## Overview
This app has been updated with basic security measures to make it safer for web deployment while maintaining the "bring your own API key" model.

## Implemented Security Features

### 1. HTTPS Warning ⚠️
- Displays a prominent warning when the site is accessed over HTTP (non-localhost)
- Warns users that their API key may be visible to attackers on insecure connections
- **Action Required**: Deploy with HTTPS enabled (e.g., via Heroku, Vercel, or with Let's Encrypt)

### 2. Session-Only Storage Option 🔒
- Users can choose to store their API key only for the current browser session
- Key is automatically deleted when the browser is closed
- Reduces risk of long-term key exposure
- Default: Keys persist in localStorage (can be changed by user)

### 3. Rate Limiting 🚦
- Limits: **20 requests per 5 minutes** per API key
- Prevents abuse and runaway API costs
- Uses SHA-256 hash of API keys (server never stores actual keys)
- Returns clear error messages with wait times when limit is exceeded

### 4. Clear Security Warnings 📢
- Modal dialog with comprehensive security notice
- Explains that:
  - Keys are stored in browser only
  - Keys should never be shared
  - Users should monitor OpenAI usage
  - Requests go through the server (transparency)

## Current Security Level

**✅ Good for:**
- Hackathons and demos
- Personal projects
- Small trusted user groups
- Educational purposes

**❌ Not recommended for:**
- Large-scale public deployment
- Commercial applications
- High-value use cases
- Untrusted user environments

## Remaining Risks

1. **Server can still see API keys** - Keys are sent through your Flask server
2. **XSS vulnerabilities** - If your site has XSS, keys can be stolen from localStorage
3. **No user authentication** - Anyone can use the app
4. **In-memory rate limiting** - Resets when server restarts
5. **No audit logging** - Can't track misuse

## Recommendations for Production

If you want to deploy this for real users:

### Option 1: Add proper authentication
```
- User login system (email/password or OAuth)
- Store YOUR API key server-side
- Track usage per user
- Implement persistent rate limiting (Redis/database)
```

### Option 2: Use OpenAI's client-side SDK
```
- Remove the backend proxy entirely
- Frontend calls OpenAI directly
- Your server never sees keys
- Requires CORS configuration
```

### Option 3: Monetize it
```
- Remove API key input
- Use your own OpenAI key
- Charge users for access
- Implement proper billing
```

## Configuration

Rate limiting can be adjusted in `app.py`:

```python
RATE_LIMIT_REQUESTS = 20  # Max requests per window
RATE_LIMIT_WINDOW = 300   # Window in seconds (5 minutes)
```

## Testing

Test the security features:

1. **HTTPS Warning**: Access via `http://` (not localhost) - should see warning
2. **Session Storage**: Check "Session only" - key disappears after closing browser
3. **Rate Limiting**: Make 21+ requests in 5 minutes - should get rate limit error

## Deployment Checklist

- [ ] Deploy with HTTPS enabled
- [ ] Test HTTPS warning on HTTP fallback
- [ ] Verify rate limiting works
- [ ] Set appropriate rate limits for your use case
- [ ] Monitor server logs for errors
- [ ] Consider adding Content Security Policy (CSP) headers
- [ ] Add error tracking (e.g., Sentry)

## Support

For more secure implementations, consider:
- Flask-Limiter for better rate limiting
- Flask-Login for user authentication
- Redis for distributed rate limiting
- API gateway services (AWS API Gateway, Kong, etc.)
