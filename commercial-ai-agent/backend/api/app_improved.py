"""
Enhanced Flask API application with security, validation, and error handling.
"""
import logging
import uuid
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import jwt
import datetime
from werkzeug.security import check_password_hash
from sqlalchemy import text

from backend.agents.langgraph_orchestrator import LangGraphOrchestrator
from backend.config.settings import cors_origins, settings
from backend.api.auth import jwt_required
from backend.api.middleware import setup_middleware, RequestValidator
from backend.database.connection import SessionLocal
from backend.models.user import User
from backend.api_schemas import (
    LoginRequest, ProcessRequest, ApproveRequest,
    ExecutionStatusRequest, ProcessResponse, ApproveResponse,
    HealthCheckResponse, LoginResponse, ErrorResponse
)
from backend.exceptions import (
    AuthenticationError, ValidationError as AgentValidationError,
    AgentException, create_error_response
)
from backend.logging_config import setup_logging, get_logger

# Initialize logger
logger = get_logger(__name__)


def create_app(log_file: str = None):
    """
    Create and configure Flask application.
    
    Args:
        log_file: Optional log file path
    
    Returns:
        Configured Flask app
    """
    # Setup logging first
    setup_logging(app_env=settings.APP_ENV, log_file=log_file)
    
    app = Flask(__name__)
    
    # Configure CORS
    CORS(app, resources={r"/api/*": {"origins": cors_origins()}})
    
    # Setup rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["100 per hour"],
        storage_uri="memory://"
    )
    
    # Setup middleware (validation, error handling, logging)
    setup_middleware(app)
    
    # Register MCP tools
    from backend.mcp.database.server import register_database_tools
    from backend.mcp.spreadsheet.server import register_spreadsheet_tools
    from backend.mcp.document.server import register_document_tools
    from backend.mcp.email.server import register_email_tools
    from backend.mcp.utils.server import register_utils_tools
    
    try:
        logger.info("Registering MCP tools...")
        register_database_tools()
        register_spreadsheet_tools()
        register_document_tools()
        register_email_tools()
        register_utils_tools()
        logger.info("MCP tools registered successfully")
    except Exception as e:
        logger.error(f"Failed to register MCP tools: {str(e)}", exc_info=e)
        raise
    
    # Initialize orchestrator
    try:
        logger.info("Initializing LangGraph orchestrator...")
        app.orchestrator = LangGraphOrchestrator()
        logger.info("Orchestrator initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {str(e)}", exc_info=e)
        raise

    # ===== ROUTES =====
    
    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint."""
        try:
            # Check database
            db = SessionLocal()
            try:
                db.execute(text("SELECT 1"))
                db_status = "connected"
            except:
                db_status = "disconnected"
            finally:
                db.close()
            
            response = HealthCheckResponse(
                status="ok" if db_status == "connected" else "degraded",
                service="commercial-ai-agent",
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                database=db_status,
                llm="ready"  # Can add LLM health check
            )
            
            return jsonify(response.dict()), 200
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                "status": "down",
                "service": "commercial-ai-agent",
                "error": str(e)
            }), 503

    @app.route("/api/login", methods=["POST"])
    @limiter.limit("5 per 15 minutes")
    @RequestValidator.validate_request_size(max_size_mb=1)
    @RequestValidator.validate_json_body(LoginRequest)
    def login():
        """
        User login endpoint.
        
        Request:
            {
                "email": "user@example.com",
                "password": "password"
            }
        
        Response:
            {
                "token": "jwt-token",
                "user_id": 1,
                "email": "user@example.com"
            }
        """
        try:
            validated = g.validated_data
            
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.email == validated.email).first()
                
                if not user or not check_password_hash(user.hashed_password, validated.password):
                    logger.warning(f"Failed login attempt for email: {validated.email}")
                    raise AuthenticationError("Invalid email or password")
                
                # Generate JWT token
                token = jwt.encode({
                    "sub": str(user.id),
                    "email": user.email,
                    "role": user.role,
                    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
                }, settings.JWT_SECRET, algorithm="HS256")
                
                response = LoginResponse(
                    token=token,
                    user_id=user.id,
                    email=user.email
                )
                
                logger.info(f"User logged in: {user.email}")
                return jsonify(response.dict()), 200
            
            finally:
                db.close()
        
        except AgentException as e:
            e.log(logger)
            return jsonify(e.to_dict()), e.status_code
        except Exception as e:
            logger.error(f"Login failed: {str(e)}", exc_info=e)
            error = AgentValidationError("Login failed", original_error=e)
            return jsonify(error.to_dict()), 500

    @app.route("/api/process", methods=["POST"])
    @limiter.limit("20 per hour")
    @jwt_required
    @RequestValidator.validate_request_size(max_size_mb=5)
    @RequestValidator.validate_json_body(ProcessRequest)
    def process():
        """
        Submit a request for processing.
        
        Request:
            {
                "user_input": "I need a quote for...",
                "auto_approve": false
            }
        
        Response:
            {
                "execution_id": "exec-uuid",
                "status": "waiting_approval|executing|completed",
                "message": "...",
                "results": {}
            }
        """
        try:
            validated = g.validated_data
            execution_id = f"exec-{uuid.uuid4()}"
            
            logger.info(f"Processing request: {execution_id}")
            
            # Process the request
            result = app.orchestrator.process_request(
                user_input=validated.user_input,
                auto_approve=validated.auto_approve
            )
            
            # Add execution ID to result
            result["execution_id"] = execution_id
            
            response = ProcessResponse(**result)
            
            return jsonify(response.dict(exclude_none=True)), 202
        
        except AgentException as e:
            e.log(logger)
            return jsonify(e.to_dict()), e.status_code
        except Exception as e:
            logger.error(f"Processing failed: {str(e)}", exc_info=e)
            error = AgentValidationError("Request processing failed", original_error=e)
            return jsonify(error.to_dict()), 500

    @app.route("/api/approve", methods=["POST"])
    @limiter.limit("30 per hour")
    @jwt_required
    @RequestValidator.validate_json_body(ApproveRequest)
    def approve():
        """
        Approve or reject a pending step.
        
        Request:
            {
                "execution_id": "exec-uuid",
                "step_id": 1,
                "approved": true
            }
        
        Response:
            {
                "status": "executing|failed",
                "message": "...",
                "execution_id": "exec-uuid"
            }
        """
        try:
            validated = g.validated_data
            
            logger.info(f"Approval for {validated.execution_id}/step {validated.step_id}: {validated.approved}")
            
            # Process approval
            result = app.orchestrator.process_approval(
                execution_id=validated.execution_id,
                step_id=validated.step_id,
                approved=validated.approved,
                rejection_reason=validated.rejection_reason
            )
            
            response = ApproveResponse(
                status=result.get("status"),
                message=result.get("message"),
                execution_id=validated.execution_id
            )
            
            return jsonify(response.dict()), 200
        
        except AgentException as e:
            e.log(logger)
            return jsonify(e.to_dict()), e.status_code
        except Exception as e:
            logger.error(f"Approval processing failed: {str(e)}", exc_info=e)
            error = AgentValidationError("Approval processing failed", original_error=e)
            return jsonify(error.to_dict()), 500

    @app.route("/api/execution/<execution_id>", methods=["GET"])
    @jwt_required
    def get_execution_status(execution_id: str):
        """
        Get execution status.
        
        Response:
            {
                "execution_id": "exec-uuid",
                "status": "completed",
                "results": {}
            }
        """
        try:
            # Validate execution_id format
            if not execution_id.startswith("exec-"):
                raise AgentValidationError("Invalid execution ID format", field="execution_id")
            
            logger.info(f"Retrieving status for execution: {execution_id}")
            
            # Get execution status
            status = app.orchestrator.get_execution_status(execution_id)
            
            return jsonify(status), 200
        
        except AgentException as e:
            e.log(logger)
            return jsonify(e.to_dict()), e.status_code
        except Exception as e:
            logger.error(f"Status retrieval failed: {str(e)}", exc_info=e)
            error = AgentValidationError("Status retrieval failed", original_error=e)
            return jsonify(error.to_dict()), 500

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(settings.PORT) if hasattr(settings, "PORT") else 5001
    debug = settings.APP_ENV == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
