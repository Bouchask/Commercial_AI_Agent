"""
Pydantic request/response models for API validation.
Ensures all inputs are validated against defined schemas.
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any, List
from enum import Enum


class LoginRequest(BaseModel):
    """User login request model."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, max_length=256, description="User password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "password123"
            }
        }


class ProcessRequest(BaseModel):
    """Process request model for workflow submission."""
    user_input: str = Field(
        ...,
        min_length=5,
        max_length=5000,
        description="User request or instruction"
    )
    auto_approve: bool = Field(
        default=False,
        description="Automatically approve all steps (dangerous, use with caution)"
    )
    
    @validator("user_input")
    def validate_user_input(cls, v):
        """Ensure user input is not just whitespace."""
        if not v.strip():
            raise ValueError("User input cannot be empty or whitespace only")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_input": "I need a quote for John Doe for an e-commerce website",
                "auto_approve": False
            }
        }


class ChatRequest(BaseModel):
    """Authenticated conversational request accepted by the dashboard."""
    prompt: str = Field(..., min_length=1, max_length=5000)
    thread_id: Optional[str] = Field(None, min_length=1, max_length=128)

    @validator("prompt")
    def validate_prompt(cls, value):
        if not value.strip():
            raise ValueError("Prompt cannot be empty or whitespace only")
        return value.strip()


class ApproveRequest(BaseModel):
    """Step approval request model."""
    execution_id: str = Field(
        ...,
        min_length=10,
        description="Execution ID from process request"
    )
    step_id: int = Field(
        ...,
        ge=1,
        description="Step ID to approve"
    )
    approved: bool = Field(
        ...,
        description="Approval decision (true to approve, false to reject)"
    )
    rejection_reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for rejection (if approved=false)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": "exec-550e8400-e29b-41d4-a716-446655440000",
                "step_id": 1,
                "approved": True
            }
        }


class ExecutionStatusRequest(BaseModel):
    """Get execution status request model."""
    execution_id: str = Field(
        ...,
        min_length=10,
        description="Execution ID to check"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": "exec-550e8400-e29b-41d4-a716-446655440000"
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    context: Optional[Dict[str, Any]] = Field(None, description="Error context")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "INVALID_INPUT",
                "message": "Email is required",
                "context": {"field": "email"},
                "request_id": "req-550e8400-e29b-41d4-a716-446655440000"
            }
        }


class ProcessResponse(BaseModel):
    """Process request response model."""
    execution_id: str = Field(..., description="Execution ID")
    status: str = Field(
        ...,
        description="Execution status (executing, waiting_approval, completed, failed)"
    )
    message: Optional[str] = Field(None, description="Status message")
    step: Optional[int] = Field(None, description="Current step ID if waiting approval")
    tool: Optional[str] = Field(None, description="Tool name if waiting approval")
    arguments: Optional[Dict[str, Any]] = Field(None, description="Tool arguments if waiting approval")
    results: Optional[Dict[str, Any]] = Field(None, description="Results if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": "exec-550e8400-e29b-41d4-a716-446655440000",
                "status": "waiting_approval",
                "message": "Approval required for step 1",
                "step": 1,
                "tool": "db.find_or_create_client",
                "arguments": {"name": "John Doe"}
            }
        }


class ApproveResponse(BaseModel):
    """Approval response model."""
    status: str = Field(..., description="Updated execution status")
    message: str = Field(..., description="Status message")
    execution_id: str = Field(..., description="Execution ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "executing",
                "message": "Step approved, continuing execution",
                "execution_id": "exec-550e8400-e29b-41d4-a716-446655440000"
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status (ok, degraded, down)")
    service: str = Field(..., description="Service name")
    timestamp: str = Field(..., description="Check timestamp")
    database: str = Field(..., description="Database status")
    llm: str = Field(..., description="LLM provider status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "service": "commercial-ai-agent",
                "timestamp": "2024-08-12T12:20:36Z",
                "database": "connected",
                "llm": "ready"
            }
        }


class LoginResponse(BaseModel):
    """Login response model."""
    token: str = Field(..., description="JWT authentication token")
    user_id: int = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "user_id": 1,
                "email": "user@example.com"
            }
        }


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of items per page"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip"
    )


class SearchParams(BaseModel):
    """Search parameters for query endpoints."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum results"
    )


# Dashboard-related payloads
class ClientCreate(BaseModel):
    name: str = Field(..., description="Client name")
    email: Optional[EmailStr] = Field(None, description="Client email")
    phone: Optional[str] = Field(None, description="Client phone")
    address: Optional[str] = Field(None, description="Client address")


class ServiceCreate(BaseModel):
    code: str = Field(..., description="Unique service code")
    name: str = Field(..., description="Service name")
    description: Optional[str] = Field(None)
    unit_price: float = Field(..., ge=0)
    currency: Optional[str] = Field('MAD')
    tax_rate: Optional[float] = Field(20.0)


class QuoteItemCreate(BaseModel):
    service_id: int
    quantity: Optional[float] = Field(1.0, ge=0)
    unit_price: float = Field(..., ge=0)
    tax_rate: Optional[float] = Field(20.0)


class QuoteCreate(BaseModel):
    quote_number: str
    client_id: int
    items: List[QuoteItemCreate]
    status: Optional[str] = Field('DRAFT')
    valid_until: Optional[str] = None


class QuoteResponse(BaseModel):
    id: int
    quote_number: str
    client_id: int
    status: str
    subtotal: float
    tax_total: float
    total_amount: float
    created_at: Optional[str]


class InvoiceItemCreate(BaseModel):
    service_id: int
    quantity: Optional[float] = Field(1.0, ge=0)
    unit_price: float = Field(..., ge=0)
    tax_rate: Optional[float] = Field(20.0)


class InvoiceCreate(BaseModel):
    invoice_number: str
    client_id: int
    items: List[InvoiceItemCreate]
    status: Optional[str] = Field('DRAFT')
    due_date: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    client_id: int
    status: str
    subtotal: float
    tax_total: float
    total_amount: float
    created_at: Optional[str]
