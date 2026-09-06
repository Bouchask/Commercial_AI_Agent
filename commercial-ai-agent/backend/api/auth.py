import jwt
import logging
from functools import wraps
from flask import request, jsonify
from backend.config.settings import settings
from backend.database.connection import SessionLocal
from backend.models.user import User

logger = logging.getLogger(__name__)

def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
        if not token:
            logger.info("Authentication rejected: token is missing")
            return jsonify({"error": "Authentication token is missing"}), 401

        db = None
        try:
            data = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
            db = SessionLocal()
            current_user = db.query(User).filter(User.id == int(data["sub"])).first()
            
            if not current_user or not current_user.is_active:
                logger.info("Authentication rejected: inactive or missing user")
                return jsonify({"error": "User no longer exists or is inactive"}), 401
                
        except jwt.ExpiredSignatureError:
            logger.info("Authentication rejected: token expired")
            return jsonify({"error": "Authentication token has expired"}), 401
        except (jwt.InvalidTokenError, KeyError, ValueError):
            logger.info("Authentication rejected: invalid token")
            return jsonify({"error": "Invalid authentication token"}), 401
        finally:
            if db is not None:
                db.close()
            
        # Attach user to request
        request.current_user = current_user
        
        return f(*args, **kwargs)
        
    return decorated


def roles_required(*roles):
    """Decorator to require the current user have one of the specified roles."""
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = getattr(request, 'current_user', None)
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            user_role = (user.role or '').upper()
            allowed = [r.upper() for r in roles]
            if user_role not in allowed:
                return jsonify({"error": "Permission denied"}), 403
            return f(*args, **kwargs)
        return decorated
    return wrapper
