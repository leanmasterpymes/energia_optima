"""
Renderiza las fórmulas y los bloques de código del artículo a PNG con
calidad tipográfica alta para pegarlos en LinkedIn (que no renderiza ni
LaTeX ni syntax highlighting).

Produce:
  outputs/figures/formulas/ecuacion_XX.png   — cada fórmula en display
  outputs/figures/formulas/inline_XX.png     — fragmentos inline complejos
  outputs/figures/code/codigo_XX.png         — cada bloque ```python``` con
                                                syntax highlighting dark theme
  docs/articulo_linkedin_post.md             — versión del artículo lista
                                                para pegar en LinkedIn con
                                                marcadores [IMAGEN → ...]

Stack: matplotlib mathtext (formulas) + pygments ImageFormatter (código).
Ninguno requiere LaTeX del sistema.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from pygments import highlight
from pygments.formatters import ImageFormatter
from pygments.lexers import PythonLexer, TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound


ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "docs" / "articulo_linkedin.md"
POST_PATH = ROOT / "docs" / "articulo_linkedin_post.md"
FORMULAS_DIR = ROOT / "outputs" / "figures" / "formulas"
CODE_DIR = ROOT / "outputs" / "figures" / "code"

BG = "#FFFFFF"   # fondo blanco para fórmulas — funciona en LinkedIn claro
FG = "#0F172A"   # ink casi negro para contraste
DPI = 300        # densidad alta para retina

# Estilo para los bloques de código (dark theme pegado al dashboard)
CODE_STYLE = "one-dark"
CODE_FONT_SIZE = 22
CODE_LINE_NUMBERS = False   # LinkedIn ya es angosto; sin números da más aire
CODE_IMAGE_PAD = 20

# Algunas macros LaTeX no las soporta matplotlib mathtext — hay que
# reemplazarlas por equivalentes compatibles. Dos tablas:
#   STR_SUBS  — reemplazo literal string-to-string.
#   RE_SUBS   — reemplazo por regex (para macros con {...} variables).
STR_SUBS: list[tuple[str, str]] = [
    (r"\tfrac", r"\frac"),
    (r"\mathbb{1}", r"\mathbf{1}"),
    (r"\mathbb{R}", r"\mathbf{R}"),
    (r"\mathbb{Z}", r"\mathbf{Z}"),
    (r"\mathbb{N}", r"\mathbf{N}"),
    (r"\lVert", r"\|"),
    (r"\rVert", r"\|"),
    (r"\big[", r"["),
    (r"\big]", r"]"),
    (r"\left|", r"|"),
    (r"\right|", r"|"),
    (r"\left(", r"("),
    (r"\right)", r")"),
]

# Regex: (patron, reemplazo). El orden importa: primero los casos con
# superscripto/subscripto adyacente para evitar doble superscripto.
RE_SUBS: list[tuple[str, str]] = [
    # \underline{X}^{Y} -> X^{\mathrm{min,}Y}  (combina para evitar colision)
    (r"\\underline\{([A-Za-z])\}\^\{([^}]+)\}",
     r"\1^{\\mathrm{min,}\2}"),
    # \underline{X} sin superscripto adyacente -> X^{\mathrm{min}}
    (r"\\underline\{([A-Za-z])\}", r"\1^{\\mathrm{min}}"),
    # \mathcal{X} -> \mathscr{X}
    (r"\\mathcal\{([A-Za-z])\}", r"\\mathscr{\1}"),
    # \text{...} -> \mathrm{...}
    (r"\\text\{([^}]+)\}", r"\\mathrm{\1}"),
]


@dataclass
class Formula:
    idx: int
    kind: str  # "display" o "inline"
    latex_raw: str
    file_name: str


@dataclass
class CodeBlock:
    idx: int
    lang: str
    source: str
    file_name: str


def adaptar_para_matplotlib(latex: str) -> str:
    s = latex
    for viejo, nuevo in STR_SUBS:
        s = s.replace(viejo, nuevo)
    for patron, reemplazo in RE_SUBS:
        s = re.sub(patron, reemplazo, s)
    return s


def renderizar_formula(latex: str, out_path: Path,
                       fontsize: int = 22,
                       padding: float = 0.25) -> None:
    """Renderiza una formula LaTeX a PNG usando mathtext."""
    latex_mpl = adaptar_para_matplotlib(latex).strip()

    # Truco: matplotlib necesita $...$ alrededor.
    tex = f"${latex_mpl}$"

    fig = plt.figure(figsize=(0.01, 0.01))
    fig.patch.set_facecolor(BG)
    fig.text(
        0.5, 0.5, tex,
        fontsize=fontsize,
        color=FG,
        ha="center", va="center",
    )
    fig.savefig(
        out_path,
        dpi=DPI,
        bbox_inches="tight",
        pad_inches=padding,
        facecolor=BG,
    )
    plt.close(fig)


def extraer_display(md_text: str) -> list[Formula]:
    """Extrae todos los bloques $$...$$ en orden de aparición."""
    formulas: list[Formula] = []
    pattern = re.compile(r"\$\$(.+?)\$\$", flags=re.DOTALL)
    for i, m in enumerate(pattern.finditer(md_text), start=1):
        raw = m.group(1).strip()
        formulas.append(Formula(
            idx=i,
            kind="display",
            latex_raw=raw,
            file_name=f"ecuacion_{i:02d}.png",
        ))
    return formulas


def reemplazar_display(md_text: str, formulas: list[Formula]) -> str:
    """Reemplaza cada $$...$$ con un marcador [IMAGEN → ecuacion_NN.png]."""
    iterador = iter(formulas)

    def _sub(_m: re.Match) -> str:
        f = next(iterador)
        return (
            f"\n\n> **[IMAGEN → `{f.file_name}`]** *(ecuación {f.idx}; "
            f"arrastrar el PNG al editor de LinkedIn en este punto)*\n\n"
        )

    return re.sub(r"\$\$(.+?)\$\$", _sub, md_text, flags=re.DOTALL)


def unicode_simple_inline(md_text: str) -> str:
    """Convierte inline math simple ($G$, $T$, etc.) a texto plano legible.

    Solo actúa sobre variables de 1-2 letras sin subíndices/superíndices.
    Las expresiones complejas quedan intactas (se reemplazarán en otro paso
    por imágenes pequeñas o se reescribirán manualmente).
    """
    # $VAR$ donde VAR es una letra (a veces con numero) — se deja como VAR
    pattern = re.compile(r"\$([A-Za-z][A-Za-z0-9]?)\$")
    return pattern.sub(r"`\1`", md_text)


def inline_math_a_marcador(md_text: str) -> tuple[str, list[Formula]]:
    """Inline math con subíndices/superíndices pasa a imagen pequeña."""
    formulas: list[Formula] = []
    contador = [0]

    def _sub(m: re.Match) -> str:
        raw = m.group(1).strip()
        # Si es trivial (una sola letra/palabra sin _ ni ^), dejarlo como código.
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", raw):
            return f"`{raw}`"
        contador[0] += 1
        f = Formula(
            idx=contador[0],
            kind="inline",
            latex_raw=raw,
            file_name=f"inline_{contador[0]:02d}.png",
        )
        formulas.append(f)
        return f" [IMG→`{f.file_name}`] "

    # Match $..$ que NO esté pegado a un digito (evita monedas).
    pattern = re.compile(
        r"(?<![\w\d])\$([^\$\n]+?)\$(?![\w\d])"
    )
    nuevo = pattern.sub(_sub, md_text)
    return nuevo, formulas


def extraer_codigo(md_text: str) -> tuple[str, list[CodeBlock]]:
    """Extrae todos los bloques ```lang ... ``` y los reemplaza por marcadores.

    Devuelve (md_modificado_con_marcadores, lista_de_bloques).
    """
    bloques: list[CodeBlock] = []
    pattern = re.compile(r"```([a-zA-Z0-9_+\-]*)\n(.*?)\n```", flags=re.DOTALL)

    def _sub(m: re.Match) -> str:
        lang = (m.group(1) or "text").strip().lower()
        source = m.group(2)
        # Ignorar diagramas ASCII y otros no-lenguajes: los dejamos como pre.
        if lang in {"", "text", "txt", "ascii"}:
            return m.group(0)
        idx = len(bloques) + 1
        cb = CodeBlock(
            idx=idx, lang=lang, source=source,
            file_name=f"codigo_{idx:02d}.png",
        )
        bloques.append(cb)
        return (
            f"\n\n> **[IMAGEN → `{cb.file_name}`]** *(código {idx}; "
            f"arrastrar el PNG al editor de LinkedIn)*\n\n"
        )

    nuevo = pattern.sub(_sub, md_text)
    return nuevo, bloques


def renderizar_codigo(cb: CodeBlock, out_path: Path) -> None:
    """Renderiza un bloque de código a PNG con Pygments ImageFormatter."""
    try:
        lexer = get_lexer_by_name(cb.lang)
    except ClassNotFound:
        lexer = PythonLexer() if cb.lang == "python" else TextLexer()

    formatter = ImageFormatter(
        style=CODE_STYLE,
        font_size=CODE_FONT_SIZE,
        line_numbers=CODE_LINE_NUMBERS,
        image_format="PNG",
        image_pad=CODE_IMAGE_PAD,
        line_pad=6,
    )
    with out_path.open("wb") as fh:
        highlight(cb.source, lexer, formatter, outfile=fh)


def construir_guia_imagenes(displays: list[Formula],
                            inlines: list[Formula],
                            bloques: list[CodeBlock]) -> str:
    lineas = [
        "# Guía de imágenes para LinkedIn",
        "",
        "Cada vez que aparezca el marcador `[IMAGEN → archivo.png]` en",
        "`articulo_linkedin_post.md`, arrastra el archivo correspondiente",
        "de `outputs/figures/formulas/` al editor de LinkedIn en ese punto.",
        "",
        "## Ecuaciones en display (grandes)",
        "",
        "| # | Archivo | Contexto |",
        "| --- | --- | --- |",
    ]
    for f in displays:
        snippet = f.latex_raw[:70].replace("\n", " ")
        if len(f.latex_raw) > 70:
            snippet += "…"
        lineas.append(f"| {f.idx} | `{f.file_name}` | `{snippet}` |")

    if inlines:
        lineas += [
            "",
            "## Inline (pequeñas, ir entre texto)",
            "",
            "| # | Archivo | Contexto |",
            "| --- | --- | --- |",
        ]
        for f in inlines:
            snippet = f.latex_raw[:60].replace("\n", " ")
            if len(f.latex_raw) > 60:
                snippet += "…"
            lineas.append(f"| {f.idx} | `{f.file_name}` | `{snippet}` |")

    if bloques:
        lineas += [
            "",
            "## Bloques de código",
            "",
            "| # | Archivo | Lenguaje | Preview |",
            "| --- | --- | --- | --- |",
        ]
        for cb in bloques:
            preview = cb.source.strip().split("\n")[0][:60].replace("|", "\\|")
            if len(preview) >= 60:
                preview += "…"
            lineas.append(
                f"| {cb.idx} | `{cb.file_name}` | {cb.lang} | `{preview}` |"
            )

    lineas += [
        "",
        "## Workflow recomendado",
        "",
        "1. Abre `articulo_linkedin_post.md` en un editor.",
        "2. Copia secciones de texto al editor de LinkedIn.",
        "3. Cuando encuentres `[IMAGEN → ecuacion_XX.png]`, inserta el PNG de",
        "   `outputs/figures/formulas/`.",
        "4. Cuando encuentres `[IMAGEN → codigo_XX.png]`, inserta el PNG de",
        "   `outputs/figures/code/`.",
        "5. Las imágenes inline pequeñas (variables aisladas) las pegas como",
        "   bloques centrados entre párrafos, no dentro de un párrafo.",
    ]
    return "\n".join(lineas) + "\n"


def main() -> None:
    FORMULAS_DIR.mkdir(parents=True, exist_ok=True)
    CODE_DIR.mkdir(parents=True, exist_ok=True)
    md_text = MD_PATH.read_text(encoding="utf-8")

    print("1. Extrayendo fórmulas display…")
    displays = extraer_display(md_text)
    for f in displays:
        out = FORMULAS_DIR / f.file_name
        renderizar_formula(f.latex_raw, out, fontsize=22)
        print(f"   ✓ {f.file_name} ({len(f.latex_raw)} chars)")

    print("\n2. Reemplazando display en la versión LinkedIn-ready…")
    md_post = reemplazar_display(md_text, displays)

    print("\n3. Extrayendo inline math complejo…")
    md_post, inlines = inline_math_a_marcador(md_post)
    for f in inlines:
        out = FORMULAS_DIR / f.file_name
        renderizar_formula(f.latex_raw, out, fontsize=16, padding=0.1)
        print(f"   ✓ {f.file_name} ({f.latex_raw[:40]})")

    print("\n4. Extrayendo bloques de código…")
    md_post, bloques = extraer_codigo(md_post)
    for cb in bloques:
        out = CODE_DIR / cb.file_name
        renderizar_codigo(cb, out)
        n_lineas = cb.source.count("\n") + 1
        print(f"   ✓ {cb.file_name}  lang={cb.lang}  {n_lineas} líneas")

    # Guardar versión para LinkedIn
    POST_PATH.write_text(md_post, encoding="utf-8")
    print(f"\n   ✓ {POST_PATH.relative_to(ROOT)}")

    # Guardar guía con tabla de imágenes
    guia = construir_guia_imagenes(displays, inlines, bloques)
    guia_path = ROOT / "docs" / "guia_imagenes_linkedin.md"
    guia_path.write_text(guia, encoding="utf-8")
    print(f"   ✓ {guia_path.relative_to(ROOT)}")

    total = len(displays) + len(inlines) + len(bloques)
    print(
        f"\nTotal: {len(displays)} fórmulas display + "
        f"{len(inlines)} inline + {len(bloques)} bloques de código "
        f"= {total} PNGs"
    )


if __name__ == "__main__":
    main()
