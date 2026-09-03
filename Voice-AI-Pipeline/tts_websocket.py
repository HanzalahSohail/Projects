# """
# Deepgram WebSocket TTS Client

# A persistent WebSocket connection to Deepgram's TTS API.
# - Open ONCE at conversation start (or reuse across turns)
# - Send text chunks as LLM tokens arrive
# - Receive audio chunks back in real-time
# - Flush to force remaining audio out

# Protocol:
#   Send: {"type": "Speak", "text": "Hello world."}
#   Send: {"type": "Flush"}
#   Send: {"type": "Close"}
#   Recv: binary audio bytes (linear16 PCM)
#   Recv: {"type": "Flushed"} after flush completes
# """

# import os
# import json
# import asyncio
# import time
# import websockets
# from dotenv import load_dotenv

# load_dotenv()

# DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
# DEEPGRAM_TTS_WS_URL = "wss://api.deepgram.com/v1/speak"


# class DeepgramTTSWebSocket:
#     """
#     Persistent WebSocket connection to Deepgram TTS.

#     Usage:
#         tts = DeepgramTTSWebSocket()
#         await tts.connect()

#         # As LLM tokens arrive, send text:
#         await tts.send_text("Hello, ")
#         await tts.send_text("how are you today?")

#         # Flush to get remaining audio:
#         await tts.flush()

#         # Audio arrives via the callback you set:
#         tts.on_audio = async def callback(audio_bytes): ...

#         # When done with conversation:
#         await tts.close()
#     """

#     def __init__(self, voice: str = "aura-asteria-en", sample_rate: int = 16000,
#                  encoding: str = "linear16"):
#         self.voice = voice
#         self.sample_rate = sample_rate
#         self.encoding = encoding
#         self.ws = None
#         self._receive_task = None
#         self._connected = False

#         # Callbacks
#         self.on_audio = None       # async fn(bytes) — called for each audio chunk
#         self.on_flushed = None     # async fn() — called when flush completes
#         self.on_error = None       # async fn(str) — called on errors

#         # Flush synchronization
#         self._flush_event = asyncio.Event()

#     @property
#     def is_connected(self) -> bool:
#         return self._connected and self.ws is not None

#     async def connect(self):
#         """Open WebSocket connection to Deepgram TTS."""
#         if self._connected:
#             return

#         url = (
#             f"{DEEPGRAM_TTS_WS_URL}"
#             f"?model={self.voice}"
#             f"&encoding={self.encoding}"
#             f"&sample_rate={self.sample_rate}"
#             f"&container=none"
#         )

#         headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

#         connect_start = time.time()
#         try:
#             self.ws = await websockets.connect(
#                 url,
#                 extra_headers=headers,
#                 ping_interval=20,
#                 ping_timeout=10,
#                 close_timeout=5,
#             )
#             self._connected = True
#             elapsed = round((time.time() - connect_start) * 1000, 1)
#             print(f"[TTS-WS] Connected to Deepgram TTS WebSocket in {elapsed}ms")

#             # Start receiving audio in background
#             self._receive_task = asyncio.create_task(self._receive_loop())

#         except Exception as e:
#             print(f"[TTS-WS] Connection failed: {e}")
#             self._connected = False
#             raise

#     async def send_text(self, text: str):
#         """Send a text chunk to be synthesized. Can be called multiple times."""
#         if not self.is_connected:
#             print("[TTS-WS] Not connected, attempting reconnect...")
#             await self.connect()

#         msg = json.dumps({"type": "Speak", "text": text})
#         await self.ws.send(msg)
#         print(f"[TTS-WS] Sent text: {text[:60]}...")

#     async def flush(self, timeout: float = 15.0):
#         """
#         Send Flush command and wait until Deepgram confirms all audio has been sent.
#         This blocks until the Flushed response arrives or timeout.
#         """
#         if not self.is_connected:
#             return

#         self._flush_event.clear()
#         await self.ws.send(json.dumps({"type": "Flush"}))
#         print("[TTS-WS] Flush sent, waiting for Flushed response...")

#         try:
#             await asyncio.wait_for(self._flush_event.wait(), timeout=timeout)
#             print("[TTS-WS] Flush complete")
#         except asyncio.TimeoutError:
#             print(f"[TTS-WS] Flush timeout after {timeout}s")

#     async def close(self):
#         """Gracefully close the WebSocket."""
#         if not self.is_connected:
#             return

#         try:
#             await self.ws.send(json.dumps({"type": "Close"}))
#             await self.ws.close()
#         except Exception as e:
#             print(f"[TTS-WS] Close error: {e}")
#         finally:
#             self._connected = False
#             if self._receive_task:
#                 self._receive_task.cancel()
#                 try:
#                     await self._receive_task
#                 except (asyncio.CancelledError, Exception):
#                     pass
#             print("[TTS-WS] Connection closed")

#     async def reset(self):
#         """
#         Send Clear + Flush to discard any queued text (for interruption handling).
#         Then the connection is reusable for the next turn.
#         """
#         if not self.is_connected:
#             return

#         try:
#             await self.ws.send(json.dumps({"type": "Clear"}))
#             await self.ws.send(json.dumps({"type": "Flush"}))
#             # Wait briefly for the flushed response
#             self._flush_event.clear()
#             try:
#                 await asyncio.wait_for(self._flush_event.wait(), timeout=3.0)
#             except asyncio.TimeoutError:
#                 pass
#             print("[TTS-WS] Reset complete (cleared + flushed)")
#         except Exception as e:
#             print(f"[TTS-WS] Reset error: {e}")

#     async def _receive_loop(self):
#         """Background task: receive audio chunks and control messages."""
#         try:
#             async for message in self.ws:
#                 if isinstance(message, bytes):
#                     # Audio data
#                     if message and self.on_audio:
#                         await self.on_audio(message)
#                 elif isinstance(message, str):
#                     # Control message
#                     try:
#                         data = json.loads(message)
#                         msg_type = data.get("type", "")

#                         if msg_type == "Flushed":
#                             self._flush_event.set()
#                             if self.on_flushed:
#                                 await self.on_flushed()

#                         elif msg_type == "Warning":
#                             print(f"[TTS-WS] Warning: {data.get('warn_msg', data)}")

#                         elif msg_type == "Error":
#                             err = data.get("err_msg", str(data))
#                             print(f"[TTS-WS] Error: {err}")
#                             if self.on_error:
#                                 await self.on_error(err)

#                         else:
#                             print(f"[TTS-WS] Message: {data}")

#                     except json.JSONDecodeError:
#                         print(f"[TTS-WS] Non-JSON text: {message[:100]}")

#         except websockets.exceptions.ConnectionClosed as e:
#             print(f"[TTS-WS] Connection closed: {e}")
#         except asyncio.CancelledError:
#             pass
#         except Exception as e:
#             print(f"[TTS-WS] Receive error: {e}")
#         finally:
#             self._connected = False


# # ─── Connection Pool ─────────────────────────────────────────────────────────

# _tts_connections: dict[str, DeepgramTTSWebSocket] = {}


# async def get_tts_ws(session_id: str = "default",
#                       voice: str = "aura-asteria-en") -> DeepgramTTSWebSocket:
#     """
#     Get or create a TTS WebSocket for a session.
#     Reuses connection across turns in the same conversation.
#     """
#     key = f"{session_id}:{voice}"

#     if key in _tts_connections and _tts_connections[key].is_connected:
#         return _tts_connections[key]

#     # Create new connection
#     tts = DeepgramTTSWebSocket(voice=voice)
#     await tts.connect()
#     _tts_connections[key] = tts
#     return tts


# async def close_tts_ws(session_id: str = "default", voice: str = "aura-asteria-en"):
#     """Close and remove a TTS WebSocket for a session."""
#     key = f"{session_id}:{voice}"
#     if key in _tts_connections:
#         tts = _tts_connections.pop(key)
#         await tts.close()


"""
Deepgram WebSocket TTS Client

A persistent WebSocket connection to Deepgram's TTS API.
- Open ONCE at conversation start (or reuse across turns)
- Send text chunks as LLM tokens arrive
- Receive audio chunks back in real-time
- Flush to force remaining audio out

Protocol:
  Send: {"type": "Speak", "text": "Hello world."}
  Send: {"type": "Flush"}
  Send: {"type": "Close"}
  Recv: binary audio bytes (linear16 PCM)
  Recv: {"type": "Flushed"} after flush completes
"""

import os
import json
import asyncio
import time
import websockets
from dotenv import load_dotenv

load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
DEEPGRAM_TTS_WS_URL = "wss://api.deepgram.com/v1/speak"


class DeepgramTTSWebSocket:
    """
    Persistent WebSocket connection to Deepgram TTS.

    Usage:
        tts = DeepgramTTSWebSocket()
        await tts.connect()

        # As LLM tokens arrive, send text:
        await tts.send_text("Hello, ")
        await tts.send_text("how are you today?")

        # Flush to get remaining audio:
        await tts.flush()

        # Audio arrives via the callback you set:
        tts.on_audio = async def callback(audio_bytes): ...

        # When done with conversation:
        await tts.close()
    """

    def __init__(self, voice: str = "aura-asteria-en", sample_rate: int = 16000,
                 encoding: str = "linear16"):
        self.voice = voice
        self.sample_rate = sample_rate
        self.encoding = encoding
        self.ws = None
        self._receive_task = None
        self._connected = False

        # Callbacks
        self.on_audio = None       # async fn(bytes) — called for each audio chunk
        self.on_flushed = None     # async fn() — called when flush completes
        self.on_error = None       # async fn(str) — called on errors

        # Flush synchronization
        self._flush_event = asyncio.Event()

    @property
    def is_connected(self) -> bool:
        return self._connected and self.ws is not None

    async def connect(self):
        """Open WebSocket connection to Deepgram TTS."""
        if self._connected:
            return

        url = (
            f"{DEEPGRAM_TTS_WS_URL}"
            f"?model={self.voice}"
            f"&encoding={self.encoding}"
            f"&sample_rate={self.sample_rate}"
            f"&container=none"
        )

        headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

        connect_start = time.time()
        try:
            self.ws = await websockets.connect(
                url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
            )
            self._connected = True
            elapsed = round((time.time() - connect_start) * 1000, 1)
            print(f"[TTS-WS] Connected to Deepgram TTS WebSocket in {elapsed}ms")

            # Start receiving audio in background
            self._receive_task = asyncio.create_task(self._receive_loop())

        except Exception as e:
            print(f"[TTS-WS] Connection failed: {e}")
            self._connected = False
            raise

    async def send_text(self, text: str):
        """Send a text chunk to be synthesized. Can be called multiple times."""
        if not self.is_connected:
            print("[TTS-WS] Not connected, attempting reconnect...")
            await self.connect()

        msg = json.dumps({"type": "Speak", "text": text})
        await self.ws.send(msg)
        print(f"[TTS-WS] Sent text: {text[:60]}...")

    async def flush(self, timeout: float = 15.0):
        """
        Send Flush command and wait until Deepgram confirms all audio has been sent.
        This blocks until the Flushed response arrives or timeout.
        """
        if not self.is_connected:
            return

        self._flush_event.clear()
        await self.ws.send(json.dumps({"type": "Flush"}))
        print("[TTS-WS] Flush sent, waiting for Flushed response...")

        try:
            await asyncio.wait_for(self._flush_event.wait(), timeout=timeout)
            print("[TTS-WS] Flush complete")
        except asyncio.TimeoutError:
            print(f"[TTS-WS] Flush timeout after {timeout}s")

    async def close(self):
        """Gracefully close the WebSocket."""
        if not self.is_connected:
            return

        try:
            await self.ws.send(json.dumps({"type": "Close"}))
            await self.ws.close()
        except Exception as e:
            print(f"[TTS-WS] Close error: {e}")
        finally:
            self._connected = False
            if self._receive_task:
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except (asyncio.CancelledError, Exception):
                    pass
            print("[TTS-WS] Connection closed")

    async def reset(self):
        """
        Send Clear + Flush to discard any queued text (for interruption handling).
        Then the connection is reusable for the next turn.
        """
        if not self.is_connected:
            return

        try:
            await self.ws.send(json.dumps({"type": "Clear"}))
            await self.ws.send(json.dumps({"type": "Flush"}))
            # Wait briefly for the flushed response
            self._flush_event.clear()
            try:
                await asyncio.wait_for(self._flush_event.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                pass
            print("[TTS-WS] Reset complete (cleared + flushed)")
        except Exception as e:
            print(f"[TTS-WS] Reset error: {e}")

    async def _receive_loop(self):
        """Background task: receive audio chunks and control messages."""
        try:
            async for message in self.ws:
                if isinstance(message, bytes):
                    # Audio data
                    if message and self.on_audio:
                        await self.on_audio(message)
                elif isinstance(message, str):
                    # Control message
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type", "")

                        if msg_type == "Flushed":
                            # Call callback FIRST (sends buffered audio to client)
                            # THEN set event (so flush() returns after audio is sent)
                            if self.on_flushed:
                                await self.on_flushed()
                            self._flush_event.set()

                        elif msg_type == "Warning":
                            print(f"[TTS-WS] Warning: {data.get('warn_msg', data)}")

                        elif msg_type == "Error":
                            err = data.get("err_msg", str(data))
                            print(f"[TTS-WS] Error: {err}")
                            if self.on_error:
                                await self.on_error(err)

                        else:
                            print(f"[TTS-WS] Message: {data}")

                    except json.JSONDecodeError:
                        print(f"[TTS-WS] Non-JSON text: {message[:100]}")

        except websockets.exceptions.ConnectionClosed as e:
            print(f"[TTS-WS] Connection closed: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[TTS-WS] Receive error: {e}")
        finally:
            self._connected = False


# ─── Connection Pool ─────────────────────────────────────────────────────────

_tts_connections: dict[str, DeepgramTTSWebSocket] = {}


async def get_tts_ws(session_id: str = "default",
                      voice: str = "aura-asteria-en") -> DeepgramTTSWebSocket:
    """
    Get or create a TTS WebSocket for a session.
    Reuses connection across turns in the same conversation.
    """
    key = f"{session_id}:{voice}"

    if key in _tts_connections and _tts_connections[key].is_connected:
        return _tts_connections[key]

    # Create new connection
    tts = DeepgramTTSWebSocket(voice=voice)
    await tts.connect()
    _tts_connections[key] = tts
    return tts


async def close_tts_ws(session_id: str = "default", voice: str = "aura-asteria-en"):
    """Close and remove a TTS WebSocket for a session."""
    key = f"{session_id}:{voice}"
    if key in _tts_connections:
        tts = _tts_connections.pop(key)
        await tts.close()