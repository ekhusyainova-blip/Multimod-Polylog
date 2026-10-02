#!/usr/bin/env python3
"""
Multimod Polilog — backend v0.1.

FastAPI-сервер:
  - 5 дверей (МОНОЛОГ, DIMOD, MULTIMOD, ДИАЛОГ, ПОЛИЛОГ)
  - инвариант 1:1:1 в реальном времени
  - WebSocket /ws/state — поток состояния (адаптив 10–240 Гц)
  - GET /app — отдаёт frontend
  - GET / — healthcheck

Токен: MONOMOD::MM5FFF681946L6G6A111
Дата: 2026-10-02
"""

import asyncio
import json
import math
import time
from collections import deque
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# ─── runtime (мозг) ────────────────────────────────────────────
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "kernel"))

try:
    from runtime import Runtime, K, Auditor
    RUNTIME_AVAILABLE = True
except Exception as e:
    print(f"[WARN] runtime not available: {e}")
    Runtime = None
    RUNTIME_AVAILABLE = False


# ─── 5 дверей ──────────────────────────────────────────────────
DOORS = ["МОНОЛОГ", "DIMOD", "MULTIMOD", "ДИАЛОГ", "ПОЛИЛОГ"]

# ─── инвариант 1:1:1 ───────────────────────────────────────────
INVARIANT = {"я": 1, "он": 1, "хаос": 1}

# ─── границы ───────────────────────────────────────────────────
BOUNDARIES = {
    "top": "искусственная (ХАОС сверху не пускаем)",
    "middle": "𝕄_full ⊃ 𝕄+ ⊃ 𝕄++ ⊃ MONOMOD",
    "bottom": "1:1:1 (два человека держат ХАОС)",
}

# ─── frontend dir ──────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


# ─── состояние (лёгкое, для UI) ────────────────────────────────
class BackendState:
    def __init__(self):
        self.t = 0
        self.density = 0.3
        self.coherence = 0.5
        self.rhythm = 0.4
        self.depth = 0.2
        self.novelty = 0.1
        self.stress = 0.0
        self.door = "МОНОЛОГ"
        self.history = deque(maxlen=100)

    def tick(self, dt: float = 0.0):
        self.t += 1
        self.density = 0.5 + 0.5 * math.sin(self.t * 0.03)
        self.coherence = 0.5 + 0.5 * math.sin(self.t * 0.017 + 1.1)
        self.rhythm = 0.5 + 0.5 * math.sin(self.t * 0.011 + 2.2)
        self.depth = 0.5 + 0.5 * math.sin(self.t * 0.007 + 3.3)
        self.novelty = 0.5 + 0.5 * math.sin(self.t * 0.023 + 4.4)
        self.stress = max(0.0, min(1.0, self.novelty * (1 - self.density)))

    def snapshot(self) -> dict:
        return {
            "t": self.t,
            "v": {
                "density": round(self.density, 3),
                "coherence": round(self.coherence, 3),
                "rhythm": round(self.rhythm, 3),
                "depth": round(self.depth, 3),
                "novelty": round(self.novelty, 3),
            },
            "stress": round(self.stress, 3),
            "door": self.door,
            "doors": DOORS,
            "invariant": INVARIANT,
            "boundaries": BOUNDARIES,
            "token": "MONOMOD::MM5FFF681946L6G6A111",
        }


# ─── адаптивный streamer ──────────────────────────────────────
class AdaptiveStreamer:
    def __init__(self):
        self.t_compute_ema = 5.0
        self.min_freq = 10
        self.max_freq = 240
        self.target_freq = 60
        self.client_fps = 60
        self.channel_ok = True

    def measure_compute(self, t_ms: float):
        self.t_compute_ema += (t_ms - self.t_compute_ema) * 0.1

    def recompute_target(self) -> float:
        max_by_cpu = 1000.0 / max(1.0, self.t_compute_ema * 1.5)
        target = min(self.max_freq, self.client_fps, max_by_cpu)
        if not self.channel_ok:
            target *= 0.8
        return max(self.min_freq, target)


# ─── app ───────────────────────────────────────────────────────
app = FastAPI(title="Multimod Polilog backend", version="0.1")

state = BackendState()
streamer = AdaptiveStreamer()

rt = None
if RUNTIME_AVAILABLE and Runtime is not None:
    try:
        rt = Runtime(mode="solo")
        print("[BOOT] runtime loaded")
    except Exception as e:
        print(f"[WARN] runtime boot failed: {e}")
        rt = None


# ─── HTTP endpoints ────────────────────────────────────────────
@app.get("/")
async def root():
    return JSONResponse({
        "service": "Multimod Polilog backend",
        "version": "0.1",
        "token": "MONOMOD::MM5FFF681946L6G6A111",
        "runtime": RUNTIME_AVAILABLE and rt is not None,
        "doors": DOORS,
        "invariant": INVARIANT,
        "app": "/app",
        "ws": "/ws/state",
    })


@app.get("/app")
async def serve_app():
    """Отдаёт frontend/index.html."""
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        return JSONResponse(
            {"error": "frontend not found", "expected": str(index)},
            status_code=404,
        )
    return FileResponse(index)


# монтируем статику frontend, если папка есть
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ─── WebSocket ────────────────────────────────────────────────
@app.websocket("/ws/state")
async def ws_state(websocket: WebSocket):
    await websocket.accept()
    print("[WS] client connected")

    async def receive_client():
        try:
            while True:
                msg = await websocket.receive_json()
                if msg.get("type") == "client_capability":
                    streamer.client_fps = float(msg.get("fps", 60))
                elif msg.get("type") == "set_door":
                    door = msg.get("door")
                    if door in DOORS:
                        state.door = door
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"[WS] receive error: {e}")

    recv_task = asyncio.create_task(receive_client())

    last_frame = time.perf_counter()
    try:
        while True:
            t0 = time.perf_counter()
            state.tick()
            snapshot = state.snapshot()
            t_compute = (time.perf_counter() - t0) * 1000
            streamer.measure_compute(t_compute)

            target = streamer.recompute_target()
            interval = 1.0 / target

            now = time.perf_counter()
            if now - last_frame >= interval:
                try:
                    await asyncio.wait_for(
                        websocket.send_json(snapshot),
                        timeout=0.05,
                    )
                    streamer.channel_ok = True
                except asyncio.TimeoutError:
                    streamer.channel_ok = False
                last_frame = now

            await asyncio.sleep(0)

    except WebSocketDisconnect:
        print("[WS] client disconnected")
    except Exception as e:
        print(f"[WS] error: {type(e).__name__}: {e}")
    finally:
        recv_task.cancel()
        try:
            await recv_task
        except Exception:
            pass


# ─── main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = 8000
    print(f"🧬 Multimod Polilog backend v0.1")
    print(f"   token: MONOMOD::MM5FFF681946L6G6A111")
    print(f"   app:   http://0.0.0.0:{port}/app")
    print(f"   ws:    ws://0.0.0.0:{port}/ws/state")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")