# ─── serve frontend ────────────────────────────────────────────
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

@app.get("/app")
async def serve_app():
    """Отдаёт index.html."""
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        return JSONResponse(
            {"error": "frontend not found", "expected": str(index)},
            status_code=404,
        )
    return FileResponse(index)

# монтируем статику frontend (если папка существует)
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")