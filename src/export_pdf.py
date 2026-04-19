"""
Genera el PDF técnico del artículo (versión completa con todas las fórmulas).

Lee docs/articulo_tecnico.md, reemplaza cada bloque matemático por el PNG
correspondiente de outputs/figures/formulas/, los bloques de código por los
PNG de outputs/figures/code/, renderiza a HTML con tema light profesional
(dark se ve mal impreso) y convierte a PDF con WeasyPrint.

Salida: outputs/articulo_tecnico.pdf
"""
from __future__ import annotations

import re
from pathlib import Path

import markdown
from weasyprint import CSS, HTML


ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "docs" / "articulo_tecnico.md"
PDF_PATH = ROOT / "outputs" / "articulo_tecnico.pdf"
FORMULAS_DIR = ROOT / "outputs" / "figures" / "formulas"
CODE_DIR = ROOT / "outputs" / "figures" / "code"


CSS_PDF = """
@page {
  size: A4;
  margin: 2.2cm 2cm;
  @top-right {
    content: "Optimización de Compras EDEs · RD";
    font-family: 'Inter', sans-serif;
    font-size: 8pt;
    color: #64748B;
  }
  @bottom-right {
    content: "p. " counter(page) " / " counter(pages);
    font-family: 'JetBrains Mono', monospace;
    font-size: 8pt;
    color: #64748B;
  }
  @bottom-left {
    content: "github.com/leanmasterpymes/energia_optima";
    font-family: 'JetBrains Mono', monospace;
    font-size: 8pt;
    color: #94A3B8;
  }
}

* { box-sizing: border-box; }

body {
  font-family: 'Inter', -apple-system, sans-serif;
  font-size: 10.5pt;
  line-height: 1.55;
  color: #1E293B;
}

h1 {
  font-size: 22pt;
  font-weight: 700;
  color: #0F172A;
  margin: 0 0 0.4rem 0;
  letter-spacing: -0.02em;
  font-family: 'Space Grotesk', sans-serif;
}
h2 {
  font-size: 15pt;
  font-weight: 600;
  color: #0F172A;
  margin: 1.8rem 0 0.7rem 0;
  padding-left: 0.6rem;
  border-left: 3px solid #0891B2;
  page-break-after: avoid;
  font-family: 'Space Grotesk', sans-serif;
}
h3 {
  font-size: 12pt;
  font-weight: 600;
  color: #0891B2;
  margin: 1.2rem 0 0.4rem 0;
  page-break-after: avoid;
  font-family: 'Space Grotesk', sans-serif;
}

p { margin: 0 0 0.7rem 0; orphans: 3; widows: 3; }
strong { color: #0F172A; font-weight: 600; }
em { color: #334155; }

/* CALLOUTS (blockquotes) */
blockquote {
  margin: 1rem 0 1.3rem 0;
  padding: 0.9rem 1rem;
  background: #FEF9E7;
  border-left: 4px solid #CA8A04;
  border-radius: 4px;
  font-size: 10pt;
  color: #374151;
  page-break-inside: avoid;
}
blockquote strong { color: #92400E; }
blockquote p { margin: 0; }

/* CODE */
pre {
  background: #F1F5F9;
  border: 1px solid #CBD5E1;
  border-radius: 6px;
  padding: 0.8rem 1rem;
  font-size: 8.5pt;
  font-family: 'JetBrains Mono', monospace;
  line-height: 1.4;
  overflow-x: auto;
  page-break-inside: avoid;
  margin: 0.8rem 0 1rem 0;
}
code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9pt;
  color: #0F172A;
}
p code, li code, td code {
  background: #E0F2FE;
  border: 1px solid #BAE6FD;
  padding: 0.05em 0.35em;
  border-radius: 3px;
  font-size: 8.8pt;
  color: #075985;
}

/* FORMULAS (imagenes PNG) */
figure.formula {
  text-align: center;
  margin: 1rem auto 1.2rem auto;
  page-break-inside: avoid;
}
figure.formula img {
  max-width: 90%;
  max-height: 120px;
  height: auto;
}
figure.formula.display img {
  max-height: 140px;
}
figure.code-block {
  text-align: center;
  margin: 1rem auto 1.2rem auto;
  page-break-inside: avoid;
}
figure.code-block img {
  max-width: 100%;
  max-height: 420px;
  height: auto;
  border: 1px solid #CBD5E1;
  border-radius: 6px;
}

/* TABLES */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.8rem 0 1.2rem 0;
  font-size: 9.5pt;
  page-break-inside: avoid;
}
th {
  background: #E0F2FE;
  color: #0C4A6E;
  font-family: 'JetBrains Mono', monospace;
  font-size: 8pt;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.55rem 0.7rem;
  text-align: left;
  border-bottom: 2px solid #0891B2;
}
td {
  padding: 0.5rem 0.7rem;
  border-bottom: 1px solid #E2E8F0;
  color: #1E293B;
}

/* LISTS */
ul, ol { padding-left: 1.2rem; margin: 0.5rem 0 1rem 0; }
li { margin-bottom: 0.3rem; }
li::marker { color: #0891B2; }

a { color: #0E7490; text-decoration: none; }

hr {
  border: none; height: 1px; background: #CBD5E1; margin: 1.5rem 0;
}

/* Cover-like header */
.hero-meta {
  font-family: 'JetBrains Mono', monospace;
  font-size: 8pt;
  color: #64748B;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 0.4rem;
}
.hero-subtitle {
  color: #475569;
  font-size: 11pt;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #E2E8F0;
}
"""


def preparar_math_inline(md_text: str) -> tuple[str, dict[str, str]]:
    """Enmascara math blocks antes del parser markdown."""
    mapping: dict[str, str] = {}
    counter = [0]

    def _token(html: str) -> str:
        key = f"MATHTOKEN{counter[0]:04d}"
        counter[0] += 1
        mapping[key] = html
        return key

    code_blocks: list[str] = []

    def _proteger(m: re.Match) -> str:
        code_blocks.append(m.group(0))
        return f"\x00CB{len(code_blocks)-1}\x00"

    md_text = re.sub(r"```.*?```", _proteger, md_text, flags=re.DOTALL)
    md_text = re.sub(r"`[^`\n]+`", _proteger, md_text)

    # Display: reemplaza cada $$...$$ por la imagen correspondiente (en orden)
    display_idx = [0]

    def _display(m: re.Match) -> str:
        display_idx[0] += 1
        rel = f"outputs/figures/formulas/ecuacion_{display_idx[0]:02d}.png"
        abs_path = ROOT / rel
        if not abs_path.exists():
            # Si no existe la imagen, renderizamos el raw latex como fallback
            return _token(f'<code>{m.group(1).strip()}</code>')
        src = abs_path.as_uri()
        return _token(
            f'<figure class="formula display">'
            f'<img src="{src}" alt="ecuacion {display_idx[0]}"/>'
            f'</figure>'
        )

    md_text = re.sub(r"\$\$(.+?)\$\$", _display, md_text, flags=re.DOTALL)

    # Inline: $...$ no adyacente a dígito, con contenido tipo math
    inline_idx = [0]

    def _inline(m: re.Match) -> str:
        before, content = m.group(1), m.group(2)
        es_math = bool(re.search(r"[\\_^{}]", content))
        es_var = bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", content))
        if not (es_math or es_var):
            return m.group(0)
        inline_idx[0] += 1
        rel = f"outputs/figures/formulas/inline_{inline_idx[0]:02d}.png"
        abs_path = ROOT / rel
        if not abs_path.exists():
            return f"{before}<code>{content}</code>"
        src = abs_path.as_uri()
        return (
            f'{before}<img src="{src}" alt="math {inline_idx[0]}" '
            f'style="height:1em;vertical-align:middle;"/>'
        )

    md_text = re.sub(
        r"(^|[\s(\[{,;:])\$([^\$\n]+?)\$(?=[\s.,;:!?\])}]|$)",
        _inline,
        md_text,
        flags=re.MULTILINE,
    )

    for i, cb in enumerate(code_blocks):
        md_text = md_text.replace(f"\x00CB{i}\x00", cb)

    return md_text, mapping


def reemplazar_codigo_por_imagen(md_text: str) -> str:
    """Reemplaza ```python ... ``` por la imagen PNG correspondiente."""
    code_idx = [0]

    def _sub(m: re.Match) -> str:
        lang = (m.group(1) or "text").strip().lower()
        if lang in {"", "text", "txt", "ascii"}:
            return m.group(0)
        code_idx[0] += 1
        rel = ROOT / f"outputs/figures/code/codigo_{code_idx[0]:02d}.png"
        if not rel.exists():
            return m.group(0)
        src = rel.as_uri()
        return (
            f'\n\n<figure class="code-block">'
            f'<img src="{src}" alt="codigo {code_idx[0]}"/>'
            f'</figure>\n\n'
        )

    return re.sub(
        r"```([a-zA-Z0-9_+\-]*)\n(.*?)\n```",
        _sub,
        md_text,
        flags=re.DOTALL,
    )


def render_to_pdf() -> None:
    md_text = MD_PATH.read_text(encoding="utf-8")
    md_text, math_map = preparar_math_inline(md_text)
    md_text = reemplazar_codigo_por_imagen(md_text)

    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "attr_list", "toc"],
    )
    body = md.convert(md_text)
    for key, value in math_map.items():
        body = body.replace(key, value)

    from datetime import datetime
    fecha = datetime.now().strftime("%Y-%m-%d")

    html_full = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Optimización de Compras de Energía — EDEs Dominicanas · Versión técnica</title>
</head>
<body>
<div class="hero-meta">Versión técnica · {fecha} · github.com/leanmasterpymes/energia_optima</div>
{body}
</body>
</html>
"""

    HTML(string=html_full, base_url=str(ROOT)).write_pdf(
        str(PDF_PATH),
        stylesheets=[CSS(string=CSS_PDF)],
    )
    size_kb = PDF_PATH.stat().st_size / 1024
    print(f"✓ {PDF_PATH.relative_to(ROOT)}  ({size_kb:,.0f} KB)")


if __name__ == "__main__":
    render_to_pdf()
