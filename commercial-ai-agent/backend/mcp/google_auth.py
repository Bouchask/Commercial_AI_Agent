import contextvars
import logging
from typing import Optional
from flask import has_request_context, request
from google.oauth2.credentials import Credentials
from backend.config.settings import settings
from backend.database.connection import SessionLocal
from backend.models.user import User

logger = logging.getLogger(__name__)

# Thread-safe and async-safe context variables to carry user context into worker threads / MCP calls
active_user_context: contextvars.ContextVar[Optional[User]] = contextvars.ContextVar("active_user_context", default=None)
active_execution_id_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("active_execution_id_context", default=None)


def set_active_user(user: Optional[User]) -> None:
    """Set the active User in the current execution context."""
    active_user_context.set(user)


def set_active_execution_id(execution_id: Optional[str]) -> None:
    """Set the active execution ID in the current execution context."""
    active_execution_id_context.set(execution_id)


def get_current_user(execution_id: Optional[str] = None) -> Optional[User]:
    """
    Safely retrieve the current User across all runtime environments:
    1. Active Flask request context (when inside an HTTP request)
    2. ContextVar (when running in background workers / subthreads)
    3. Database lookup by execution_id (via executions table)
    4. Database fallback to active user (for background tasks or single-user instances)
    
    Guaranteed NEVER to raise 'Working outside of request context'.
    """
    # 1. Check Flask request context safely
    try:
        if has_request_context():
            user = getattr(request, 'current_user', None)
            if user:
                return user
    except Exception:
        pass

    # 2. Check ContextVar
    try:
        ctx_user = active_user_context.get()
        if ctx_user:
            return ctx_user
    except Exception:
        pass

    # 3. Look up by execution_id from database
    target_exec_id = execution_id or active_execution_id_context.get()
    if target_exec_id:
        try:
            from backend.models.execution import Execution
            db = SessionLocal()
            try:
                ex = db.get(Execution, str(target_exec_id))
                if ex and ex.user_id:
                    user = db.get(User, ex.user_id)
                    if user:
                        return user
            finally:
                db.close()
        except Exception as e:
            logger.debug(f"Unable to resolve user by execution_id '{target_exec_id}': {e}")

    # 4. Fallback to active user with google credentials in database
    try:
        db = SessionLocal()
        try:
            user_with_token = db.query(User).filter(
                User.is_active == True,
                User.google_access_token.isnot(None)
            ).order_by(User.id.asc()).first()
            if user_with_token:
                return user_with_token

            # Otherwise any active user
            user = db.query(User).filter(User.is_active == True).order_by(User.id.asc()).first()
            if user:
                return user
        finally:
            db.close()
    except Exception as e:
        logger.debug(f"Unable to resolve fallback user from DB: {e}")

    return None


def get_user_google_credentials(execution_id: Optional[str] = None) -> Optional[Credentials]:
    """
    Retrieve Google OAuth2 Credentials for the currently authenticated user.
    Safely resolves the user inside or outside of a Flask request context.
    """
    user = get_current_user(execution_id)
    if not user:
        logger.warning("get_user_google_credentials: No user could be resolved.")
        return None
        
    if not user.google_access_token:
        logger.warning(f"User {user.email} does not have a google_access_token.")
        return None
        
    return Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET
    )
