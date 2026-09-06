"""
API middleware for request validation, security, and logging.
Implements request/response interceptors for standardized handling.
"""
import time
import uuid
import logging
from functools import wraps
from typing import Callable, Optional
from flask import Flask, request, jsonify, g
from pydantic import ValidationError

from backend.exceptions import (
    AgentException, ValidationError as AgentValidationError, 
    AuthenticationError, create_error_response
)
from backend.logging_config import CorrelationIDFilter

logger = logging.getLogger(__name__)


class RequestValidator:
    """Validate and sanitize incoming requests."""
    
    @staticmethod
    def validate_json_body(schema_class):
        """
        Decorator to validate request JSON body against schema.
        
        Args:
            schema_class: Pydantic model to validate against
        """
        def decorator(f: Callable):
            @wraps(f)
            def wrapper(*args, **kwargs):
                # Skip validation for GET requests
                if request.method == 'GET':
                    return f(*args, **kwargs)
                
                # Ensure content-type is JSON
                if not request.is_json:
                    error = AgentValidationError(
                        "Content-Type must be application/json",
                        field="Content-Type"
                    )
                    error.log(logger)
                    return jsonify(error.to_dict()), 400
                
                try:
                    # Parse and validate request body
                    data = request.get_json()
                    validated = schema_class(**data)
                    
                    # Store validated data in request context
                    g.validated_data = validated
                    
                    return f(*args, **kwargs)
                
                except ValidationError as e:
                    # Convert Pydantic errors to agent errors
                    errors = e.errors()
                    first_error = errors[0] if errors else {}
                    field = str(first_error.get("loc", ["unknown"])[0])
                    message = first_error.get("msg", "Validation failed")
                    
                    error = AgentValidationError(
                        message=message,
                        field=field,
                        context={"validation_errors": errors}
                    )
                    error.log(logger)
                    return jsonify(error.to_dict()), 400
                
                except Exception as e:
                    error = AgentValidationError(
                        message=f"Request parsing failed: {str(e)}",
                        original_error=e
                    )
                    error.log(logger)
                    return jsonify(error.to_dict()), 400
            
            return wrapper
        return decorator
    
    @staticmethod
    def validate_request_size(max_size_mb: int = 10):
        """
        Decorator to enforce request size limits.
        
        Args:
            max_size_mb: Maximum request size in megabytes
        """
        def decorator(f: Callable):
            @wraps(f)
            def wrapper(*args, **kwargs):
                content_length = request.content_length
                max_bytes = max_size_mb * 1024 * 1024
                
                if content_length and content_length > max_bytes:
                    error = AgentValidationError(
                        message=f"Request too large. Maximum size: {max_size_mb}MB",
                        context={"max_size_mb": max_size_mb, "content_length": content_length}
                    )
                    error.log(logger)
                    return jsonify(error.to_dict()), 413
                
                return f(*args, **kwargs)
            
            return wrapper
        return decorator


class RequestContext:
    """Manage request context including correlation IDs and timing."""
    
    @staticmethod
    def setup_request_context():
        """Initialize request context before processing."""
        # Generate or get correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = f"req-{uuid.uuid4()}"
        
        CorrelationIDFilter.set_correlation_id(correlation_id)
        g.correlation_id = correlation_id
        g.request_start_time = time.time()
        
        logger.info(
            "Request received",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.path,
                    "remote_addr": request.remote_addr
                }
            }
        )
    
    @staticmethod
    def finalize_request_context(response):
        """Finalize request context after processing."""
        if hasattr(g, "request_start_time"):
            duration_ms = (time.time() - g.request_start_time) * 1000
            
            logger.info(
                "Request completed",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.path,
                        "status": response.status_code,
                        "duration_ms": duration_ms
                    }
                }
            )
        
        # Add correlation ID to response headers
        if hasattr(g, "correlation_id"):
            response.headers["X-Correlation-ID"] = g.correlation_id
        
        return response


class ErrorHandler:
    """Standardized error handling for all exceptions."""
    
    @staticmethod
    def register_handlers(app: Flask):
        """Register error handlers with Flask app."""
        
        @app.errorhandler(AgentException)
        def handle_agent_exception(error: AgentException):
            """Handle agent exceptions."""
            error.log(logger)
            response = jsonify(error.to_dict())
            response.status_code = error.status_code
            return response
        
        @app.errorhandler(ValidationError)
        def handle_validation_error(error: ValidationError):
            """Handle Pydantic validation errors."""
            agent_error = AgentValidationError(
                message=str(error),
                context={"validation_error": str(error)}
            )
            agent_error.log(logger)
            return jsonify(agent_error.to_dict()), 400
        
        @app.errorhandler(404)
        def handle_not_found(error):
            """Handle 404 errors."""
            response = {
                "error": "NOT_FOUND",
                "message": "The requested resource was not found",
                "request_id": g.get("correlation_id")
            }
            return jsonify(response), 404
        
        @app.errorhandler(405)
        def handle_method_not_allowed(error):
            """Handle 405 errors."""
            response = {
                "error": "METHOD_NOT_ALLOWED",
                "message": f"Method {request.method} is not allowed for {request.path}",
                "request_id": g.get("correlation_id")
            }
            return jsonify(response), 405
        
        @app.errorhandler(500)
        def handle_internal_error(error):
            """Handle unhandled exceptions."""
            logger.error(
                "Internal server error",
                exc_info=error,
                extra={
                    "extra_fields": {
                        "error_type": type(error).__name__
                    }
                }
            )
            response = {
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "request_id": g.get("correlation_id")
            }
            return jsonify(response), 500
        
        @app.errorhandler(503)
        def handle_service_unavailable(error):
            """Handle service unavailable errors."""
            response = {
                "error": "SERVICE_UNAVAILABLE",
                "message": "The service is temporarily unavailable",
                "request_id": g.get("correlation_id")
            }
            return jsonify(response), 503

        @app.errorhandler(413)
        def handle_request_too_large(error):
            response = {
                "error": "REQUEST_TOO_LARGE",
                "message": "The request body is too large",
                "request_id": g.get("correlation_id")
            }
            return jsonify(response), 413


def setup_middleware(app: Flask) -> None:
    """
    Setup all API middleware.
    
    Args:
        app: Flask application instance
    """
    # Register error handlers
    ErrorHandler.register_handlers(app)
    
    # Setup request/response context
    @app.before_request
    def before_request():
        RequestContext.setup_request_context()
    
    @app.after_request
    def after_request(response):
        return RequestContext.finalize_request_context(response)
