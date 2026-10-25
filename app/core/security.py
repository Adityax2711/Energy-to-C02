"""
Security & Hardening Module for Energy-to-CO2 Translation Engine
Implements:
1. OWASP Security Headers Middleware (X-Frame-Options, CSP, nosniff)
2. Sliding-Window In-Memory Rate Limiting (DDoS & Abuse Protection)
3. API Key Authentication Guard (Optional / Enforceable via config)
4. AI Prompt Injection & Payload Sanitization
"""
import time
from typing import Dict, List, Optional
from collections import defaultdict
from fastapi import Request, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings

# API Key Security Header Scheme
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies defense-in-depth OWASP recommended security headers to all HTTP responses.
    Protects against MIME sniffing, clickjacking, cross-site scripting (XSS), and data leakage.
    """
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "accelerometer=(), camera=(), geolocation=(), microphone=(), payment=()"
        
        # CSP: Allow self and verified CDNs for Chart.js and Google Fonts
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        return response


class SlidingWindowRateLimiter:
    """
    Thread-safe sliding-window rate limiter for protecting endpoints from DoS and abuse.
    Tracks client request timestamps within a 60-second sliding window.
    """
    def __init__(self, max_requests_per_minute: int = 150):
        self.max_requests = max_requests_per_minute
        self.window_seconds = 60.0
        self.requests_log: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Filter timestamps outside the sliding window
        window = [ts for ts in self.requests_log[client_ip] if ts > cutoff]
        self.requests_log[client_ip] = window

        if len(window) >= self.max_requests:
            return False

        self.requests_log[client_ip].append(now)
        return True


rate_limiter = SlidingWindowRateLimiter(max_requests_per_minute=180)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware applying rate limits to API endpoints while exempting static assets.
    """
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Static files and health checks bypass rate limiting
        if path.startswith("/static") or path == "/health" or path == "/":
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"

        if settings.RATE_LIMIT_ENABLED and not rate_limiter.is_allowed(client_ip):
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please throttle requests (maximum 180 requests/minute)."},
                headers={"Retry-After": "10"}
            )

        return await call_next(request)


def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)):
    """
    Validates API key when security enforcement is active.
    When settings.SECURITY_ENABLED is False (default for demo/tests), all calls pass.
    """
    if not settings.SECURITY_ENABLED:
        return True

    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    return True


def sanitize_input_text(text: str) -> str:
    """
    Sanitizes user input to prevent prompt injection and control character attacks.
    """
    if not text:
        return ""
    
    # Strip null bytes and non-printable characters
    cleaned = "".join(ch for ch in text if ch.isprintable() or ch in ("\n", "\r", "\t"))
    
    import re
    # Check for known destructive prompt injection signatures
    suspicious_patterns = [
        r"ignore previous instructions",
        r"disregard all previous",
        r"drop\s+table",
        r"delete\s+from",
        r"system\s*prompt\s*:"
    ]
    for pattern in suspicious_patterns:
        cleaned = re.sub(pattern, "[FILTERED]", cleaned, flags=re.IGNORECASE)
            
    return cleaned.strip()
