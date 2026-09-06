from typing import Dict, Any, Optional
import os
import uuid
from backend.services.latex_service import LatexService
from backend.services.excel_service import ExcelService
from backend.services.document_validation import DocumentValidator
from backend.database.connection import SessionLocal
from backend.models.client import Client
from backend.models.document import Document

def generate_document(
    document_type: str,
    items: list,
    total_ht: float,
    tax: float,
    total_ttc: float,
    client_name: Optional[str] = None,
    original_subtotal: float = 0.0,
    discount_amount: float = 0.0,
    discount_percent_val: float = 0.0,
    tax_rate_val: float = 20.0,
    template_name: str = "b2b",
    additional_context: Optional[Dict[str, Any]] = None,
    client_id: Optional[int] = None,
    reference_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Generate a document (PDF) based on structured content."""
    if document_type not in ["quote", "invoice"]:
        raise ValueError(f"Document type {document_type} is not supported. Only 'quote' and 'invoice' are supported.")
    if template_name != "b2b":
        raise ValueError("Unsupported document template.")
    
    # We will use the LaTeX service to render and compile the document
    # and return the generated filepath or ID
    
    # Resolve client_name and client_id dynamically
    resolved_client_id = int(client_id) if client_id is not None else None
    resolved_client_name = client_name
    
    db = SessionLocal()
    try:
        if resolved_client_id is not None and not resolved_client_name:
            client = db.query(Client).filter(Client.id == resolved_client_id).first()
            if client:
                resolved_client_name = client.name
        elif resolved_client_name and resolved_client_id is None:
            client = db.query(Client).filter(Client.name == resolved_client_name).first()
            if client:
                resolved_client_id = client.id
                
        if not resolved_client_name:
            resolved_client_name = "Client" # Fallback if totally unknown
    finally:
        db.close()

    context = {
        "client_name": resolved_client_name,
        "items": items,
        "subtotal": total_ht,
        "original_subtotal": original_subtotal,
        "discount_amount": discount_amount,
        "discount_percent_val": discount_percent_val,
        "tax_rate_val": int(tax_rate_val) if float(tax_rate_val).is_integer() else tax_rate_val,
        "tax": tax,
        "total": total_ttc,
        "document_number": f"{document_type[:3].upper()}-{str(uuid.uuid4())[:8]}"
    }
    
    if additional_context:
        context.update(additional_context)
        
    latex_service = LatexService()
    
    # 1. Render template
    tex_content = latex_service.render_template(document_type, template_name, context)
    
    # 2. Compile to PDF
    pdf_path = latex_service.compile_pdf(tex_content, document_type)
    
    # 3. Validate
    is_valid, error = DocumentValidator.validate_pdf(pdf_path, context)
    if not is_valid:
        raise RuntimeError(f"Document generation failed validation: {error}")
        
    # Record the generated artifact so the quote remains traceable after the
    # execution process has finished.
    db = SessionLocal()
    try:
        if resolved_client_id is None:
            raise ValueError("A generated document must be linked to an existing client.")
        with open(pdf_path, "rb") as f:
            file_content = f.read()
            
        document = Document(
            filename=os.path.basename(pdf_path),
            filepath=pdf_path,
            content=file_content,
            document_type=document_type,
            reference_id=int(reference_id) if reference_id is not None else None,
            client_id=resolved_client_id,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {
        "success": True,
        "file_path": pdf_path,
        "document_type": document_type,
        "document_number": context["document_number"],
        "document_id": document.id,
    }


def generate_excel_document(
    document_type: str,
    items: list,
    total_ht: float,
    tax: float,
    total_ttc: float,
    client_name: Optional[str] = None,
    original_subtotal: float = 0.0,
    discount_amount: float = 0.0,
    discount_percent_val: float = 0.0,
    tax_rate_val: float = 20.0,
    additional_context: Optional[Dict[str, Any]] = None,
    client_id: Optional[int] = None,
    reference_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Generate a document (Excel) based on structured content."""
    if document_type != "quote":
        raise ValueError("Only quote documents are available in this MVP.")
    
    # Resolve client_name and client_id dynamically
    resolved_client_id = int(client_id) if client_id is not None else None
    resolved_client_name = client_name
    
    db = SessionLocal()
    try:
        if resolved_client_id is not None and not resolved_client_name:
            client = db.query(Client).filter(Client.id == resolved_client_id).first()
            if client:
                resolved_client_name = client.name
        elif resolved_client_name and resolved_client_id is None:
            client = db.query(Client).filter(Client.name == resolved_client_name).first()
            if client:
                resolved_client_id = client.id
                
        if not resolved_client_name:
            resolved_client_name = "Client" # Fallback if totally unknown
    finally:
        db.close()

    context = {
        "client_name": resolved_client_name,
        "items": items,
        "subtotal": total_ht,
        "original_subtotal": original_subtotal,
        "discount_amount": discount_amount,
        "discount_percent_val": discount_percent_val,
        "tax_rate_val": int(tax_rate_val) if float(tax_rate_val).is_integer() else tax_rate_val,
        "tax": tax,
        "total": total_ttc,
        "document_number": f"{document_type[:3].upper()}-{str(uuid.uuid4())[:8]}"
    }
    
    if additional_context:
        context.update(additional_context)
        
    excel_service = ExcelService()
    
    # 1. Generate Excel file
    excel_path = excel_service.generate_excel_quote(context)
        
    # Record the generated artifact
    db = SessionLocal()
    try:
        if resolved_client_id is None:
            raise ValueError("A generated document must be linked to an existing client.")
        with open(excel_path, "rb") as f:
            file_content = f.read()
            
        document = Document(
            filename=os.path.basename(excel_path),
            filepath=excel_path,
            content=file_content,
            document_type=document_type,
            reference_id=int(reference_id) if reference_id is not None else None,
            client_id=resolved_client_id,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {
        "success": True,
        "file_path": excel_path,
        "document_type": document_type,
        "document_number": context["document_number"],
        "document_id": document.id,
    }
