from flask import Blueprint, request, jsonify
from decimal import Decimal, InvalidOperation
from math import isfinite
import uuid
from backend.api.auth import jwt_required, roles_required
from backend.database.connection import SessionLocal
from backend.models.client import Client
from backend.models.service import Service
from backend.models.quote import Quote, QuoteItem
from backend.models.invoice import Invoice, InvoiceItem

bp = Blueprint('dashboard', __name__, url_prefix='/api')

def _is_admin():
    return (request.current_user.role or "").upper() == "ADMIN"

def _owned_clients(db):
    query = db.query(Client)
    return query if _is_admin() else query.filter(Client.owner_user_id == request.current_user.id)

def _client_or_404(db, client_id):
    client = _owned_clients(db).filter(Client.id == client_id).first()
    if not client:
        return None
    return client

def _number(value, field, *, minimum=0, maximum=None):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field} must be a number")
    if not number.is_finite() or number < Decimal(str(minimum)) or (maximum is not None and number > Decimal(str(maximum))):
        raise ValueError(f"{field} is outside the permitted range")
    return number

def _line_items(db, items):
    if not isinstance(items, list) or not items or len(items) > 100:
        raise ValueError("items must contain between 1 and 100 entries")
    parsed, subtotal, tax_total = [], Decimal("0"), Decimal("0")
    for item in items:
        if not isinstance(item, dict): raise ValueError("each item must be an object")
        try: service_id = int(item["service_id"])
        except (KeyError, TypeError, ValueError): raise ValueError("each item requires a valid service_id")
        if not db.get(Service, service_id): raise ValueError("service_id does not exist")
        quantity = _number(item.get("quantity", 1), "quantity", minimum="0.0001")
        unit_price = _number(item.get("unit_price"), "unit_price", minimum=0)
        tax_rate = _number(item.get("tax_rate", 20), "tax_rate", minimum=0, maximum=100)
        parsed.append((service_id, quantity, unit_price, tax_rate))
        subtotal += quantity * unit_price
        tax_total += quantity * unit_price * tax_rate / Decimal("100")
    return parsed, subtotal, tax_total


@bp.route('/clients', methods=['GET'])
@jwt_required
def list_clients():
    db = SessionLocal()
    try:
        limit = max(1, min(int(request.args.get('limit', 20)), 100))
        offset = max(0, int(request.args.get('offset', 0)))
        query = _owned_clients(db).order_by(Client.created_at.desc()).limit(limit).offset(offset).all()
        results = [
            {"id": c.id, "name": c.name, "email": c.email, "phone": c.phone, "address": c.address}
            for c in query
        ]
        return jsonify(results)
    finally:
        db.close()


@bp.route('/clients', methods=['POST'])
@jwt_required
@roles_required('ADMIN','SALES')
def create_client():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload.get('name'), str) or not payload['name'].strip() or len(payload['name']) > 255:
        return jsonify({"error": "Missing 'name'"}), 400
    db = SessionLocal()
    try:
        client = Client(name=payload['name'].strip(), email=payload.get('email'), phone=payload.get('phone'), address=payload.get('address'), owner_user_id=request.current_user.id)
        db.add(client)
        db.commit()
        db.refresh(client)
        return jsonify({"id": client.id, "name": client.name}), 201
    finally:
        db.close()


@bp.route('/services', methods=['GET'])
@jwt_required
def list_services():
    db = SessionLocal()
    try:
        services = db.query(Service).order_by(Service.name).all()
        return jsonify([
            {"id": s.id, "code": s.code, "name": s.name, "unit_price": s.unit_price, "currency": s.currency}
            for s in services
        ])
    finally:
        db.close()


@bp.route('/services', methods=['POST'])
@jwt_required
@roles_required('ADMIN','SALES')
def create_service():
    payload = request.get_json(silent=True) or {}
    # Accept either {code,name,unit_price} or {title,price}
    if 'code' in payload and 'name' in payload and 'unit_price' in payload:
        code = payload['code']
        name = payload['name']
        unit_price = _number(payload['unit_price'], 'unit_price', minimum=0)
    elif 'title' in payload and 'price' in payload:
        code = payload.get('code') or payload['title'].lower().replace(' ', '-')[:20]
        name = payload['title']
        unit_price = _number(payload['price'], 'price', minimum=0)
    else:
        return jsonify({"error": "Missing service fields (expected code,name,unit_price or title,price)"}), 400

    db = SessionLocal()
    try:
        if not isinstance(code, str) or not code.strip() or not isinstance(name, str) or not name.strip():
            return jsonify({"error": "Invalid service fields"}), 400
        service = Service(code=code.strip().upper(), name=name.strip(), description=payload.get('description'), unit_price=float(unit_price), currency=payload.get('currency', 'MAD'))
        db.add(service)
        db.commit()
        db.refresh(service)
        return jsonify({"id": service.id, "code": service.code, "name": service.name, "price": service.unit_price}), 201
    except (ValueError, InvalidOperation) as exc:
        db.rollback(); return jsonify({"error": str(exc)}), 400
    finally:
        db.close()


@bp.route('/quotes', methods=['GET'])
@jwt_required
def list_quotes():
    db = SessionLocal()
    try:
        limit = max(1, min(int(request.args.get('limit', 20)), 100)); offset = max(0, int(request.args.get('offset', 0)))
        q = db.query(Quote).join(Client).filter(Client.owner_user_id == request.current_user.id).order_by(Quote.created_at.desc()).limit(limit).offset(offset).all() if not _is_admin() else db.query(Quote).order_by(Quote.created_at.desc()).limit(limit).offset(offset).all()
        out = []
        for quote in q:
            out.append({
                "id": quote.id,
                "quote_number": quote.quote_number,
                "client_id": quote.client_id,
                "status": quote.status,
                "subtotal": quote.subtotal,
                "tax_total": quote.tax_total,
                "total_amount": quote.total_amount,
                "created_at": quote.created_at.isoformat() if quote.created_at else None
            })
        return jsonify(out)
    finally:
        db.close()


@bp.route('/quotes', methods=['POST'])
@jwt_required
@roles_required('ADMIN','SALES')
def create_quote():
    payload = request.get_json(silent=True) or {}
    # allow client to omit quote_number; generate server-side when missing
    required = ['client_id', 'items']
    for r in required:
        if r not in payload:
            return jsonify({"error": f"Missing '{r}'"}), 400

    quote_number = payload.get('quote_number') or f"Q-{uuid.uuid4().hex[:12].upper()}"

    db = SessionLocal()
    try:
        client = _client_or_404(db, int(payload['client_id']))
        if not client: return jsonify({"error": "Client not found"}), 404
        parsed_items, subtotal, tax_total = _line_items(db, payload['items'])
        quote = Quote(quote_number=quote_number, client_id=client.id, status=payload.get('status', 'DRAFT'))
        db.add(quote)
        db.flush()

        for service_id, quantity, unit_price, tax_rate in parsed_items:
            qi = QuoteItem(quote_id=quote.id, service_id=service_id, quantity=float(quantity), unit_price=float(unit_price), tax_rate=float(tax_rate))
            db.add(qi)

        quote.subtotal = float(subtotal); quote.tax_total = float(tax_total); quote.total_amount = float(subtotal + tax_total)
        db.commit()
        db.refresh(quote)
        return jsonify({"id": quote.id, "quote_number": quote.quote_number}), 201
    except (ValueError, TypeError, InvalidOperation) as exc:
        db.rollback(); return jsonify({"error": str(exc)}), 400
    finally:
        db.close()


@bp.route('/invoices', methods=['GET'])
@jwt_required
def list_invoices():
    db = SessionLocal()
    try:
        invoices = db.query(Invoice).join(Client).filter(Client.owner_user_id == request.current_user.id).order_by(Invoice.created_at.desc()).limit(50).all() if not _is_admin() else db.query(Invoice).order_by(Invoice.created_at.desc()).limit(50).all()
        return jsonify([
            {"id": inv.id, "invoice_number": inv.invoice_number, "client_id": inv.client_id, "total_amount": inv.total_amount, "status": inv.status}
            for inv in invoices
        ])
    finally:
        db.close()


@bp.route('/invoices', methods=['POST'])
@jwt_required
@roles_required('ADMIN','SALES')
def create_invoice():
    payload = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        # Support creating invoice from an existing quote by providing quote_id
        if 'quote_id' in payload:
            quote_id = int(payload['quote_id'])
            quote_query = db.query(Quote).filter(Quote.id == quote_id)
            if not _is_admin(): quote_query = quote_query.join(Client).filter(Client.owner_user_id == request.current_user.id)
            quote = quote_query.first()
            if not quote:
                return jsonify({"error": "Quote not found"}), 404
            invoice_number = payload.get('invoice_number') or f"I-{uuid.uuid4().hex[:12].upper()}"
            invoice = Invoice(invoice_number=invoice_number, client_id=quote.client_id, status=payload.get('status', 'DRAFT'))
            db.add(invoice)
            db.flush()
            # copy items from quote
            items = db.query(QuoteItem).filter(QuoteItem.quote_id == quote.id).all()
            subtotal = 0.0
            tax_total = 0.0
            for it in items:
                ii = InvoiceItem(invoice_id=invoice.id, service_id=it.service_id, quantity=it.quantity, unit_price=it.unit_price, tax_rate=it.tax_rate)
                db.add(ii)
                line_ht = it.quantity * it.unit_price
                line_tax = line_ht * (it.tax_rate / 100.0)
                subtotal += line_ht
                tax_total += line_tax
            invoice.subtotal = subtotal
            invoice.tax_total = tax_total
            invoice.total_amount = subtotal + tax_total
            db.commit()
            db.refresh(invoice)
            return jsonify({"id": invoice.id, "invoice_number": invoice.invoice_number}), 201

        # Otherwise expect full invoice payload with items
        required = ['invoice_number', 'client_id', 'items']
        for r in required:
            if r not in payload:
                return jsonify({"error": f"Missing '{r}'"}), 400

        client = _client_or_404(db, int(payload['client_id']))
        if not client: return jsonify({"error": "Client not found"}), 404
        parsed_items, subtotal, tax_total = _line_items(db, payload['items'])
        invoice = Invoice(invoice_number=payload['invoice_number'], client_id=client.id, status=payload.get('status', 'DRAFT'))
        db.add(invoice)
        db.flush()

        for service_id, quantity, unit_price, tax_rate in parsed_items:
            ii = InvoiceItem(invoice_id=invoice.id, service_id=service_id, quantity=float(quantity), unit_price=float(unit_price), tax_rate=float(tax_rate))
            db.add(ii)

        invoice.subtotal = float(subtotal); invoice.tax_total = float(tax_total); invoice.total_amount = float(subtotal + tax_total)
        db.commit()
        db.refresh(invoice)
        return jsonify({"id": invoice.id, "invoice_number": invoice.invoice_number}), 201
    except (ValueError, TypeError, InvalidOperation) as exc:
        db.rollback(); return jsonify({"error": str(exc)}), 400
    finally:
        db.close()


@bp.route('/agents', methods=['GET'])
@jwt_required
def list_agents():
    # allow ADMIN/SALES/AGENT to list agents
    if getattr(request, 'current_user', None) is None:
        return jsonify({"error": "Authentication required"}), 401
    # no extra role restriction for listing

    """Return users that can act as agents. Uses users table and role field."""
    from backend.models.user import User
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        results = [
            {"id": u.id, "email": u.email, "role": u.role}
            for u in users if (u.role or '').upper() in ('AGENT', 'SALES', 'ADMIN')
        ]
        return jsonify(results)
    finally:
        db.close()


@bp.route('/assignments', methods=['GET'])
@jwt_required
def list_assignments():
    # allow SALES/ADMIN/AGENT to view assignments; agents only see their own
    current_user = getattr(request, 'current_user', None)
    db = SessionLocal()
    try:
        from backend.models.assignment import Assignment
        rows = db.query(Assignment).join(Client).filter(Client.owner_user_id == current_user.id).order_by(Assignment.created_at.desc()).limit(100).all() if not _is_admin() else db.query(Assignment).order_by(Assignment.created_at.desc()).limit(100).all()
        out = []
        for a in rows:
            if current_user.role and current_user.role.upper() == 'AGENT' and a.agent_id != current_user.id:
                continue
            out.append({
                "id": a.id,
                "agent_id": a.agent_id,
                "client_id": a.client_id,
                "notes": a.notes,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None
            })
        return jsonify(out)
    finally:
        db.close()



@bp.route('/assignments', methods=['POST'])
@jwt_required
@roles_required('ADMIN', 'SALES')
def create_assignment():
    payload = request.json or {}
    required = ['agent_id', 'client_id']
    for r in required:
        if r not in payload:
            return jsonify({"error": f"Missing '{r}'"}), 400

    db = SessionLocal()
    try:
        from backend.models.assignment import Assignment
        if not _client_or_404(db, int(payload['client_id'])): return jsonify({"error": "Client not found"}), 404
        from backend.models.user import User
        if not db.get(User, int(payload['agent_id'])): return jsonify({"error": "Agent not found"}), 404
        a = Assignment(agent_id=int(payload['agent_id']), client_id=int(payload['client_id']), notes=payload.get('notes'), status=payload.get('status', 'active'))
        db.add(a)
        db.commit()
        db.refresh(a)
        return jsonify({"id": a.id, "agent_id": a.agent_id, "client_id": a.client_id, "status": a.status}), 201
    finally:
        db.close()


# Tool call / approval workflow endpoints

@bp.route('/toolcalls/pending', methods=['GET'])
@jwt_required
def list_pending_toolcalls():
    db = SessionLocal()
    try:
        from backend.models.execution import Execution, ToolCall
        rows = db.query(ToolCall).join(Execution, Execution.id == ToolCall.execution_id).filter(ToolCall.status == 'WAITING_APPROVAL').filter(Execution.user_id == request.current_user.id).order_by(ToolCall.created_at.desc()).all() if not _is_admin() else db.query(ToolCall).filter(ToolCall.status == 'WAITING_APPROVAL').order_by(ToolCall.created_at.desc()).all()
        out = []
        for t in rows:
            out.append({"id": t.id, "execution_id": t.execution_id, "tool": t.tool_name, "arguments": t.arguments, "status": t.status, "created_at": t.created_at.isoformat() if t.created_at else None})
        return jsonify(out)
    finally:
        db.close()


@bp.route('/toolcalls/<int:tool_call_id>/approve', methods=['POST'])
@jwt_required
@roles_required('ADMIN','SALES')
def approve_toolcall(tool_call_id):
    db = SessionLocal()
    try:
        from backend.models.execution import Execution, ToolCall
        from backend.mcp.client import MCPClient
        tc = db.query(ToolCall).filter(ToolCall.id == tool_call_id).first()
        if tc and not _is_admin():
            owner = db.get(Execution, tc.execution_id)
            if not owner or owner.user_id != request.current_user.id: tc = None
        if not tc:
            return jsonify({"error": "ToolCall not found"}), 404
        if tc.status != 'WAITING_APPROVAL':
            return jsonify({"error": "ToolCall not awaiting approval"}), 400
        # Execute the tool using MCP client
        mcp = MCPClient()
        try:
            result = mcp.invoke(tc.tool_name, tc.arguments or {}, execution_id=tc.execution_id)
            tc.status = 'SUCCESS'
            tc.duration = 0.0
            db.commit()
            return jsonify({"success": True, "result": result})
        except Exception as e:
            tc.status = 'FAILED'
            db.commit()
            return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@bp.route('/quotes/<int:quote_id>/send', methods=['POST'])
@jwt_required
@roles_required('ADMIN','SALES')
def send_quote(quote_id):
    """Create a document generation toolcall for the quote and schedule email prepare/send.
    Document generation requires approval; email.send also requires approval so it's queued separately.
    Returns a tool_call id that can be approved via /toolcalls/<id>/approve
    """
    db = SessionLocal()
    try:
        quote_query = db.query(Quote).filter(Quote.id == quote_id)
        if not _is_admin(): quote_query = quote_query.join(Client).filter(Client.owner_user_id == request.current_user.id)
        quote = quote_query.first()
        if not quote:
            return jsonify({"error": "Quote not found"}), 404
        # Build document payload
        items = db.query(QuoteItem).filter(QuoteItem.quote_id == quote.id).all()
        doc_items = []
        for it in items:
            svc = db.query(Service).filter(Service.id == it.service_id).first()
            doc_items.append({
                "description": svc.name if svc else str(it.service_id),
                "quantity": it.quantity,
                "price": it.unit_price
            })
        doc_payload = {
            "document_type": "quote",
            "client_name": quote.client.name if quote.client else "",
            "client_id": quote.client_id,
            "items": doc_items,
            "total_ht": quote.subtotal,
            "tax": quote.tax_total,
            "total_ttc": quote.total_amount,
            "reference_id": quote.id
        }
        # Create execution record
        from backend.models.execution import Execution, ToolCall
        import uuid
        exec_id = str(uuid.uuid4())
        ex = Execution(id=exec_id, session_id=None, user_id=getattr(request, 'current_user', None).id if getattr(request, 'current_user', None) else None, state='RECEIVED')
        db.add(ex)
        db.flush()
        # Create waiting tool call for document.generate
        tc = ToolCall(execution_id=exec_id, tool_name='document.generate', arguments=doc_payload, status='WAITING_APPROVAL', duration=None)
        db.add(tc)
        db.commit()
        db.refresh(tc)
        return jsonify({"execution_id": exec_id, "tool_call_id": tc.id, "status": tc.status}), 202
    finally:
        db.close()


# End of extended dashboard endpoints
