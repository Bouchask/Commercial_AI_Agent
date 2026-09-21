from typing import List, Dict, Any, Optional, Union
import re
from functools import lru_cache
from sqlalchemy.orm import Session
from backend.database.connection import SessionLocal
from backend.models.client import Client
from backend.models.service import Service
from backend.models.quote import Quote, QuoteItem
from backend.database.catalogue import seed_catalogue

def get_db_session() -> Session:
    return SessionLocal()

def search_client(name: str) -> List[Dict[str, Any]]:
    """Search for a client by name."""
    db = get_db_session()
    try:
        query = db.query(Client).filter(Client.name.ilike(f"%{name}%"))
        try:
            from flask import request
            user = getattr(request, "current_user", None)
            if user and (user.role or "").upper() != "ADMIN":
                query = query.filter(Client.owner_user_id == user.id)
        except RuntimeError:
            pass
        clients = query.all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "address": c.address
            }
            for c in clients
        ]
    finally:
        db.close()

def create_client(name: str, email: Optional[str] = None, phone: Optional[str] = None, address: Optional[str] = None) -> Dict[str, Any]:
    """Create a new client in the database."""
    if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email.strip()):
        raise ValueError(f"Invalid email format: {email}")
    if phone and not re.match(r"^\+?[\d\s\-\(\)]+$", phone.strip()):
        raise ValueError(f"Invalid phone format: {phone}")
        
    db = get_db_session()
    try:
        owner_user_id = None
        try:
            from flask import request
            owner_user_id = getattr(request, "current_user", None).id
        except (RuntimeError, AttributeError):
            pass
        new_client = Client(name=name, email=email, phone=phone, address=address, owner_user_id=owner_user_id)
        db.add(new_client)
        db.commit()
        db.refresh(new_client)
        return {
            "id": new_client.id,
            "name": new_client.name,
            "email": new_client.email,
            "phone": new_client.phone,
            "address": new_client.address
        }
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Failed to create client: {str(e)}")
    finally:
        db.close()

def find_or_create_client(name: str, email: Optional[str] = None, phone: Optional[str] = None, address: Optional[str] = None) -> Dict[str, Any]:
    """Find an existing client by name, or create a new one if not found. Always returns a single client dict with an 'id'."""
    if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email.strip()):
        raise ValueError(f"Invalid email format: {email}")
    if phone and not re.match(r"^\+?[\d\s\-\(\)]+$", phone.strip()):
        raise ValueError(f"Invalid phone format: {phone}")
        
    db = get_db_session()
    try:
        query = db.query(Client).filter(Client.name.ilike(f"%{name}%"))
        owner_user_id = None
        try:
            from flask import request
            user = getattr(request, "current_user", None)
            if user:
                owner_user_id = user.id
                if (user.role or "").upper() != "ADMIN":
                    query = query.filter(Client.owner_user_id == user.id)
        except RuntimeError:
            pass
        existing = query.first()
        if existing:
            return {
                "id": existing.id,
                "name": existing.name,
                "email": existing.email or email,
                "phone": existing.phone or phone,
                "address": existing.address or address
            }
        # Client not found — create new one
        new_client = Client(name=name, email=email, phone=phone, address=address, owner_user_id=owner_user_id)
        db.add(new_client)
        db.commit()
        db.refresh(new_client)
        return {
            "id": new_client.id,
            "name": new_client.name,
            "email": new_client.email,
            "phone": new_client.phone,
            "address": new_client.address
        }
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Failed to find or create client: {str(e)}")
    finally:
        db.close()

def _fetch_all_services_from_db():
    db = get_db_session()
    try:
        if not db.query(Service.id).first():
            seed_catalogue(db)
        return [
            {
                "id": service.id,
                "code": service.code,
                "name": service.name,
                "description": service.description or service.name,
                "unit": service.unit,
                "unit_price": float(service.unit_price),
                "currency": service.currency,
                "tax_rate": float(service.tax_rate),
            }
            for service in db.query(Service).order_by(Service.code).all()
        ]
    finally:
        db.close()

def get_services(codes: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Read the managed catalogue from PostgreSQL, seeding it once if empty."""
    aliases = {
        "ecommerce": "WEB-ECOMM",
        "e-commerce": "WEB-ECOMM",
        "ecommerce_website": "WEB-ECOMM",
        "website_ecommerce": "WEB-ECOMM",
        "seo": "SEO-OPT",
        "seo_optimization": "SEO-OPT",
        "seo-optimization": "SEO-OPT",
        "maintenance_6": "MAINT-6",
        "maintenance_6_months": "MAINT-6",
    }
    
    all_services = _fetch_all_services_from_db()
    
    if not codes:
        return all_services
        
    requested_codes = {
        aliases.get(str(code).strip().lower(), str(code).strip().upper())
        for code in codes
    }
    
    return [s for s in all_services if s["code"] in requested_codes]

import uuid
def create_quote(client_id: int, items: List[Dict[str, Any]], total_ht: float, total_tax: float, total_ttc: float, status: str = "draft") -> Dict[str, Any]:
    """Create a quote header and its immutable commercial line items in one transaction."""
    # Type coercion: handle cases where the LLM/interpolation passes wrong types
    if isinstance(client_id, list):
        client_id = client_id[0] if client_id else None
    if isinstance(client_id, dict):
        client_id = client_id.get("id", client_id.get("client_id"))
    client_id = int(client_id)
    total_ht = float(total_ht)
    total_tax = float(total_tax)
    total_ttc = float(total_ttc)
    if not items:
        raise ValueError("A quote must contain at least one item.")
    
    db = get_db_session()
    try:
        new_quote = Quote(
            quote_number=f"QTE-{str(uuid.uuid4())[:8].upper()}",
            client_id=client_id,
            subtotal=total_ht,
            tax_total=total_tax,
            total_amount=total_ttc,
            status=status
        )
        db.add(new_quote)
        db.flush()
        for item in items:
            service_id = item.get("service_id", item.get("id"))
            if not service_id:
                desc = item.get("description", "Service personnalisé")
                service = db.query(Service).filter(Service.name == desc).first()
                if not service:
                    price = float(item.get("price", 0.0))
                    code = f"CUS-{str(uuid.uuid4())[:8].upper()}"
                    service = Service(code=code, name=desc, description=desc, unit_price=price)
                    db.add(service)
                    db.flush()
                service_id = service.id
                
            service = db.get(Service, int(service_id))
            if not service:
                raise ValueError(f"Service {service_id} does not exist.")
            quantity = float(item.get("quantity", 1))
            if quantity <= 0:
                raise ValueError("Item quantity must be greater than zero.")
            db.add(QuoteItem(
                quote_id=new_quote.id,
                service_id=service.id,
                quantity=quantity,
                unit_price=float(item.get("price", service.unit_price)),
                tax_rate=float(item.get("tax_rate", service.tax_rate)),
                discount=float(item.get("discount_percent", 0.0)),
            ))
        db.commit()
        db.refresh(new_quote)
        return {
            "id": new_quote.id,
            "quote_number": new_quote.quote_number,
            "status": new_quote.status,
            "items_count": len(items),
            "total_ttc": float(new_quote.total_amount),
        }
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Failed to create quote: {str(e)}")
    finally:
        db.close()


def get_quote(quote_id: int) -> Dict[str, Any]:
    """Return a quote and its stored commercial lines for follow-up actions."""
    db = get_db_session()
    try:
        quote = db.get(Quote, int(quote_id))
        if not quote:
            raise ValueError("Quote not found.")
        return {
            "id": quote.id,
            "quote_number": quote.quote_number,
            "client_id": quote.client_id,
            "status": quote.status,
            "total_ht": float(quote.subtotal),
            "total_tax": float(quote.tax_total),
            "total_ttc": float(quote.total_amount),
            "items": [
                {
                    "service_id": line.service_id,
                    "quantity": float(line.quantity),
                    "unit_price": float(line.unit_price),
                    "tax_rate": float(line.tax_rate),
                    "discount": float(line.discount),
                }
                for line in quote.items
            ],
        }
    finally:
        db.close()

from sqlalchemy.sql import text
def execute_sql_query(query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute a raw SQL query against the database and return results."""
    db = get_db_session()
    try:
        if parameters is None:
            parameters = {}
            
        stmt = text(query)
        result = db.execute(stmt, parameters)
        
        # If the query returns rows (e.g. SELECT)
        if result.returns_rows:
            rows = result.fetchall()
            keys = result.keys()
            data = [dict(zip(keys, row)) for row in rows]
            db.commit()
            return {"status": "success", "rows": data, "rowcount": len(data)}
        else:
            # For INSERT, UPDATE, DELETE
            db.commit()
            return {"status": "success", "rowcount": result.rowcount}
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"SQL Execution failed: {str(e)}")
    finally:
        db.close()

def create_service(name: str, unit_price: float, description: Optional[str] = None) -> Dict[str, Any]:
    """Create a new service in the catalogue."""
    db = get_db_session()
    try:
        import uuid
        code = f"SRV-{str(uuid.uuid4())[:8].upper()}"
        service = Service(
            code=code,
            name=name,
            description=description,
            unit_price=float(unit_price)
        )
        db.add(service)
        db.commit()
        db.refresh(service)
        return {
            "status": "success",
            "message": f"Service created successfully",
            "service_id": service.id,
            "code": service.code,
            "name": service.name,
            "unit_price": service.unit_price
        }
    except Exception as e:
        db.rollback()
        raise ValueError(f"Failed to create service: {e}")
    finally:
        db.close()

def update_service_price(service_identifier: Union[int, str], new_price: float) -> Dict[str, Any]:
    """Update the price of an existing service by ID or name."""
    db = get_db_session()
    try:
        service = None
        if isinstance(service_identifier, int) or (isinstance(service_identifier, str) and service_identifier.isdigit()):
            service = db.get(Service, int(service_identifier))
        else:
            service = db.query(Service).filter(Service.name.ilike(f"%{service_identifier}%")).first()
            
        if not service:
            raise ValueError(f"Service '{service_identifier}' not found.")
            
        old_price = service.unit_price
        service.unit_price = float(new_price)
        db.commit()
        db.refresh(service)
        return {
            "status": "success",
            "message": f"Service price updated",
            "service_id": service.id,
            "name": service.name,
            "old_price": old_price,
            "new_price": service.unit_price
        }
    except Exception as e:
        db.rollback()
        raise ValueError(f"Failed to update service price: {e}")
    finally:
        db.close()
