import logging
import logging.config
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import Base, engine

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización y limpieza de la aplicación."""
    logger.info("Iniciando Hyperred FA Sandbox...")
    # Crear tablas si no existen (en producción usaríamos solo alembic)
    Base.metadata.create_all(bind=engine)

    # Ejecutar seed si la BD está vacía
    from app.database import SessionLocal
    from app.seed.seed_data import run_seed
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()

    logger.info("Hyperred FA Sandbox listo en http://localhost:8000")
    yield
    logger.info("Cerrando Hyperred FA Sandbox.")


app = FastAPI(
    title=settings.app_name,
    description="Simulador de Tarificación Dinámica Híbrida para Flecha Amarilla",
    version="0.1.0",
    lifespan=lifespan,
)

# Archivos estáticos
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

# Templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# ── Routers ──────────────────────────────────────────────────────────────────
from app.api.routes import (  # noqa: E402
    boletos,
    comparador,
    export,
    presentacion,
    rutas,
    simulador,
    viajes,
)

app.include_router(rutas.router, prefix="/api/rutas", tags=["rutas"])
app.include_router(viajes.router, prefix="/api/viajes", tags=["viajes"])
app.include_router(boletos.router, prefix="/api/boletos", tags=["boletos"])
app.include_router(simulador.router, prefix="/api/simulador", tags=["simulador"])
app.include_router(comparador.router, prefix="/api/comparador", tags=["comparador"])
app.include_router(export.router, prefix="/api/export", tags=["exportación"])
# Alias sin prefijo /api para compatibilidad con acceso directo
app.include_router(export.router, prefix="/export", tags=["exportación-alias"], include_in_schema=False)

# Rutas de páginas (devuelven HTML)
app.include_router(presentacion.router, tags=["páginas"])


# ── Páginas principales ────────────────────────────────────────────────────
@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/simulador", response_class=HTMLResponse)
async def simulador_page(request: Request):
    return templates.TemplateResponse(request, "simulador.html")


@app.get("/comparador", response_class=HTMLResponse)
async def comparador_page(request: Request):
    return templates.TemplateResponse(request, "comparador.html")


@app.get("/escenarios", response_class=HTMLResponse)
async def escenarios_page(request: Request):
    return templates.TemplateResponse(request, "escenarios.html")


@app.get("/presentacion", response_class=HTMLResponse)
async def presentacion_page(request: Request):
    return templates.TemplateResponse(request, "presentacion.html")


# ── Health check ──────────────────────────────────────────────────────────
@app.get("/health", tags=["sistema"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "version": "0.1.0",
    }


# ── Favicon ────────────────────────────────────────────────────────────────
from fastapi.responses import FileResponse  # noqa: E402


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    p = Path(__file__).parent / "static" / "img" / "favicon.svg"
    return FileResponse(str(p), media_type="image/svg+xml")


# ── Error handlers ─────────────────────────────────────────────────────────
from starlette.requests import Request as StarletteRequest  # noqa: E402
from starlette.responses import JSONResponse  # noqa: E402

# Únicas rutas que devuelven HTML — todo lo demás debe devolver JSON en errores
_HTML_PAGES = {"/", "/dashboard", "/simulador", "/comparador", "/escenarios", "/presentacion"}


def _is_html_page(path: str) -> bool:
    return path in _HTML_PAGES or path.startswith("/static/")


@app.exception_handler(404)
async def not_found_handler(request: StarletteRequest, exc):
    if _is_html_page(request.url.path):
        return templates.TemplateResponse(request, "404.html", status_code=404)
    return JSONResponse({"detail": "Recurso no encontrado"}, status_code=404)


@app.exception_handler(500)
async def server_error_handler(request: StarletteRequest, exc):
    if _is_html_page(request.url.path):
        return templates.TemplateResponse(request, "500.html", status_code=500)
    return JSONResponse({"detail": "Error interno del servidor"}, status_code=500)
