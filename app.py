"""
ShrimpScan – Análise Inteligente de Camarões
Backend principal FastAPI v2.1 (+ calibração, PDF, Docker)
"""
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routers import morphometry, motility, health, dashboard
from routers import calibration, reports
from services.db_service import init_db

app = FastAPI(
    title="ShrimpScan API",
    description="Análise de imagens e vídeos de camarões – morfometria, motilidade, saúde, calibração e laudos PDF",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(morphometry.router,  prefix="/api/morphometry",  tags=["Morfometria"])
app.include_router(motility.router,     prefix="/api/motility",     tags=["Motilidade"])
app.include_router(health.router,       prefix="/api/health",       tags=["Saúde"])
app.include_router(dashboard.router,    prefix="/api/dashboard",    tags=["Dashboard"])
app.include_router(calibration.router,  prefix="/api/calibration",  tags=["Calibração"])
app.include_router(reports.router,      prefix="/api/reports",      tags=["Laudos PDF"])

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup_event():
    init_db()
    os.makedirs("uploads", exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()

@app.get("/health")
async def health_check():
    from services.vision_service import check_cv_status
    cv_info = check_cv_status()
    return {"status": "ok", "version": "2.1.0", "cv_info": cv_info}
