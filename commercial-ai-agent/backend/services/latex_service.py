import os
import subprocess
import uuid
import tempfile
from jinja2 import Environment, FileSystemLoader
from backend.config.settings import settings


_LATEX_ESCAPES = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
    "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def _escape_latex(value):
    if isinstance(value, str):
        return "".join(_LATEX_ESCAPES.get(char, char) for char in value)
    if isinstance(value, list):
        return [_escape_latex(item) for item in value]
    if isinstance(value, dict):
        return {key: _escape_latex(item) for key, item in value.items()}
    return value

class LatexService:
    def __init__(self, templates_dir: str = "../templates"):
        # Resolve path relative to backend
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.templates_path = os.path.join(base_dir, "templates")
        self.env = Environment(
            loader=FileSystemLoader(self.templates_path),
            block_start_string='\\BLOCK{',
            block_end_string='}',
            variable_start_string='\\VAR{',
            variable_end_string='}',
            comment_start_string='\\#{',
            comment_end_string='}',
            line_statement_prefix='%%-',
            line_comment_prefix='%#',
            trim_blocks=True,
            autoescape=False,
        )

    def render_template(self, document_type: str, template_name: str, context: dict) -> str:
        """Render a LaTeX template with the given context."""
        template_file = f"{document_type}s/{template_name}.tex"
        template = self.env.get_template(template_file)
        return template.render(**_escape_latex(context))

    def compile_pdf(self, tex_content: str, document_type: str) -> str:
        """
        Compile LaTeX to PDF.
        For MVP, we use a local pdflatex or a docker container.
        If on Vercel (or if pdflatex fails), we fallback to latexonline.cc.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # If on Vercel, we must write to /tmp because the rest of the filesystem is read-only
        is_vercel = os.environ.get("VERCEL") == "1"
        data_dir = "/tmp/data" if is_vercel else os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        doc_id = str(uuid.uuid4())
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, f"{doc_id}.tex")
            with open(tex_path, "w") as f:
                f.write(tex_content)
                
            pdf_source = os.path.join(tmpdir, f"{doc_id}.pdf")
            pdf_dest = os.path.join(data_dir, f"{document_type}_{doc_id}.pdf")
            
            # Helper to compile online
            def compile_online():
                if not settings.ALLOW_ONLINE_LATEX:
                    return False
                import urllib.parse
                import urllib.request
                try:
                    url = "https://latexonline.cc/compile?text=" + urllib.parse.quote(tex_content)
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response:
                        if response.status == 200:
                            with open(pdf_source, "wb") as f:
                                f.write(response.read())
                            return True
                except Exception as e:
                    print(f"Online compilation failed: {e}")
                return False

            if is_vercel:
                success = compile_online()
                if not success:
                    raise RuntimeError("PDF generation failed on Vercel via latexonline.cc")
            else:
                try:
                    subprocess.run(
                        ["docker", "run", "--rm", "-v", f"{tmpdir}:/workdir", "-w", "/workdir", "texlive/texlive:latest", "pdflatex", "-interaction=nonstopmode", f"{doc_id}.tex"],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                except (subprocess.CalledProcessError, FileNotFoundError):
                    try:
                        subprocess.run(
                            ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_path],
                            check=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        # Final fallback
                        success = compile_online()
                        if not success:
                            raise RuntimeError("PDF generation failed: pdflatex not found and online fallback failed.")
            
            if os.path.exists(pdf_source):
                import shutil
                shutil.copy(pdf_source, pdf_dest)
                return pdf_dest
            else:
                raise RuntimeError("PDF generation failed: Output file not found.")
