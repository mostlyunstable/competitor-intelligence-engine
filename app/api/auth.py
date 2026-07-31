import hmac
import logging
import secrets

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBasic, HTTPBasicCredentials

from app.configuration.settings import get_settings

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
security = HTTPBasic(auto_error=False)

async def verify_any_auth(
    api_key: str | None = Security(api_key_header),
    credentials: HTTPBasicCredentials | None = Depends(security)
) -> str:
    settings = get_settings()
    expected_key = settings.api_key

    # 1. Try API Key
    if expected_key and api_key and hmac.compare_digest(api_key, expected_key):
        return "api-key"

    # 2. Try Basic Auth (for dashboard browser clients)
    admin_user = settings.admin_user
    admin_password = settings.admin_password
    if credentials and admin_user and admin_password:
        correct_username = secrets.compare_digest(
            credentials.username, admin_user
        )
        correct_password = secrets.compare_digest(
            credentials.password, admin_password
        )
        if correct_username and correct_password:
            return "basic-auth"

    # 3. Fallback for Dev Environment
    if not expected_key:
        if settings.environment != "development":
            logger.critical("API key is not configured in non-development environment!")
            raise HTTPException(
                status_code=500,
                detail="Security configuration error: API key is required in production.",
            )
        logger.warning(
            "No API key configured. All requests are unauthenticated. "
            "Set CI_API_KEY in your .env file to secure the API."
        )
        return "no-auth"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid API Key or Basic Auth required",
        headers={"WWW-Authenticate": "Basic"},
    )

async def verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> str:
    settings = get_settings()
    expected_key = settings.api_key
    if not expected_key:
        if settings.environment != "development":
            raise HTTPException(status_code=500, detail="Security error")
        return "no-auth"
    if api_key is None:
        raise HTTPException(status_code=401, detail="Missing API key")
    if not hmac.compare_digest(api_key, expected_key):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
