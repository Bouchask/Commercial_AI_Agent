import sys, urllib.parse, urllib.request
sys.path.append("/Users/ggffghg/Desktop/assitance ai/commercial-ai-agent")
from backend.services.latex_service import LatexService
ls = LatexService()
context = {
    "client_name": "Test Client",
    "items": [{"code": "WEB", "description": "Website", "quantity": 1, "price": 1000, "line_total": 1000, "tax_rate": 20}],
    "subtotal": 1000, "original_subtotal": 1000, "discount_amount": 0, "discount_percent_val": 0, "tax_rate_val": 20, "tax": 200, "total": 1200,
    "document_number": "QUO-12345"
}
tex = ls.render_template("quote", "b2b", context)

url = "https://latexonline.cc/compile?text=" + urllib.parse.quote(tex)
print("URL Length:", len(url))
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        if response.status == 200:
            print("Success! Size:", len(response.read()))
        else:
            print("Failed:", response.status)
except Exception as e:
    print("Error:", e)
