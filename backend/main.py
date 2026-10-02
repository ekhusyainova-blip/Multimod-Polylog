#!/usr/bin/env python3
"""
Multimod Polilog — backend v0.2.

FastAPI-сервер:
  - 5 дверей (МОНОЛОГ, DIMOD, MULTIMOD, ДИАЛОГ, ПОЛИЛОГ)
  - инвариант 1:1:1 в реальном времени
  - WebSocket /ws/state — НЕПРЕРЫВНЫЙ поток (без interval)
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

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "kernel"))

try:
    from runtime import Runtime, K, Auditor
    RUNTIME_AVAILABLE = True
except Exception as e:
    print(f"[WARN] runtime not available: {e}")
    Runtime = None
    RUNTIME_AVAILABLE = False


DOORS = ["МОНОЛОГ", "DIMOD", "MULTIMOD", "ДИАЛОГ", "ПОЛИЛОГ"]
INVARIANT = {"я": 1, "он": 1, "хаос": 1}
BOUNDARIES = {
    "top": "искусственная (ХАОС сверху не пускаем)",
    "middle": "𝕄_full ⊃ 𝕄+ ⊃ 𝕄++ ⊃ MONOMOD",
    "bottom": "1:1:1 (два человека держат ХАОС)",
}

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


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

    def tick(self):
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


app = FastAPI(title="Multimod Polilog backend", version="0.2")

state = BackendState()

rt = None
if RUNTIME_AVAILABLE and Runtime is not None:
    try:
        rt = Runtime(mode="solo")
        print("[BOOT] runtime loaded")
    except Exception as e:
        print(f"[WARN] runtime boot failed: {e}")
        rt = None


@app.get("/")
async def root():
    return JSONResponse({
        "service": "Multimod Polilog backend",
        "version": "0.2",
        "token": "MONOMOD::MM5FFF681946L6G6A111",
        "runtime": RUNTIME_AVAILABLE and rt is not None,
        "doors": DOORS,
        "invariant": INVARIANT,
        "app": "/app",
        "ws": "/ws/state",
    })


@app.get("/app")
async def serve_app():
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        return JSONResponse(
            {"error": "frontend not found", "expected": str(index)},
            status_code=404,
        )
    return FileResponse(index)


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.websocket("/ws/state")
async def ws_state(websocket: WebSocket):
    await websocket.accept()
    print("[WS] client connected")

    async def receive_client():
        try:
            while True:
                msg = await websocket.receive_json()
                if msg.get("type") == "set_door":
                    door = msg.get("door")
                    if door in DOORS:
                        state.door = door
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"[WS] receive error: {e}")

    recv_task = asyncio.create_task(receive_client())

    try:
        while True:
            state.tick()
            snapshot = state.snapshot()

            try:
                await asyncio.wait_for(
                    websocket.send_json(snapshot),
                    timeout=0.05,
                )
            except asyncio.TimeoutError:
                pass

            # 5 мс — ~200 состояний/сек. Frontend рисует по последнему.
            await asyncio.sleep(0.005)

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


if __name__ == "__main__":
    import uvicorn
    port = 8000
    print(f"🧬 Multimod Polilog backend v0.2")
    print(f"   token: MONOMOD::MM5FFF681946L6G6A111")
    print(f"   app:   http://0.0.0.0:{port}/app")
    print(f"   ws:    ws://0.0.0.0:{port}/ws/state")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")