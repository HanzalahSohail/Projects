# """
# FastAPI server for Voice AI Pipeline with Tool Calling.

# Endpoints:
#   GET  /              → Web UI
#   WS   /ws/audio      → Full duplex audio + tools
#   POST /api/text      → Text mode with tools
#   GET  /api/health    → Health check
#   GET  /api/tools     → List registered tools
#   GET  /api/leads     → View CRM leads
#   GET  /api/call-logs → View call logs
# """

# import os
# import json
# import time
# import asyncio
# import base64
# from pathlib import Path

# from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
# from fastapi.responses import HTMLResponse, JSONResponse
# from fastapi.templating import Jinja2Templates
# from dotenv import load_dotenv

# from voice_pipeline import (
#     ConversationContext,
#     LatencyTracker,
#     run_pipeline,
#     run_pipeline_with_tools,
#     transcribe_audio_stream,
#     init_tools,
#     DEEPGRAM_API_KEY,
#     get_tts_manager,
#     AZURE_OPENAI_ENDPOINT,
#     AZURE_OPENAI_API_KEY,
# )
# from tools import registry

# load_dotenv()

# app = FastAPI(title="Voice AI Pipeline + Tools")

# templates_dir = Path(__file__).parent / "templates"
# templates_dir.mkdir(exist_ok=True)
# templates = Jinja2Templates(directory=str(templates_dir))

# # Initialize tools at startup
# # Initialize tools and open persistent TTS WebSocket at startup
# init_tools()


# #new code
# # @app.on_event("startup")
# # async def startup():
# #     await get_tts_manager()  # opens TTS WS before first request



# conversations = {}


# def get_conversation(session_id: str) -> ConversationContext:
#     if session_id not in conversations:
#         conversations[session_id] = ConversationContext()
#     return conversations[session_id]


# # ─── Health Check ────────────────────────────────────────────────────────────

# @app.get("/api/health")
# async def health():
#     return {
#         "status": "ok",
#         "deepgram_configured": bool(DEEPGRAM_API_KEY),
#         "azure_openai_configured": bool(AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY),
#         "tools_registered": registry.list_tools(),
#         "tool_count": len(registry.list_tools()),
#     }


# # ─── Tools List ──────────────────────────────────────────────────────────────

# @app.get("/api/tools")
# async def list_tools():
#     tools = registry.get_openai_tools()
#     return {"tools": [t["function"]["name"] for t in tools], "schemas": tools}


# # ─── CRM Data ────────────────────────────────────────────────────────────────

# @app.get("/api/leads")
# async def get_leads():
#     data_file = Path(__file__).parent / "data" / "leads.json"
#     if data_file.exists():
#         return json.loads(data_file.read_text())
#     return []


# @app.get("/api/call-logs")
# async def get_call_logs():
#     data_file = Path(__file__).parent / "data" / "call_logs.json"
#     if data_file.exists():
#         return json.loads(data_file.read_text())
#     return []


# # ─── Web UI ──────────────────────────────────────────────────────────────────

# @app.get("/", response_class=HTMLResponse)
# async def index(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})


# # ─── Text Mode ───────────────────────────────────────────────────────────────

# @app.post("/api/text")
# async def text_to_voice(request: Request):
#     body = await request.json()
#     user_text = body.get("text", "").strip()
#     session_id = body.get("session_id", "default")
#     voice = body.get("voice", "aura-asteria-en")

#     if not user_text:
#         return JSONResponse({"error": "No text provided"}, status_code=400)

#     conversation = get_conversation(session_id)
#     tracker = LatencyTracker()

#     audio_chunks = []
#     async for chunk in run_pipeline(user_text, conversation, tracker, voice):
#         audio_chunks.append(chunk)

#     audio_bytes = b"".join(audio_chunks)
#     audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

#     return {
#         "audio_base64": audio_b64,
#         "audio_format": "linear16",
#         "sample_rate": 16000,
#         "latency": tracker.report(),
#         "session_id": session_id,
#     }


# # ─── WebSocket Audio + Tools ────────────────────────────────────────────────

# @app.websocket("/ws/audio")
# async def audio_websocket(ws: WebSocket):
#     await ws.accept()
#     session_id = f"ws-{id(ws)}"
#     conversation = get_conversation(session_id)
#     print(f"[WS] Client connected: {session_id}")

#     audio_queue = asyncio.Queue()
#     processing = False

#     async def on_final_transcript(text: str):
#         nonlocal processing
#         if processing:
#             return
#         processing = True

#         try:
#             await ws.send_text(json.dumps({"type": "transcript", "text": text}))

#             tracker = LatencyTracker()

#             async def audio_callback(audio_bytes: bytes):
#                 await ws.send_bytes(audio_bytes)
#                 await ws.send_text(json.dumps({"type": "tts_done"}))

#             async def tool_status_callback(status: str):
#                 await ws.send_text(json.dumps({"type": "tool_status", "text": status}))

#             report = await run_pipeline_with_tools(
#                 text, conversation, tracker,
#                 audio_callback, tool_status_callback,
#                 voice="aura-asteria-en"
#             )

#             # Send response text
#             msgs = conversation.get_messages()
#             for m in reversed(msgs):
#                 if m.get("role") == "assistant" and m.get("content"):
#                     await ws.send_text(json.dumps({"type": "response", "text": m["content"]}))
#                     break

#             await ws.send_text(json.dumps({"type": "latency", "metrics": report}))

#         except Exception as e:
#             print(f"[WS] Pipeline error: {e}")
#             import traceback
#             traceback.print_exc()
#             try:
#                 await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
#             except Exception:
#                 pass
#         finally:
#             processing = False

#     async def on_partial_transcript(text: str):
#         try:
#             await ws.send_text(json.dumps({"type": "partial", "text": text}))
#         except Exception:
#             pass

#     stt_task = asyncio.create_task(
#         transcribe_audio_stream(audio_queue, on_final_transcript, on_partial_transcript)
#     )

#     try:
#         while True:
#             data = await ws.receive()
#             if data.get("type") == "websocket.receive":
#                 if "bytes" in data and data["bytes"]:
#                     await audio_queue.put(data["bytes"])
#                 elif "text" in data and data["text"]:
#                     msg = json.loads(data["text"])
#                     if msg.get("type") == "stop":
#                         await audio_queue.put(None)
#                     elif msg.get("type") == "clear":
#                         conversation.clear()
#                         await ws.send_text(json.dumps({"type": "status", "message": "Cleared"}))
#     except WebSocketDisconnect:
#         print(f"[WS] Disconnected: {session_id}")
#     except Exception as e:
#         print(f"[WS] Error: {e}")
#     finally:
#         await audio_queue.put(None)
#         stt_task.cancel()
#         conversations.pop(session_id, None)


# if __name__ == "__main__":
#     import uvicorn
#     print("=" * 60)
#     print("  Voice AI Pipeline + Tool Calling")
#     print("  http://localhost:8000")
#     print("=" * 60)
#     uvicorn.run(app, host="0.0.0.0", port=8000)






"""
FastAPI server for Voice AI Pipeline with Tool Calling + WebSocket TTS.

Key change: TTS now uses persistent WebSocket to Deepgram, not REST API.
"""

import os
import json
import asyncio
import base64
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from voice_pipeline import (
    ConversationContext, LatencyTracker,
    run_pipeline, run_pipeline_with_tools,
    transcribe_audio_stream, init_tools,
    DEEPGRAM_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY,
)
from tts_websocket import close_tts_ws
from tools import registry

load_dotenv()

app = FastAPI(title="Voice AI Pipeline + Tools")
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

init_tools()

conversations = {}


def get_conversation(sid: str) -> ConversationContext:
    if sid not in conversations:
        conversations[sid] = ConversationContext()
    return conversations[sid]


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "deepgram_configured": bool(DEEPGRAM_API_KEY),
        "azure_openai_configured": bool(AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY),
        "tools_registered": registry.list_tools(),
        "tool_count": len(registry.list_tools()),
        "tts_mode": "websocket",
    }


@app.get("/api/tools")
async def list_tools():
    schemas = registry.get_openai_tools()
    return {"tools": [t["function"]["name"] for t in schemas], "schemas": schemas}


@app.get("/api/leads")
async def get_leads():
    f = Path(__file__).parent / "data" / "leads.json"
    return json.loads(f.read_text()) if f.exists() else []


@app.get("/api/call-logs")
async def get_call_logs():
    f = Path(__file__).parent / "data" / "call_logs.json"
    return json.loads(f.read_text()) if f.exists() else []


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/text")
async def text_to_voice(request: Request):
    body = await request.json()
    user_text = body.get("text", "").strip()
    session_id = body.get("session_id", "default")
    voice = body.get("voice", "aura-asteria-en")

    if not user_text:
        return JSONResponse({"error": "No text"}, status_code=400)

    conversation = get_conversation(session_id)
    tracker = LatencyTracker()

    chunks = []
    async for chunk in run_pipeline(user_text, conversation, tracker, voice):
        chunks.append(chunk)

    audio = b"".join(chunks)
    return {
        "audio_base64": base64.b64encode(audio).decode("utf-8"),
        "audio_format": "linear16",
        "sample_rate": 16000,
        "latency": tracker.report(),
        "session_id": session_id,
    }


# ─── WebSocket: Audio + Tools + WebSocket TTS ───────────────────────────────

@app.websocket("/ws/audio")
async def audio_websocket(ws: WebSocket):
    await ws.accept()
    session_id = f"ws-{id(ws)}"
    conversation = get_conversation(session_id)
    print(f"[WS] Connected: {session_id}")

    audio_queue = asyncio.Queue()
    processing = False

    async def on_final_transcript(text: str):
        nonlocal processing
        if processing:
            return
        processing = True

        try:
            await ws.send_text(json.dumps({"type": "transcript", "text": text}))

            tracker = LatencyTracker()

            async def audio_callback(audio_bytes: bytes):
                """Forward TTS audio chunks to browser client."""
                await ws.send_bytes(audio_bytes)

            async def tool_status_callback(status: str):
                await ws.send_text(json.dumps({"type": "tool_status", "text": status}))

            report = await run_pipeline_with_tools(
                text, conversation, tracker,
                audio_callback, tool_status_callback,
                voice="aura-asteria-en",
                session_id=session_id,
            )

            # Signal audio complete
            await ws.send_text(json.dumps({"type": "tts_done"}))

            # Send response text for chat display
            msgs = conversation.get_messages()
            for m in reversed(msgs):
                if m.get("role") == "assistant" and m.get("content"):
                    await ws.send_text(json.dumps({"type": "response", "text": m["content"]}))
                    break

            await ws.send_text(json.dumps({"type": "latency", "metrics": report}))

        except Exception as e:
            print(f"[WS] Pipeline error: {e}")
            import traceback
            traceback.print_exc()
            try:
                await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
            except Exception:
                pass
        finally:
            processing = False

    async def on_partial(text: str):
        try:
            await ws.send_text(json.dumps({"type": "partial", "text": text}))
        except Exception:
            pass

    stt_task = asyncio.create_task(
        transcribe_audio_stream(audio_queue, on_final_transcript, on_partial)
    )

    try:
        while True:
            data = await ws.receive()
            if data.get("type") == "websocket.receive":
                if "bytes" in data and data["bytes"]:
                    await audio_queue.put(data["bytes"])
                elif "text" in data and data["text"]:
                    msg = json.loads(data["text"])
                    if msg.get("type") == "stop":
                        await audio_queue.put(None)
                    elif msg.get("type") == "clear":
                        conversation.clear()
                        await ws.send_text(json.dumps({"type": "status", "message": "Cleared"}))
    except WebSocketDisconnect:
        print(f"[WS] Disconnected: {session_id}")
    except Exception as e:
        print(f"[WS] Error: {e}")
    finally:
        await audio_queue.put(None)
        stt_task.cancel()
        # Clean up TTS WebSocket for this session
        try:
            await close_tts_ws(session_id)
        except Exception:
            pass
        conversations.pop(session_id, None)


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  Voice AI Pipeline + Tools (WebSocket TTS)")
    print("  http://localhost:8000")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)