"""
Renderiza los documentos de docs/*.md a HTML dark-premium.

Genera:
  docs/articulo_linkedin.html  — artículo principal con figuras
  docs/guia_explicativa.html   — guión de respuestas
  docs/glosario.html           — glosario alfabetico con nav

- CSS dark premium inspirado en el dashboard (Inter + Space Grotesk + JetBrains Mono)
- MathJax (CDN) para las formulas en LaTeX
- highlight.js (CDN) para los bloques de codigo
- Inserta las figuras outputs/figures/*.png en las secciones relevantes
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import markdown


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "outputs" / "figures"


@dataclass
class DocSpec:
    md_path: Path
    html_path: Path
    page_title: str
    header_eyebrow: str
    header_meta: str
    insert_figures: dict[str, str] = field(default_factory=dict)
    add_nav: bool = False  # solo glosario necesita nav alfabetico


DOCS: list[DocSpec] = [
    DocSpec(
        md_path=ROOT / "docs" / "articulo_linkedin.md",
        html_path=ROOT / "docs" / "articulo_linkedin.html",
        page_title="Optimización de Compras de Energía — EDEs RD",
        header_eyebrow="// Energy Intelligence · República Dominicana",
        header_meta="Artículo técnico · versión preview local",
        insert_figures={
            "El problema que nadie cuantifica": "01_hero_ahorro.png",
            "Resultados del escenario base":    "06_comparacion_kpis.png",
            "La capa de IA":                    "07_forecast_vs_real.png",
            "Dashboard Streamlit":              "02_despacho_horario.png",
        },
    ),
    DocSpec(
        md_path=ROOT / "docs" / "guia_explicativa.md",
        html_path=ROOT / "docs" / "guia_explicativa.html",
        page_title="Guía explicativa — EDEs RD",
        header_eyebrow="// Preparación técnica · guion de respuestas",
        header_meta="Material personal · no publicar",
    ),
    DocSpec(
        md_path=ROOT / "docs" / "glosario.md",
        html_path=ROOT / "docs" / "glosario.html",
        page_title="Glosario técnico — EDEs RD",
        header_eyebrow="// Glosario técnico · orden alfabético",
        header_meta="Referencia rápida de términos del modelo",
        add_nav=True,
    ),
]


CSS = """
:root {
  --bg: #0A0E1A;
  --bg-panel: #111827;
  --bg-elev: #1E293B;
  --ink: #F1F5F9;
  --ink-soft: #94A3B8;
  --ink-dim: #64748B;
  --accent: #22D3EE;
  --accent-glow: rgba(34,211,238,0.25);
  --emerald: #34D399;
  --gold: #FBBF24;
  --coral: #F87171;
  --violet: #A78BFA;
  --border: rgba(255,255,255,0.08);
  --border-hot: rgba(34,211,238,0.35);
}
* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0;
  background:
    radial-gradient(1400px 700px at 90% -20%, rgba(34,211,238,0.08), transparent 60%),
    radial-gradient(1000px 600px at -10% 110%, rgba(167,139,250,0.06), transparent 60%),
    var(--bg);
  color: var(--ink);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 17px;
  line-height: 1.7;
  letter-spacing: -0.005em;
}
main {
  max-width: 860px;
  margin: 0 auto;
  padding: 5rem 2rem 6rem 2rem;
}
header.hero {
  border-bottom: 1px solid var(--border);
  padding-bottom: 1.5rem;
  margin-bottom: 3rem;
}
header.hero .eyebrow {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem; font-weight: 600;
  color: var(--accent);
  letter-spacing: 0.22em; text-transform: uppercase;
  margin-bottom: 0.8rem;
}
header.hero .meta {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  color: var(--ink-dim);
  letter-spacing: 0.08em;
  margin-top: 1rem;
}
h1, h2, h3 {
  font-family: 'Space Grotesk', sans-serif;
  color: var(--ink);
  letter-spacing: -0.02em;
  line-height: 1.2;
}
h1 {
  font-size: 2.6rem; font-weight: 700; margin: 0 0 0.5rem 0;
  background: linear-gradient(135deg, #FFFFFF 0%, #94A3B8 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
h2 {
  font-size: 1.75rem; font-weight: 700;
  margin: 3rem 0 1rem 0;
  padding-left: 0.9rem;
  border-left: 3px solid var(--accent);
}
h3 {
  font-size: 1.25rem; font-weight: 600;
  color: var(--accent);
  margin: 2rem 0 0.6rem 0;
  font-family: 'Space Grotesk', sans-serif;
}
p {
  color: var(--ink);
  margin: 0 0 1.1rem 0;
}
strong, b { color: #FFFFFF; font-weight: 600; }
a {
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px dashed rgba(34,211,238,0.4);
  transition: all 0.2s ease;
}
a:hover { color: #FFFFFF; border-bottom-color: var(--accent); }
ul, ol { padding-left: 1.4rem; }
li { margin-bottom: 0.4rem; }
li::marker { color: var(--accent); }
hr {
  border: none;
  height: 1px;
  background: var(--border);
  margin: 3rem 0;
}

/* CALLOUT — nota metodológica */
blockquote {
  margin: 1.5rem 0 2.5rem 0;
  padding: 1.4rem 1.6rem;
  background: linear-gradient(135deg, rgba(251,191,36,0.05) 0%, rgba(34,211,238,0.04) 100%);
  border: 1px solid var(--border);
  border-left: 4px solid var(--gold);
  border-radius: 8px;
  font-size: 0.95rem;
  color: var(--ink-soft);
}
blockquote strong { color: var(--gold); }
blockquote p { margin: 0; }

/* CODE */
pre {
  background: #0F172A;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.1rem 1.3rem;
  overflow-x: auto;
  font-size: 0.88rem;
  line-height: 1.55;
  margin: 1.4rem 0 2rem 0;
  position: relative;
}
pre::before {
  content: "";
  position: absolute; top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--accent) 0%, var(--emerald) 100%);
  border-top-left-radius: 10px; border-top-right-radius: 10px;
}
code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.88em;
  color: var(--ink);
}
p code, li code, td code {
  background: rgba(34,211,238,0.08);
  border: 1px solid rgba(34,211,238,0.18);
  padding: 0.08em 0.45em;
  border-radius: 5px;
  font-size: 0.85em;
  color: var(--accent);
}

/* MATH (MathJax) */
.math-display {
  display: block;
  margin: 1.6rem 0;
  padding: 1.1rem 1.3rem;
  background: rgba(15,23,42,0.55);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow-x: auto;
}
.math-inline {
  color: var(--ink);
}
mjx-container { color: var(--ink) !important; }
mjx-container[display="true"] {
  margin: 0 !important;
  padding: 0 !important;
}

/* TABLES */
table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 1.6rem 0 2rem 0;
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  font-size: 0.93rem;
}
th {
  background: rgba(34,211,238,0.07);
  color: var(--accent);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 0.85rem 1rem;
  text-align: left;
  border-bottom: 1px solid var(--border);
}
td {
  padding: 0.8rem 1rem;
  border-bottom: 1px solid var(--border);
  color: var(--ink);
}
tr:last-child td { border-bottom: none; }
tr:hover td { background: rgba(34,211,238,0.03); }

/* FIGURAS */
figure {
  margin: 2rem 0 2.6rem 0;
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}
figure img {
  display: block;
  width: 100%;
  height: auto;
  border-bottom: 1px solid var(--border);
}
figcaption {
  padding: 0.75rem 1rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  color: var(--ink-dim);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

/* FOOTER */
footer.article-footer {
  margin-top: 4rem;
  padding-top: 2rem;
  border-top: 1px solid var(--border);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.78rem;
  color: var(--ink-dim);
  letter-spacing: 0.05em;
}

/* NAV entre docs */
nav.docnav {
  margin-top: 1rem;
  display: flex; gap: 1.2rem; flex-wrap: wrap;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  letter-spacing: 0.12em;
}
nav.docnav a {
  color: var(--ink-dim);
  border: none;
  padding: 0.3rem 0.7rem;
  border-radius: 6px;
  background: rgba(255,255,255,0.03);
  transition: all 0.2s ease;
}
nav.docnav a:hover {
  color: var(--accent);
  background: rgba(34,211,238,0.08);
}

/* NAV alfabetica (glosario) */
nav.alphanav {
  position: sticky; top: 0;
  z-index: 10;
  display: flex; flex-wrap: wrap; gap: 0.4rem;
  padding: 0.8rem 1rem;
  margin: 0 0 2rem 0;
  background: rgba(17,24,39,0.88);
  backdrop-filter: blur(8px);
  border: 1px solid var(--border);
  border-radius: 10px;
  font-family: 'JetBrains Mono', monospace;
}
nav.alphanav a {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--ink-soft);
  padding: 0.25rem 0.55rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
}
nav.alphanav a:hover {
  color: var(--accent);
  border-color: var(--border-hot);
  background: rgba(34,211,238,0.08);
}
nav.alphanav a.muted {
  opacity: 0.3;
  pointer-events: none;
}

/* Glosario — mejor tipografía para h3 como términos */
body.glossary h3 {
  margin-top: 2.4rem;
  padding-top: 1.2rem;
  border-top: 1px solid var(--border);
}
body.glossary h3::before {
  content: "§ ";
  color: var(--ink-dim);
  font-weight: 400;
}
span.letter-anchor {
  display: block;
  height: 0;
  scroll-margin-top: 5rem; /* offset para la nav sticky */
}
"""


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">

<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/atom-one-dark.min.css">
<script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/highlight.min.js"></script>
<script>hljs.configure({{ignoreUnescapedHTML: true}}); document.addEventListener('DOMContentLoaded', () => hljs.highlightAll());</script>

<script>
window.MathJax = {{
  tex: {{
    inlineMath: [['\\\\(', '\\\\)']],
    displayMath: [['\\\\[', '\\\\]']],
    processEscapes: true
  }},
  chtml: {{
    displayAlign: 'left',
    scale: 1.05
  }}
}};
</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>

<style>
{css}
</style>
</head>
<body>
<main>
<header class="hero">
  <div class="eyebrow">{header_eyebrow}</div>
  <div class="meta">{header_meta} · {fecha}</div>
  <nav class="docnav">
    <a href="articulo_linkedin.html">// Artículo</a>
    <a href="guia_explicativa.html">// Guía</a>
    <a href="glosario.html">// Glosario</a>
  </nav>
</header>
{nav_block}
{content}
<footer class="article-footer">
  github.com/leanmasterpymes/energia_optima &nbsp;·&nbsp;
  PuLP + CBC · XGBoost · Streamlit · Python 3.12 &nbsp;·&nbsp;
  Manuel A. Pérez Ogando — MBA Tech
</footer>
</main>
</body>
</html>
"""


def insertar_figuras(html: str) -> str:
    """Inserta <figure><img></figure> despues del heading coincidente."""
    for match_text, img in INSERT_AFTER_HEADING.items():
        fig_path = FIG_DIR / img
        if not fig_path.exists():
            continue
        rel = f"../outputs/figures/{img}"
        figure = (
            f'<figure>'
            f'<img src="{rel}" alt="{img}" loading="lazy">'
            f'<figcaption>// {img.replace("_", " ").replace(".png", "")}</figcaption>'
            f'</figure>'
        )
        # Busca el heading h2/h3 que contiene match_text y pega la figura despues.
        pattern = re.compile(
            rf'(<h[23][^>]*>[^<]*{re.escape(match_text)}[^<]*</h[23]>)'
        )
        html, n = pattern.subn(rf'\1\n{figure}', html, count=1)
        if n == 0:
            # fallback: buscar ignorando acentos/case
            pattern_ci = re.compile(
                rf'(<h[23][^>]*>[^<]*{re.escape(match_text)}[^<]*</h[23]>)',
                re.IGNORECASE,
            )
            html = pattern_ci.sub(rf'\1\n{figure}', html, count=1)
    return html


def preparar_math(md_text: str) -> tuple[str, dict[str, str]]:
    """Enmascara math blocks antes de markdown para que no sean tocados.

    Devuelve (texto_con_placeholders, mapping_placeholder_a_html_final).
    El HTML final usa \\(...\\) y \\[...\\] para MathJax.
    """
    mapping: dict[str, str] = {}
    counter = [0]

    def _token(html_math: str) -> str:
        key = f"MATHTOKEN{counter[0]:04d}"
        counter[0] += 1
        mapping[key] = html_math
        return key

    # 1) Proteger bloques fenced y codigo inline.
    code_blocks: list[str] = []

    def _proteger_codigo(m: re.Match) -> str:
        code_blocks.append(m.group(0))
        return f"\x00CB{len(code_blocks)-1}\x00"

    md_text = re.sub(r"```.*?```", _proteger_codigo, md_text, flags=re.DOTALL)
    md_text = re.sub(r"`[^`\n]+`", _proteger_codigo, md_text)

    # 2) Display math $$...$$ -> placeholder -> <span class="math-display">\[...\]</span>
    # (span, no div, para que pueda vivir dentro de <p> sin romper HTML.)
    def _display(m: re.Match) -> str:
        html = f'<span class="math-display">\\[{m.group(1).strip()}\\]</span>'
        return _token(html)

    md_text = re.sub(r"\$\$(.+?)\$\$", _display, md_text, flags=re.DOTALL)

    # 3) Inline math $...$: solo si NO es moneda.
    def _inline(m: re.Match) -> str:
        before, content = m.group(1), m.group(2)
        es_math = bool(re.search(r"[\\_^{}]", content))
        es_var = bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", content))
        if not (es_math or es_var):
            return m.group(0)
        html = f'<span class="math-inline">\\({content}\\)</span>'
        return f"{before}{_token(html)}"

    md_text = re.sub(
        r"(^|[\s(\[{,;:])\$([^\$\n]+?)\$(?=[\s.,;:!?\])}]|$)",
        _inline,
        md_text,
        flags=re.MULTILINE,
    )

    # 4) Restaurar code blocks.
    for i, cb in enumerate(code_blocks):
        md_text = md_text.replace(f"\x00CB{i}\x00", cb)

    return md_text, mapping


def rehidratar_math(html: str, mapping: dict[str, str]) -> str:
    for key, value in mapping.items():
        html = html.replace(key, value)
    return html


def insertar_figuras_en(html: str, mapping: dict[str, str]) -> str:
    """Versión generica de insertar_figuras usando un mapping local."""
    for match_text, img in mapping.items():
        fig_path = FIG_DIR / img
        if not fig_path.exists():
            continue
        rel = f"../outputs/figures/{img}"
        figure = (
            f'<figure>'
            f'<img src="{rel}" alt="{img}" loading="lazy">'
            f'<figcaption>// {img.replace("_", " ").replace(".png", "")}</figcaption>'
            f'</figure>'
        )
        pattern = re.compile(
            rf'(<h[23][^>]*>[^<]*{re.escape(match_text)}[^<]*</h[23]>)'
        )
        html, n = pattern.subn(rf'\1\n{figure}', html, count=1)
        if n == 0:
            pattern_ci = re.compile(
                rf'(<h[23][^>]*>[^<]*{re.escape(match_text)}[^<]*</h[23]>)',
                re.IGNORECASE,
            )
            html = pattern_ci.sub(rf'\1\n{figure}', html, count=1)
    return html


def construir_nav_alfabetica(html: str) -> tuple[str, str]:
    """Devuelve (nav_html, html_modificado).

    Inserta un <span id="letra-X"></span> ANCHOR antes del primer h3 de cada
    letra (no toca los slugs originales) y construye la nav A–Z.
    """
    import unicodedata

    def _inicial(texto: str) -> str:
        nfkd = unicodedata.normalize("NFKD", texto)
        stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
        for c in stripped.upper():
            if c.isalpha():
                return c
        return "#"

    h3_pattern = re.compile(r'<h3([^>]*)>(.*?)</h3>', re.DOTALL)
    letras_vistas: set[str] = set()

    def _anclar(m: re.Match) -> str:
        attrs = m.group(1)
        texto = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        letra = _inicial(texto)
        h3 = f'<h3{attrs}>{m.group(2)}</h3>'
        if letra not in letras_vistas:
            letras_vistas.add(letra)
            return f'<span id="letra-{letra}" class="letter-anchor"></span>\n{h3}'
        return h3

    html = h3_pattern.sub(_anclar, html)

    letras = [chr(ord("A") + i) for i in range(26)]
    items = []
    for letra in letras:
        if letra in letras_vistas:
            items.append(f'<a href="#letra-{letra}">{letra}</a>')
        else:
            items.append(f'<a class="muted">{letra}</a>')
    nav = '<nav class="alphanav">' + "".join(items) + '</nav>'
    return nav, html


def render_doc(spec: DocSpec) -> None:
    md_text = spec.md_path.read_text(encoding="utf-8")
    md_text, math_map = preparar_math(md_text)

    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "attr_list", "toc"],
    )
    content_html = md.convert(md_text)
    content_html = rehidratar_math(content_html, math_map)

    nav_block = ""
    body_class = ""
    if spec.insert_figures:
        content_html = insertar_figuras_en(content_html, spec.insert_figures)
    if spec.add_nav:
        nav_block, content_html = construir_nav_alfabetica(content_html)
        body_class = "glossary"

    from datetime import datetime
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = HTML_TEMPLATE.format(
        css=CSS,
        page_title=spec.page_title,
        header_eyebrow=spec.header_eyebrow,
        header_meta=spec.header_meta,
        nav_block=nav_block,
        content=content_html,
        fecha=fecha,
    )
    # Body class solo para glosario
    if body_class:
        html = html.replace("<body>", f'<body class="{body_class}">')

    spec.html_path.write_text(html, encoding="utf-8")
    print(f"✓ Rendered {spec.html_path.relative_to(ROOT)}")


def render_all() -> None:
    for spec in DOCS:
        if spec.md_path.exists():
            render_doc(spec)
        else:
            print(f"⚠ Skipping {spec.md_path.name} (not found)")


if __name__ == "__main__":
    render_all()
