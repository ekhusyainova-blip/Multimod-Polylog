#!/usr/bin/env python3
"""
Multimod Polilog — backend v0.3.

FastAPI-сервер:
  - 5 дверей (МОНОЛОГ, DIMOD, MULTIMOD, ДИАЛОГ, ПОЛИЛОГ)
  - инвариант 1:1:1 в реальном времени
  - WebSocket /ws/state — непрерывный поток
  - GET /app — генерирует HTML на лету (no-cache)
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
from fastapi.responses import HTMLResponse, JSONResponse

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


app = FastAPI(title="Multimod Polilog backend", version="0.3")

state = BackendState()

rt = None
if RUNTIME_AVAILABLE and Runtime is not None:
    try:
        rt = Runtime(mode="solo")
        print("[BOOT] runtime loaded")
    except Exception as e:
        print(f"[WARN] runtime boot failed: {e}")
        rt = None


# ─── HTML генерируется на лету ────────────────────────────────
def generate_html() -> str:
    """Генерирует HTML с актуальным токеном и doors."""
    doors_json = json.dumps(DOORS, ensure_ascii=False)
    token = "MONOMOD::MM5FFF681946L6G6A111"

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#050508">
<meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>Multimod Polilog · Stream</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color:transparent; }}
html, body {{ height:100%; background:#050508; color:#c8c8d4;
  font: 14px/1.4 'Courier New', monospace; overflow:hidden; }}
#app {{ position:absolute; inset:0; display:grid;
  grid-template-rows: auto 1fr auto; }}
#header {{ padding:10px 14px; background:#08080c;
  border-bottom:1px solid #14141c;
  display:flex; gap:10px; align-items:center; font-size:10px;
  letter-spacing:1.4px; flex-wrap:wrap; }}
#header .core {{ color:#e8c39e; font-weight:bold; }}
#header .tok  {{ color:#4dd0c7; }}
#header .st   {{ color:#8888a0; }}
#header .fps  {{ color:#a78bfa; margin-left:auto; }}
#main {{ position:relative; overflow:hidden; }}
#canvas {{ position:absolute; inset:0; width:100%; height:100%; display:block; }}
#doors {{ position:absolute; top:10px; left:10px; right:10px;
  display:flex; gap:6px; flex-wrap:wrap; z-index:3; }}
#doors button {{ background:#0e0e14; border:1px solid #1c1c26;
  color:#8888a0; padding:6px 10px;
  font:9px 'Courier New', monospace; letter-spacing:1.2px;
  cursor:pointer; text-transform:uppercase; }}
#doors button.on {{ border-color:#4dd0c7; color:#4dd0c7; }}
#invariant {{ position:absolute; top:50%; left:50%;
  transform:translate(-50%,-50%);
  font-size:40px; letter-spacing:8px;
  color:#e8c39e; z-index:3;
  text-shadow:0 0 20px #050508, 0 0 40px #050508;
  pointer-events:none; }}
#stress-wrap {{ position:absolute; left:10px; bottom:10px;
  width:220px; z-index:3; }}
#stress-label {{ font-size:9px; color:#44445a;
  letter-spacing:1.4px; text-transform:uppercase;
  margin-bottom:4px; }}
#stress-bar {{ height:6px; background:#14141c; position:relative; }}
#stress-fill {{ position:absolute; left:0; top:0; bottom:0;
  width:0; background:#ff6b9d; transition:width .15s; }}
#footer {{ padding:10px 14px; background:#08080c;
  border-top:1px solid #14141c;
  display:flex; gap:10px; align-items:center;
  font-size:9px; letter-spacing:1.2px;
  text-transform:uppercase; color:#44445a; flex-wrap:wrap; }}
#footer button {{ background:#0e0e14; border:1px solid #1c1c26;
  color:#8888a0; padding:8px 12px;
  font:9px 'Courier New', monospace;
  letter-spacing:1.2px; cursor:pointer;
  text-transform:uppercase; }}
#footer button:hover {{ border-color:#4dd0c7; color:#4dd0c7; }}
#status {{ margin-left:auto; color:#8888a0; }}
#status.on {{ color:#2ed573; }}
#status.off {{ color:#ff4757; }}
</style>
</head>
<body>

<div id="app">
  <div id="header">
    <span class="core">𝕄_full</span>
    <span class="tok">{token}</span>
    <span class="st" id="h-status">stream: off</span>
    <span class="fps" id="h-fps">-- Hz</span>
  </div>

  <div id="main">
    <canvas id="canvas"></canvas>
    <div id="doors"></div>
    <div id="invariant">1 : 1 : 1</div>
    <div id="stress-wrap">
      <div id="stress-label">stress · хаос снизу</div>
      <div id="stress-bar"><div id="stress-fill"></div></div>
    </div>
  </div>

  <div id="footer">
    <button id="btn-sound">🔊 звук: выкл</button>
    <button id="btn-reconnect">⟳ переподключить</button>
    <span id="status" class="off">disconnected</span>
  </div>
</div>

<script>
"use strict";

const DOORS = {doors_json};
const WS_URL = (location.protocol === "https:" ? "wss://" : "ws://")
  + location.host + "/ws/state";

let ws = null;
let lastState = null;
let smoothed = null;
let canvas, ctx, W, H;
let doorsEl, statusEl, fpsEl, stressFill, hStatus;

let audioCtx = null;
let osc = null;
let noiseSource = null;
let noiseGain = null;
let gainMain = null;
let soundOn = false;

let measuredFps = 60;
let reconnectDelay = 1000;
let reconnectTimer = null;
let frameCount = 0;

function boot() {{
  canvas = document.getElementById("canvas");
  ctx = canvas.getContext("2d");
  doorsEl = document.getElementById("doors");
  statusEl = document.getElementById("status");
  fpsEl = document.getElementById("h-fps");
  stressFill = document.getElementById("stress-fill");
  hStatus = document.getElementById("h-status");

  resize();
  window.addEventListener("resize", resize);

  document.getElementById("btn-sound").addEventListener("click", toggleSound);
  document.getElementById("btn-reconnect").addEventListener("click", () => {{
    if (ws) try {{ ws.close(); }} catch (e) {{}}
    connect();
  }});

  measureFps();
  connect();
  renderLoop();
}}

function resize() {{
  W = canvas.width = canvas.clientWidth;
  H = canvas.height = canvas.clientHeight;
}}

function connect() {{
  clearTimeout(reconnectTimer);
  setStatus("connecting to " + WS_URL, "off");

  try {{
    ws = new WebSocket(WS_URL);
  }} catch (e) {{
    setStatus("bad url: " + e.message, "off");
    scheduleReconnect();
    return;
  }}

  ws.onopen = () => {{
    setStatus("connected", "on");
    hStatus.textContent = "stream: on";
    reconnectDelay = 1000;
  }};

  ws.onmessage = (ev) => {{
    try {{
      lastState = JSON.parse(ev.data);
    }} catch (e) {{}}
  }};

  ws.onclose = () => {{
    setStatus("disconnected", "off");
    hStatus.textContent = "stream: off";
    scheduleReconnect();
  }};

  ws.onerror = (e) => {{
    setStatus("error: " + (e.message || "unknown"), "off");
  }};
}}

function scheduleReconnect() {{
  reconnectTimer = setTimeout(() => {{
    reconnectDelay = Math.min(reconnectDelay * 1.5, 15000);
    connect();
  }}, reconnectDelay);
}}

function setStatus(text, cls) {{
  statusEl.textContent = text;
  statusEl.className = cls;
}}

function measureFps() {{
  let frames = 0;
  let last = performance.now();
  function tick(now) {{
    frames++;
    if (now - last >= 1000) {{
      measuredFps = Math.round(frames * 1000 / (now - last));
      frames = 0; last = now;
      fpsEl.textContent = measuredFps + " Hz";
    }}
    requestAnimationFrame(tick);
  }}
  requestAnimationFrame(tick);
}}

let doorsBuilt = false;
function buildDoors() {{
  if (doorsBuilt) return;
  doorsEl.innerHTML = "";
  for (const d of DOORS) {{
    const b = document.createElement("button");
    b.textContent = d;
    b.dataset.door = d;
    b.addEventListener("click", () => {{
      if (ws && ws.readyState === WebSocket.OPEN) {{
        ws.send(JSON.stringify({{ type: "set_door", door: d }}));
      }}
    }});
    doorsEl.appendChild(b);
  }}
  doorsBuilt = true;
}}

function markDoor(door) {{
  for (const b of doorsEl.children) {{
    b.classList.toggle("on", b.dataset.door === door);
  }}
}}

function renderLoop() {{
  frameCount++;

  if (lastState) {{
    buildDoors();
    markDoor(lastState.door);

    if (!smoothed) {{
      smoothed = JSON.parse(JSON.stringify(lastState));
    }} else {{
      const alpha = 0.08;
      for (const k of ["density","coherence","rhythm","depth","novelty"]) {{
        smoothed.v[k] += (lastState.v[k] - smoothed.v[k]) * alpha;
      }}
      smoothed.stress += (lastState.stress - smoothed.stress) * alpha;
      smoothed.door = lastState.door;
    }}

    drawState(smoothed, frameCount);
    stressFill.style.width = (smoothed.stress * 100) + "%";
  }} else {{
    drawIdle();
  }}

  requestAnimationFrame(renderLoop);
}}

function drawState(s, t) {{
  const v = s.v;
  ctx.fillStyle = "#050508";
  ctx.fillRect(0, 0, W, H);

  const hue = (v.depth * 180 + 30) % 360;

  const g = ctx.createRadialGradient(W/2, H/2, 20, W/2, H/2, Math.min(W,H)/2);
  g.addColorStop(0, `hsla(${{hue}}, 60%, 40%, ${{0.3 + v.density * 0.35}})`);
  g.addColorStop(1, "hsla(240, 20%, 5%, 0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);

  const n = 24;
  for (let i = 0; i < n; i++) {{
    const a = (i / n) * Math.PI * 2 + t * 0.002;
    const r = 60 + v.rhythm * 100 + Math.sin(t * 0.008 + i) * 12;
    const x = W/2 + Math.cos(a) * r;
    const y = H/2 + Math.sin(a) * r;
    const rad = 1.5 + v.coherence * 2.5;
    ctx.fillStyle = `hsla(${{(hue + i * 4) % 360}}, 70%, 60%, ${{0.5 + v.novelty * 0.4}})`;
    ctx.beginPath();
    ctx.arc(x, y, rad, 0, Math.PI * 2);
    ctx.fill();
  }}

  ctx.fillStyle = "#e8c39e";
  ctx.beginPath();
  ctx.arc(W/2, H/2, 3 + v.depth * 4, 0, Math.PI * 2);
  ctx.fill();
}}

function drawIdle() {{
  ctx.fillStyle = "#050508";
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = "#1c1c26";
  ctx.beginPath();
  ctx.arc(W/2, H/2, 3, 0, Math.PI * 2);
  ctx.fill();
}}

function toggleSound() {{
  if (!soundOn) startSound();
  else stopSound();
}}

function startSound() {{
  try {{
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") audioCtx.resume();

    osc = audioCtx.createOscillator();
    osc.type = "sine";
    osc.frequency.value = 110;

    const bufSize = 2 * audioCtx.sampleRate;
    const buf = audioCtx.createBuffer(1, bufSize, audioCtx.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
    noiseSource = audioCtx.createBufferSource();
    noiseSource.buffer = buf;
    noiseSource.loop = true;

    noiseGain = audioCtx.createGain();
    noiseGain.gain.value = 0.02;

    gainMain = audioCtx.createGain();
    gainMain.gain.value = 0.15;

    osc.connect(gainMain);
    noiseSource.connect(noiseGain);
    noiseGain.connect(gainMain);
    gainMain.connect(audioCtx.destination);

    osc.start();
    noiseSource.start();
    soundOn = true;
    document.getElementById("btn-sound").textContent = "🔊 звук: вкл";

    setInterval(() => {{
      if (!soundOn || !smoothed || !audioCtx) return;
      osc.frequency.value = 110 + smoothed.v.depth * 80;
      gainMain.gain.value = 0.1 + smoothed.v.density * 0.15;
      noiseGain.gain.value = 0.005 + smoothed.stress * 0.06;
    }}, 100);
  }} catch (e) {{
    console.warn("audio failed:", e);
  }}
}}

function stopSound() {{
  try {{
    if (osc) {{ osc.stop(); osc.disconnect(); osc = null; }}
    if (noiseSource) {{ noiseSource.stop(); noiseSource.disconnect(); noiseSource = null; }}
    if (gainMain) {{ gainMain.disconnect(); gainMain = null; }}
    if (audioCtx) {{ audioCtx.close(); audioCtx = null; }}
  }} catch (e) {{}}
  soundOn = false;
  document.getElementById("btn-sound").textContent = "🔊 звук: выкл";
}}

boot();
</script>

</body>
</html>
"""


NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


@app.get("/")
async def root():
    return JSONResponse(
        {
            "service": "Multimod Polilog backend",
            "version": "0.3",
            "token": "MONOMOD::MM5FFF681946L6G6A111",
            "runtime": RUNTIME_AVAILABLE and rt is not None,
            "doors": DOORS,
            "invariant": INVARIANT,
            "app": "/app",
            "ws": "/ws/state",
        },
        headers=NO_CACHE_HEADERS,
    )


@app.get("/app")
async def serve_app():
    """Генерирует HTML на лету. Не кэшируется."""
    return HTMLResponse(generate_html(), headers=NO_CACHE_HEADERS)


@app.get("/ws-test")
async def ws_test():
    """Простой тест WebSocket — прямо на экране."""
    return HTMLResponse("""<!DOCTYPE html>
<html><body style="background:#111;color:#eee;font-family:monospace;padding:20px">
<h2>WebSocket test</h2>
<pre id="log" style="background:#000;padding:10px;white-space:pre-wrap"></pre>
<script>
const log = document.getElementById('log');
const url = (location.protocol === "https:" ? "wss://" : "ws://")
  + location.host + "/ws/state";
log.textContent = "URL: " + url + "\\n";
const ws = new WebSocket(url);
ws.onopen = () => log.textContent += "OPEN\\n";
ws.onmessage = (e) => log.textContent += "MSG: " + e.data.slice(0, 100) + "\\n";
ws.onerror = (e) => log.textContent += "ERROR: " + (e.message || "unknown") + "\\n";
ws.onclose = (e) => log.textContent += "CLOSE: code=" + e.code + " reason=" + e.reason + "\\n";
</script>
</body></html>""", headers=NO_CACHE_HEADERS)


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
    print(f"🧬 Multimod Polilog backend v0.3")
    print(f"   token: MONOMOD::MM5FFF681946L6G6A111")
    print(f"   app:   http://0.0.0.0:{port}/app")
    print(f"   ws:    ws://0.0.0.0:{port}/ws/state")
    print(f"   test:  http://0.0.0.0:{port}/ws-test")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")