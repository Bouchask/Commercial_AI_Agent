import ast
import operator
from typing import Dict, Any, List


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _evaluate_expression(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _evaluate_expression(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate_expression(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate_expression(node.left)
        right = _evaluate_expression(node.right)
        if type(node.op) is ast.Pow and abs(right) > 10:
            raise ValueError("Exponent is too large")
        return _BINARY_OPERATORS[type(node.op)](left, right)
    raise ValueError("Only numeric arithmetic is allowed")

def calculate(expression: str) -> Dict[str, Any]:
    """Calculate the result of a mathematical expression."""
    try:
        parsed = ast.parse(expression, mode="eval")
        return {"result": float(_evaluate_expression(parsed))}
    except Exception as e:
        raise RuntimeError(f"Failed to evaluate expression: {str(e)}")

from collections import Counter

def prepare_quote_items(codes: List[str], quantities: Dict[str, int] = None, custom_descriptions: Dict[str, str] = None, discount_percent: float = 0.0, tax_rate: float = 0.20) -> Dict[str, Any]:
    """Look up product codes, apply a discount and tax, and format the output for document generation."""
    from backend.mcp.database.tools import get_services

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

    def normalize_code(code: str) -> str:
        value = str(code).strip()
        return aliases.get(value.lower(), value.upper())
    
    if discount_percent < 0.0 or discount_percent > 1.0:
        raise ValueError("discount_percent must be between 0.0 (0%) and 1.0 (100%)")
        
    quantities = quantities or {}
    custom_descriptions = custom_descriptions or {}
    normalized_codes = [normalize_code(code) for code in codes]
    code_counts = Counter(normalized_codes)
    
    print(f"[DEBUG] prepare_quote_items requested normalized_codes: {normalized_codes}")
    
    services = get_services(list(code_counts.keys()))
    
    print(f"[DEBUG] prepare_quote_items got services from DB: {[s.get('code') for s in services]}")
    
    if not services:
        # Also let's print ALL services to see if it's there
        all_s = get_services()
        print(f"[DEBUG] ALL services in DB: {[s.get('code') for s in all_s]}")
        raise ValueError(f"No catalogue products match the requested codes: {', '.join(codes)}")
        
    items = []
    subtotal = 0.0
    
    for s in services:
        canonical_code = s["code"]
        quantity = quantities.get(canonical_code)
        if quantity is None:
            quantity = next(
                (value for key, value in quantities.items() if normalize_code(key) == canonical_code),
                code_counts[canonical_code],
            )
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            raise ValueError(f"Quantity for {canonical_code} must be a positive integer")

        qty = quantity
        price = float(s.get("unit_price", 0.0))
        line_total = price * qty
        description = custom_descriptions.get(canonical_code)
        if description is None:
            description = next(
                (value for key, value in custom_descriptions.items() if normalize_code(key) == canonical_code),
                s.get("name", "Unknown"),
            )
        items.append({
            "service_id": s["id"],
            "code": canonical_code,
            "description": description,
            "quantity": qty,
            "price": price,
            "line_total": line_total,
            "tax_rate": s.get("tax_rate", tax_rate),
        })
        subtotal += line_total
        
    # Apply discount
    discount_amount = subtotal * discount_percent
    subtotal_discounted = subtotal - discount_amount
    # A catalogue item may define a tax rate different from the request default.
    # Apply the global discount proportionally before calculating each line's tax.
    tax = sum(item["line_total"] * (1 - discount_percent) * float(item["tax_rate"]) for item in items)
    total = subtotal_discounted + tax
    
    return {
        "items": items,
        "original_subtotal": subtotal,
        "discount_amount": discount_amount,
        "discount_percent_val": discount_percent * 100,
        "tax_rate_val": tax_rate * 100,
        "total_ht": subtotal_discounted,
        "tax": tax,
        "total_ttc": total
    }
