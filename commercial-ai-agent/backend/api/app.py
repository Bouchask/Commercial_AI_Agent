import logging
import io
from flask import Flask, jsonify, request, g, send_file, abort
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import text
from backend.agents.langgraph_orchestrator import LangGraphOrchestrator
from backend.config.settings import cors_origins, settings
from backend.api.auth import jwt_required
import jwt
import datetime
from werkzeug.security import check_password_hash
from backend.database.connection import SessionLocal
from backend.database.schema_guard import ensure_critical_user_columns, ensure_ownership_columns
from backend.models.user import User
from backend.api.middleware import setup_middleware, RequestValidator
from backend.api_schemas import ChatRequest, LoginRequest, ApproveRequest
from backend.logging_config import setup_logging, get_logger

# Configure basic logging if not already configured
logger = get_logger(__name__)

def create_app():
    setup_logging(app_env=settings.APP_ENV)
    
    # Ensure database tables exist (important for Vercel cold starts)
    try:
        from backend.database.connection import engine
        from backend.models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created successfully.")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        
    ensure_critical_user_columns()
    ensure_ownership_columns()
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
    CORS(app, resources={r"/api/*": {"origins": cors_origins()}})
    setup_middleware(app)
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour"],
        storage_uri="memory://",
    )
    
    # Register tools
    from backend.mcp.database.server import register_database_tools
    from backend.mcp.spreadsheet.server import register_spreadsheet_tools
    from backend.mcp.document.server import register_document_tools
    from backend.mcp.email.server import register_email_tools
    from backend.mcp.utils.server import register_utils_tools
    from backend.mcp.google_calendar.server import register_google_calendar_tools
    from backend.mcp.google_sheets.server import register_google_sheets_tools
    
    for register_tools in (
        register_database_tools, register_spreadsheet_tools, register_document_tools,
        register_email_tools, register_utils_tools, register_google_calendar_tools,
        register_google_sheets_tools,
    ):
        register_tools()

    # Apply auto-migrations on startup for serverless environments
    try:
        from sqlalchemy import text
        with engine.begin() as conn:
            # SQLite doesn't natively support ADD COLUMN IF NOT EXISTS in all versions, 
            # but postgres does. Catching exceptions ensures it doesn't break if it exists.
            try:
                if "sqlite" in str(engine.url):
                    conn.execute(text("ALTER TABLE executions ADD COLUMN title VARCHAR"))
                else:
                    conn.execute(text("ALTER TABLE executions ADD COLUMN IF NOT EXISTS title VARCHAR"))
            except Exception:
                pass
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    execution_id VARCHAR NOT NULL,
                    role VARCHAR NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_messages_execution_id ON messages (execution_id)"))
    except Exception as e:
        logger.error(f"Auto-migration error: {e}")

    # Dashboard API blueprint (clients, services, quotes, invoices)
    from backend.api.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp)

    app.orchestrator = LangGraphOrchestrator()

    @app.route("/api/documents/<path:filename>", methods=["GET"])
    @jwt_required
    def serve_document(filename):
        # Fetch from DB first for stateless environments (Vercel)
        from backend.models.document import Document

        db = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.filename == filename).first()
            user = request.current_user
            if doc:
                from backend.models.client import Client
                client = db.get(Client, doc.client_id)
                if not client or (user.role or "").upper() != "ADMIN" and client.owner_user_id != user.id:
                    abort(404)
            if doc and doc.content:
                mimetype = 'application/pdf' if filename.endswith('.pdf') else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                return send_file(
                    io.BytesIO(doc.content),
                    mimetype=mimetype,
                    as_attachment=False,
                    download_name=filename
                )
        except Exception:
            logger.exception("Failed to fetch document from DB")
        finally:
            db.close()

        # Filesystem artifacts without a database record have no ownership
        # proof and must never be served.
        abort(404)

    @app.route("/health", methods=["GET"])
    def health_check():
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return jsonify({"status": "ok", "service": "commercial-ai-agent", "database": "connected"})
        except Exception:
            logging.exception("Health check database failure")
            return jsonify({"status": "degraded", "service": "commercial-ai-agent", "database": "unavailable"}), 503
        finally:
            db.close()

    @app.route("/api/user/spreadsheet", methods=["GET"])
    @jwt_required
    def get_user_spreadsheet():
        user = getattr(request, 'current_user', None)
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
            
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.id == user.id).first()
            if db_user and db_user.default_spreadsheet_id:
                return jsonify({"spreadsheet_id": db_user.default_spreadsheet_id})
            return jsonify({"spreadsheet_id": None})
        finally:
            db.close()

    @app.route("/api/user/spreadsheet/data", methods=["GET"])
    @jwt_required
    def get_user_spreadsheet_data():
        user = getattr(request, 'current_user', None)
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
            
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.id == user.id).first()
            if not db_user or not db_user.default_spreadsheet_id:
                return jsonify({"error": "No spreadsheet associated with this user"}), 404
            
            from backend.mcp.google_sheets.tools import get_all_sheets_data
            data = get_all_sheets_data(db_user.default_spreadsheet_id)
            return jsonify({"data": data})
        except Exception:
            logger.exception("Failed to retrieve spreadsheet data")
            return jsonify({"error": "Unable to retrieve spreadsheet data"}), 502
        finally:
            db.close()

    @app.route("/api/auth/google", methods=["POST"])
    @limiter.limit("10 per hour")
    def google_auth():
        data = request.get_json(silent=True) or {}
        code = data.get("code")
        if not code:
            return jsonify({"error": "Missing authorization code"}), 400
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            logger.error("Google OAuth attempted without configured credentials")
            return jsonify({"error": "Google sign-in is not configured"}), 503
            
        import requests
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": "postmessage",
            "grant_type": "authorization_code"
        }
        
        try:
            resp = requests.post(token_url, data=payload, timeout=15)
        except requests.RequestException:
            logger.exception("Google token exchange request failed")
            return jsonify({"error": "Google sign-in is temporarily unavailable"}), 503
        if not resp.ok:
            logging.warning("Google token exchange failed with status %s", resp.status_code)
            return jsonify({"error": "Failed to exchange token"}), 400
            
        token_data = resp.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        id_token_jwt = token_data.get("id_token")
        granted_scopes = token_data.get("scope", "")

        if not id_token_jwt:
            logger.warning("Google token exchange did not return an OpenID token")
            return jsonify({"error": "Google sign-in did not return an identity token. Please try again."}), 400
        
        # Verify that the user checked the boxes for Calendar and Sheets
        if "calendar" not in granted_scopes.lower() or "spreadsheets" not in granted_scopes.lower():
            return jsonify({
                "error": "Autorisations manquantes. Vous DEVEZ cocher les cases pour Google Agenda et Google Sheets lors de la connexion."
            }), 403
        
        
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
        try:
            id_info = google_id_token.verify_oauth2_token(id_token_jwt, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
        except (ValueError, TypeError):
            logger.warning("Google returned an invalid identity token")
            return jsonify({"error": "Invalid ID token"}), 400
            
        email = id_info.get("email")
        google_id = id_info.get("sub")
        
        from sqlalchemy.exc import SQLAlchemyError

        def persist_google_user(db):
            user = db.query(User).filter((User.email == email) | (User.google_id == google_id)).first()
            if user is None:
                user = User(name=email, password="!", email=email, google_id=google_id, role="SALES", is_active=True)
                db.add(user)
            else:
                user.google_id = google_id
            user.google_access_token = access_token
            if refresh_token:
                user.google_refresh_token = refresh_token
            db.commit()
            db.refresh(user)
            return user

        user = None
        for attempt in range(2):
            db = SessionLocal()
            try:
                user = persist_google_user(db)
                break
            except SQLAlchemyError:
                db.rollback()
                if attempt == 0:
                    # Drop stale sockets and retry a fresh connection once.
                    from backend.database.connection import engine
                    engine.dispose()
                    logger.warning("Database connection failed during Google sign-in; retrying once")
                    continue
                logger.exception("Google user persistence failed after retry")
                return jsonify({"error": "Database temporarily unavailable. Please try again."}), 503
            except Exception:
                db.rollback()
                logger.exception("Google user persistence failed")
                return jsonify({"error": "Unable to complete Google sign-in"}), 503
            finally:
                db.close()

        if user is not None:
            jwt_token = jwt.encode({
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)
            }, settings.JWT_SECRET, algorithm="HS256")
            
            return jsonify({
                "token": jwt_token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role
                }
            })
        return jsonify({"error": "Database temporarily unavailable. Please try again."}), 503

    @app.route("/api/auth/google/config", methods=["GET"])
    @limiter.limit("60 per hour")
    def google_auth_config():
        """Return the public OAuth client ID needed by the browser SDK."""
        if not settings.GOOGLE_CLIENT_ID:
            return jsonify({"error": "Google sign-in is not configured"}), 503
        return jsonify({"client_id": settings.GOOGLE_CLIENT_ID})

    @app.route("/api/login", methods=["POST"])
    @limiter.limit("5 per 15 minutes")
    @RequestValidator.validate_request_size(max_size_mb=1)
    @RequestValidator.validate_json_body(LoginRequest)
    def login():
        db = SessionLocal()
        try:
            data = g.validated_data
            user = db.query(User).filter(User.email == data.email).first()
            if not user or not check_password_hash(user.hashed_password, data.password):
                return jsonify({"error": "Invalid credentials"}), 401
                
            token = jwt.encode({
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, settings.JWT_SECRET, algorithm="HS256")
            
            return jsonify({
                "token": token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role
                }
            })
        finally:
            db.close()

    @app.route("/api/chat", methods=["POST"])
    @jwt_required
    @limiter.limit("30 per hour")
    @RequestValidator.validate_request_size(max_size_mb=1)
    @RequestValidator.validate_json_body(ChatRequest)
    def chat():
        prompt = g.validated_data.prompt
        thread_id = g.validated_data.thread_id
        
        try:
            result = app.orchestrator.process_request(prompt, thread_id=thread_id, user_id=request.current_user.id)
            return jsonify(result)
        except PermissionError:
            return jsonify({"status": "error", "error": "Execution not found"}), 404
        except Exception as e:
            logging.exception("Error during orchestrator execution")
            return jsonify({
                "status": "error",
                "error": "Unable to process the request"
            }), 500

    @app.route("/api/conversations", methods=["GET"])
    @jwt_required
    def get_conversations():
        db = SessionLocal()
        try:
            executions = db.query(Execution).filter(
                Execution.user_id == request.current_user.id
            ).order_by(Execution.updated_at.desc()).all()
            
            return jsonify([{
                "id": ex.id,
                "title": ex.title or "Nouvelle discussion",
                "updated_at": ex.updated_at.isoformat() if ex.updated_at else None
            } for ex in executions])
        finally:
            db.close()

    @app.route("/api/conversations/<thread_id>/history", methods=["GET"])
    @jwt_required
    def get_conversation_history(thread_id):
        db = SessionLocal()
        try:
            execution = db.get(Execution, thread_id)
            if not execution or execution.user_id != request.current_user.id:
                return jsonify({"error": "Not found"}), 404
                
            from backend.models.execution import Message
            messages = db.query(Message).filter(
                Message.execution_id == thread_id
            ).order_by(Message.created_at.asc()).all()
            
            return jsonify([{
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            } for msg in messages])
        finally:
            db.close()

    @app.route("/api/approve", methods=["POST"])
    @jwt_required
    @limiter.limit("30 per hour")
    @RequestValidator.validate_request_size(max_size_mb=1)
    @RequestValidator.validate_json_body(ApproveRequest)
    def approve():
        try:
            data = g.validated_data
            result = app.orchestrator.process_approval(
                data.execution_id,
                data.step_id,
                data.approved,
                user_id=request.current_user.id,
            )
            return jsonify(result)
        except PermissionError:
            return jsonify({"status": "error", "error": "Execution not found"}), 404
        except Exception as e:
            logging.exception("Error during orchestrator approval")
            return jsonify({
                "status": "error",
                "error": "Unable to process approval"
            }), 500

    return app
