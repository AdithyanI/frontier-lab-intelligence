"""FastAPI app — server-rendered UI per DESIGN.md.

First surface: /architecture renders docs/architecture/overview.md with
Mermaid diagrams, so the living map is viewable in the product itself.
"""

from pathlib import Path

import markdown
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

REPO_ROOT = Path(__file__).resolve().parents[3]
ARCHITECTURE_DOC = REPO_ROOT / "docs" / "architecture" / "overview.md"

_WEB_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=_WEB_DIR / "templates")

app = FastAPI(title="Frontier Lab Intelligence")
app.mount("/static", StaticFiles(directory=_WEB_DIR / "static"), name="static")


def render_markdown(text: str) -> str:
    """Markdown → HTML, turning ```mermaid fences into <pre class="mermaid">."""
    return markdown.markdown(
        text,
        extensions=["tables", "fenced_code"],
        extension_configs={},
        output_format="html",
    ).replace(
        '<pre><code class="language-mermaid">', '<pre class="mermaid"><code>'
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "home.html", {"title": "Frontier Lab Intelligence"}
    )


@app.get("/architecture", response_class=HTMLResponse)
def architecture(request: Request) -> HTMLResponse:
    body = render_markdown(ARCHITECTURE_DOC.read_text(encoding="utf-8"))
    return templates.TemplateResponse(
        request,
        "architecture.html",
        {"title": "Architecture", "body": body},
    )
