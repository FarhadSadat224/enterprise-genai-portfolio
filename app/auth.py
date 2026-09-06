import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models import Principal

bearer = HTTPBearer(auto_error=False)


def authenticate(
    request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)
):
    settings = request.app.state.settings
    if settings.auth_mode == "none":
        return Principal(subject="local-demo", tenant="demo", role="admin")
    if not credentials:
        raise HTTPException(401, "Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.jwt_public_key.replace("\\n", "\n"),
            algorithms=["RS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp", "iat", "sub", "tenant"]},
        )
        if not claims["sub"] or not claims["tenant"]:
            raise ValueError("Empty identity")
        return Principal(
            subject=claims["sub"], tenant=claims["tenant"], role=claims.get("role", "reader")
        )
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, "Invalid bearer token") from None
