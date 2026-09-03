# """
# Voice AI Pipeline with Tool Calling

# STT (Deepgram) → LLM + Tools (Azure OpenAI) → TTS (Deepgram)

# The LLM can now call tools (send_sms, book_meeting, etc.) during the conversation.
# When a tool call is detected, we execute it and feed the result back to the LLM,
# which then generates a natural language response about what happened.

# TTS is now streamed sentence-by-sentence so first audio plays in ~2s instead of ~9s.
# """

# import os
# import re
# import time
# import json
# import asyncio
# import aiohttp
# from dotenv import load_dotenv
# from openai import AsyncAzureOpenAI, APIConnectionError

# from tools import registry, ToolResult
# from tools.messaging import register_messaging_tools
# from tools.crm import register_crm_tools
# from tools.scheduling import register_scheduling_tools

# load_dotenv()

# # ─── Configuration ───────────────────────────────────────────────────────────

# DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
# AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
# AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
# AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
# AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

# DEEPGRAM_STT_URL = "wss://api.deepgram.com/v1/listen"
# DEEPGRAM_TTS_URL = "https://api.deepgram.com/v1/speak"

# from datetime import datetime, timedelta

# today = datetime.now().strftime("%Y-%m-%d")
# tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

# SYSTEM_PROMPT = f"""You are a helpful, friendly voice assistant with access to tools.
# You can send SMS, WhatsApp messages, emails, create leads, log call summaries,
# check meeting availability, book meetings, and cancel meetings.

# Today's date is {today}. Tomorrow is {tomorrow}.
# Always use real current dates when scheduling. Never use example or placeholder dates.
# When the user says "tomorrow" use {tomorrow}, "today" use {today}.

# When booking meetings, the user is in Asia/Karachi timezone (UTC+5).
# Always convert their requested time to UTC before booking.
# If user says 10am, book at 05:00:00Z (subtract 5 hours for UTC).
# The attendee timezone should always be Asia/Karachi.

# Rules:
# - Keep spoken responses concise (1-3 sentences).
# - When using a tool, confirm what you're about to do, then do it.
# - After a tool executes, tell the user the result naturally.
# - If a tool fails, explain what went wrong and offer alternatives.
# - Always ask for confirmation before sending messages or booking meetings.
# - You're speaking out loud, so avoid bullet points, markdown, or code.
# - Be natural and human-like."""


# # ─── Initialize Tools ────────────────────────────────────────────────────────

# def init_tools():
#     """Register all tools. Call once at startup."""
#     register_messaging_tools()
#     register_crm_tools()
#     register_scheduling_tools()
#     print(f"[TOOLS] {len(registry.list_tools())} tools registered:")
#     print(registry.get_tool_descriptions())


# # ─── Persistent Clients ─────────────────────────────────────────────────────

# _tts_session: aiohttp.ClientSession | None = None
# _llm_client: AsyncAzureOpenAI | None = None


# async def get_tts_session() -> aiohttp.ClientSession:
#     global _tts_session
#     if _tts_session is None or _tts_session.closed:
#         connector = aiohttp.TCPConnector(limit=10, keepalive_timeout=60)
#         timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=25)
#         _tts_session = aiohttp.ClientSession(timeout=timeout, connector=connector)
#     return _tts_session


# def get_llm_client() -> AsyncAzureOpenAI:
#     global _llm_client
#     if _llm_client is None:
#         _llm_client = AsyncAzureOpenAI(
#             azure_endpoint=AZURE_OPENAI_ENDPOINT,
#             api_key=AZURE_OPENAI_API_KEY,
#             api_version=AZURE_OPENAI_API_VERSION,
#         )
#     return _llm_client


# # ─── Latency Tracker ────────────────────────────────────────────────────────

# class LatencyTracker:
#     def __init__(self):
#         self.reset()

#     def reset(self):
#         self.t0_transcript = None
#         self.t1_llm_request = None
#         self.t2_llm_first_token = None
#         self.t3_tts_request = None
#         self.t4_tts_first_chunk = None
#         self.t5_playback_start = None
#         self.tool_execution_ms = 0

#     def mark(self, stage: str):
#         ts = time.time()
#         if getattr(self, stage) is None:
#             setattr(self, stage, ts)
#         return ts

#     def report(self) -> dict:
#         r = {}
#         if self.t0_transcript and self.t5_playback_start:
#             r["total_voice_response_ms"] = round((self.t5_playback_start - self.t0_transcript) * 1000, 1)
#         if self.t1_llm_request and self.t2_llm_first_token:
#             r["llm_first_token_ms"] = round((self.t2_llm_first_token - self.t1_llm_request) * 1000, 1)
#         if self.t3_tts_request and self.t4_tts_first_chunk:
#             r["tts_first_chunk_ms"] = round((self.t4_tts_first_chunk - self.t3_tts_request) * 1000, 1)
#         if self.tool_execution_ms:
#             r["tool_execution_ms"] = self.tool_execution_ms
#         return r


# # ─── Conversation History ───────────────────────────────────────────────────

# class ConversationContext:
#     def __init__(self, max_turns: int = 20):
#         self.max_turns = max_turns
#         self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

#     def add_user(self, text: str):
#         self.messages.append({"role": "user", "content": text})
#         self._trim()

#     def add_assistant(self, text: str):
#         self.messages.append({"role": "assistant", "content": text})
#         self._trim()

#     def add_tool_call(self, tool_call_id: str, name: str, arguments: str):
#         self.messages.append({
#             "role": "assistant",
#             "content": None,
#             "tool_calls": [{
#                 "id": tool_call_id,
#                 "type": "function",
#                 "function": {"name": name, "arguments": arguments}
#             }]
#         })

#     def add_tool_result(self, tool_call_id: str, result: str):
#         self.messages.append({
#             "role": "tool",
#             "tool_call_id": tool_call_id,
#             "content": result
#         })

#     def _trim(self):
#         if len(self.messages) > 1 + self.max_turns * 2:
#             self.messages = [self.messages[0]] + self.messages[-(self.max_turns * 2):]

#     def get_messages(self) -> list:
#         return self.messages.copy()

#     def clear(self):
#         self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]


# # ─── STT: Deepgram Streaming ────────────────────────────────────────────────

# async def transcribe_audio_stream(audio_queue: asyncio.Queue,
#                                    transcript_callback,
#                                    partial_callback=None):
#     import websockets

#     params = (
#         "?encoding=linear16&sample_rate=16000&channels=1"
#         "&model=nova-2&punctuate=true"
#         "&interim_results=true&endpointing=300&vad_events=true"
#     )
#     url = DEEPGRAM_STT_URL + params
#     headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

#     async with websockets.connect(url, extra_headers=headers) as ws:
#         print("[STT] Connected to Deepgram")

#         async def send_audio():
#             try:
#                 while True:
#                     chunk = await audio_queue.get()
#                     if chunk is None:
#                         await ws.send(json.dumps({"type": "CloseStream"}))
#                         break
#                     await ws.send(chunk)
#             except Exception as e:
#                 print(f"[STT] Send error: {e}")

#         async def receive_transcripts():
#             try:
#                 async for msg in ws:
#                     data = json.loads(msg)
#                     if data.get("type") == "Results":
#                         alt = data["channel"]["alternatives"][0]
#                         transcript = alt.get("transcript", "").strip()
#                         is_final = data.get("is_final", False)
#                         if transcript:
#                             if is_final:
#                                 print(f"[STT] Final: {transcript}")
#                                 await transcript_callback(transcript)
#                             elif partial_callback:
#                                 await partial_callback(transcript)
#             except Exception as e:
#                 print(f"[STT] Receive error: {e}")

#         await asyncio.gather(send_audio(), receive_transcripts())


# # ─── LLM: Tool Calling Rounds (non-streaming) ───────────────────────────────

# MAX_TOOL_ROUNDS = 5
# MAX_LLM_RETRIES = 3


# async def _call_llm_with_retry(client, messages, tools, stream=False):
#     """
#     Call Azure OpenAI with retry logic on connection errors.
#     Resets the global client on failure so a fresh connection is used.
#     """
#     global _llm_client

#     for attempt in range(MAX_LLM_RETRIES):
#         try:
#             response = await client.chat.completions.create(
#                 model=AZURE_OPENAI_DEPLOYMENT,
#                 messages=messages,
#                 tools=tools if tools else None,
#                 tool_choice="auto" if tools else None,
#                 max_tokens=300,
#                 temperature=0.7,
#                 stream=stream,
#             )
#             return response
#         except APIConnectionError as e:
#             if attempt == MAX_LLM_RETRIES - 1:
#                 raise
#             print(f"[LLM] Connection error, retrying ({attempt + 1}/{MAX_LLM_RETRIES})...")
#             _llm_client = None          # force fresh client + connection pool
#             client = get_llm_client()
#             await asyncio.sleep(0.5 * (attempt + 1))


# async def run_tool_rounds(conversation: ConversationContext,
#                            user_text: str,
#                            tracker: LatencyTracker,
#                            tool_status_callback=None) -> bool:
#     """
#     Handle tool-calling rounds only (non-streaming).
#     Adds user message, executes any tool calls, stops before final text response.

#     Returns True if tool calls were made (final response needs streaming),
#     Returns False if the LLM returned text directly without tools (rare for short replies).

#     NOTE: If the LLM returns text directly (no tool calls needed), it is saved
#     to conversation and this function returns the text via the 'direct_reply'
#     attribute set on the conversation object for the caller to detect.
#     """
#     conversation.add_user(user_text)
#     tracker.mark("t1_llm_request")

#     client = get_llm_client()
#     tools = registry.get_openai_tools()

#     # Reset direct_reply sentinel
#     conversation._direct_reply = None

#     for round_num in range(MAX_TOOL_ROUNDS):
#         print(f"[LLM] Tool round {round_num + 1}, messages: {len(conversation.get_messages())}")

#         response = await _call_llm_with_retry(
#             client, conversation.get_messages(), tools, stream=False
#         )

#         choice = response.choices[0]
#         message = choice.message

#         if round_num == 0:
#             tracker.mark("t2_llm_first_token")

#         # ── Tool call(s) requested ──
#         if message.tool_calls:
#             for tool_call in message.tool_calls:
#                 fn_name = tool_call.function.name
#                 fn_args_str = tool_call.function.arguments
#                 tc_id = tool_call.id

#                 print(f"[LLM] Tool call: {fn_name}({fn_args_str})")

#                 if tool_status_callback:
#                     await tool_status_callback(f"Calling {fn_name}...")

#                 conversation.add_tool_call(tc_id, fn_name, fn_args_str)

#                 try:
#                     fn_args = json.loads(fn_args_str)
#                 except json.JSONDecodeError:
#                     fn_args = {}

#                 tool_start = time.time()
#                 result = await registry.execute(fn_name, fn_args)
#                 tool_ms = round((time.time() - tool_start) * 1000, 1)
#                 tracker.tool_execution_ms += tool_ms

#                 result_str = json.dumps({
#                     "success": result.success,
#                     "result": result.result,
#                     "error": result.error
#                 })
#                 conversation.add_tool_result(tc_id, result_str)

#                 print(f"[LLM] Tool result: {result_str[:100]}...")

#                 if tool_status_callback:
#                     status = f"{fn_name} {'succeeded' if result.success else 'failed'}"
#                     await tool_status_callback(status)

#             # Loop back for the LLM's response to the tool result
#             continue

#         # ── LLM returned text directly (no tool calls) ──
#         # This happens on the very first round when no tool is needed.
#         # Store it so the caller can stream it to TTS.
#         reply = message.content or ""
#         conversation._direct_reply = reply
#         print(f"[LLM] Direct reply (no tools): {reply[:80]}...")
#         return False   # signal: no tool rounds executed, use direct_reply

#     # All tool rounds done — ready for streaming final response
#     return True


# # ─── LLM: Streaming Final Response → Sentence-Chunked TTS ──────────────────

# SENTENCE_ENDS = re.compile(r'(?<=[.!?:])\s+')


# def _split_into_sentence(buffer: str):
#     """
#     Return (sentence_to_speak, remaining_buffer).
#     Splits on sentence-ending punctuation followed by whitespace.
#     """
#     parts = SENTENCE_ENDS.split(buffer, maxsplit=1)
#     if len(parts) == 2:
#         return parts[0].strip(), parts[1]
#     return None, buffer


# async def stream_response_to_tts(conversation: ConversationContext,
#                                    tracker: LatencyTracker,
#                                    audio_callback,
#                                    voice: str = "aura-asteria-en") -> str:
#     """
#     Stream the final LLM response and pipe each sentence to TTS immediately.
#     This is what cuts TTS latency from ~9s to ~2s.

#     Returns the full response text.
#     """
#     client = get_llm_client()
#     session = await get_tts_session()

#     # No tools on this round — we just want the spoken response
#     stream = await _call_llm_with_retry(
#         client,
#         conversation.get_messages(),
#         tools=None,   # intentionally no tools here
#         stream=True,
#     )

#     buffer = ""
#     full_response = ""
#     first_token = True
#     first_audio = True

#     async for chunk in stream:
#         delta = chunk.choices[0].delta.content or ""
#         if not delta:
#             continue

#         buffer += delta
#         full_response += delta

#         if first_token:
#             tracker.mark("t2_llm_first_token")
#             first_token = False

#         # Check if we have a complete sentence ready to speak
#         sentence, buffer = _split_into_sentence(buffer)

#         if sentence:
#             print(f"[TTS] Sending chunk: '{sentence[:60]}...'")
#             tracker.mark("t3_tts_request")
#             audio = await synthesize_speech_bytes(sentence, voice, session)

#             if audio:
#                 if first_audio:
#                     tracker.mark("t4_tts_first_chunk")
#                     tracker.mark("t5_playback_start")
#                     first_audio = False
#                 await audio_callback(audio)

#     # Flush any remaining text in the buffer
#     remainder = buffer.strip()
#     if remainder:
#         print(f"[TTS] Flushing remainder: '{remainder[:60]}'")
#         tracker.mark("t3_tts_request")
#         audio = await synthesize_speech_bytes(remainder, voice, session)
#         if audio:
#             if first_audio:
#                 tracker.mark("t4_tts_first_chunk")
#                 tracker.mark("t5_playback_start")
#             await audio_callback(audio)

#     # Save full response to conversation history
#     conversation.add_assistant(full_response)
#     print(f"[LLM] Full streamed response: {full_response[:100]}...")
#     return full_response


# # ─── TTS: Deepgram ──────────────────────────────────────────────────────────

# async def synthesize_speech_bytes(text: str, voice: str = "aura-asteria-en",
#                                    session: aiohttp.ClientSession = None) -> bytes:
#     if not session:
#         session = await get_tts_session()

#     url = f"{DEEPGRAM_TTS_URL}?model={voice}&encoding=linear16&sample_rate=16000&container=none"
#     headers = {
#         "Authorization": f"Token {DEEPGRAM_API_KEY}",
#         "Content-Type": "application/json",
#     }
#     body = {"text": text}

#     tts_start = time.time()
#     try:
#         async with session.post(url, headers=headers, json=body) as resp:
#             if resp.status != 200:
#                 error = await resp.text()
#                 print(f"[TTS] Error {resp.status}: {error}")
#                 return b""

#             audio = await resp.read()
#             elapsed = round((time.time() - tts_start) * 1000, 1)

#             if audio[:4] == b'RIFF':
#                 audio = audio[44:]

#             print(f"[TTS] {len(audio)} bytes in {elapsed}ms")
#             return audio

#     except asyncio.TimeoutError:
#         print(f"[TTS] Timeout")
#         return b""
#     except Exception as e:
#         print(f"[TTS] Error: {e}")
#         return b""


# # ─── Full Pipeline (with tools + streaming TTS) ─────────────────────────────

# async def run_pipeline_with_tools(user_text: str,
#                                    conversation: ConversationContext,
#                                    tracker: LatencyTracker,
#                                    audio_callback,
#                                    tool_status_callback=None,
#                                    voice: str = "aura-asteria-en"):
#     """
#     Full pipeline: STT transcript → LLM tool rounds → streaming TTS → audio.

#     Flow:
#       1. run_tool_rounds()  — non-streaming, handles all tool calls
#       2. stream_response_to_tts() — streams final LLM response, fires TTS per sentence

#     If no tools were called (direct_reply set), we still stream the response
#     for consistent low-latency behaviour.
#     """
#     tracker.reset()
#     tracker.mark("t0_transcript")

#     # Step 1: Handle tool calling rounds (non-streaming)
#     tools_were_called = await run_tool_rounds(
#         conversation, user_text, tracker, tool_status_callback
#     )

#     if not tools_were_called and conversation._direct_reply is not None:
#         # LLM answered directly without tools — synthesize the direct reply
#         # via TTS (not streamed, since it's already complete text)
#         direct_text = conversation._direct_reply
#         conversation.add_assistant(direct_text)

#         if direct_text:
#             tracker.mark("t3_tts_request")
#             session = await get_tts_session()
#             audio = await synthesize_speech_bytes(direct_text, voice, session)
#             if audio:
#                 tracker.mark("t4_tts_first_chunk")
#                 tracker.mark("t5_playback_start")
#                 await audio_callback(audio)
#     else:
#         # Step 2: Stream final response to TTS sentence by sentence
#         response_text = await stream_response_to_tts(
#             conversation, tracker, audio_callback, voice
#         )

#         if not response_text:
#             # Fallback: nothing came back from stream
#             fallback = "I've completed the actions. Is there anything else you need?"
#             conversation.add_assistant(fallback)
#             session = await get_tts_session()
#             audio = await synthesize_speech_bytes(fallback, voice, session)
#             if audio:
#                 tracker.mark("t4_tts_first_chunk")
#                 tracker.mark("t5_playback_start")
#                 await audio_callback(audio)

#     report = tracker.report()
#     print(f"[PIPELINE] Latency: {json.dumps(report)}")
#     return report


# # ─── Legacy pipeline (no tools, for /api/text endpoint) ─────────────────────

# async def llm_with_tools(conversation: ConversationContext,
#                           user_text: str,
#                           tracker: LatencyTracker,
#                           tool_status_callback=None) -> str:
#     """
#     Kept for backward compatibility with run_pipeline() used by /api/text.
#     Non-streaming, returns full response text.
#     """
#     conversation.add_user(user_text)
#     tracker.mark("t1_llm_request")

#     client = get_llm_client()
#     tools = registry.get_openai_tools()

#     for round_num in range(MAX_TOOL_ROUNDS):
#         print(f"[LLM] Round {round_num + 1}, messages: {len(conversation.get_messages())}")

#         response = await _call_llm_with_retry(
#             client, conversation.get_messages(), tools, stream=False
#         )

#         choice = response.choices[0]
#         message = choice.message

#         if round_num == 0:
#             tracker.mark("t2_llm_first_token")

#         if message.tool_calls:
#             for tool_call in message.tool_calls:
#                 fn_name = tool_call.function.name
#                 fn_args_str = tool_call.function.arguments
#                 tc_id = tool_call.id

#                 print(f"[LLM] Tool call: {fn_name}({fn_args_str})")

#                 if tool_status_callback:
#                     await tool_status_callback(f"Calling {fn_name}...")

#                 conversation.add_tool_call(tc_id, fn_name, fn_args_str)

#                 try:
#                     fn_args = json.loads(fn_args_str)
#                 except json.JSONDecodeError:
#                     fn_args = {}

#                 tool_start = time.time()
#                 result = await registry.execute(fn_name, fn_args)
#                 tool_ms = round((time.time() - tool_start) * 1000, 1)
#                 tracker.tool_execution_ms += tool_ms

#                 result_str = json.dumps({
#                     "success": result.success,
#                     "result": result.result,
#                     "error": result.error
#                 })
#                 conversation.add_tool_result(tc_id, result_str)

#                 if tool_status_callback:
#                     status = f"{fn_name} {'succeeded' if result.success else 'failed'}"
#                     await tool_status_callback(status)

#             continue

#         reply = message.content or ""
#         conversation.add_assistant(reply)
#         print(f"[LLM] Final response: {reply[:100]}...")
#         return reply

#     fallback = "I've completed the actions. Is there anything else you need?"
#     conversation.add_assistant(fallback)
#     return fallback


# async def run_pipeline(user_text: str,
#                         conversation: ConversationContext,
#                         tracker: LatencyTracker,
#                         voice: str = "aura-asteria-en"):
#     """Simple pipeline without streaming. Used by /api/text endpoint."""
#     tracker.reset()
#     tracker.mark("t0_transcript")

#     response_text = await llm_with_tools(conversation, user_text, tracker)

#     if not response_text:
#         return

#     tracker.mark("t3_tts_request")
#     session = await get_tts_session()
#     audio = await synthesize_speech_bytes(response_text, voice, session)

#     if audio:
#         tracker.mark("t4_tts_first_chunk")
#         tracker.mark("t5_playback_start")
#         yield audio

#     report = tracker.report()
#     print(f"[LATENCY] {json.dumps(report, indent=2)}")



# """
# Voice AI Pipeline with Tool Calling + WebSocket TTS

# Key latency optimizations per supervisor feedback:
#   1. TTS WebSocket opened IMMEDIATELY when transcript commits (not after LLM)
#   2. LLM tokens streamed directly to TTS WebSocket (no waiting for full sentence)
#   3. Persistent TTS WebSocket stays open across conversation turns
#   4. Audio chunks flow back to client as they're generated

# Flow:
#   transcript committed
#     → open/reuse TTS WebSocket (if not already open)
#     → run LLM (tool rounds if needed, then streaming response)
#     → LLM tokens → sent to TTS WebSocket as text chunks
#     → audio bytes stream back → forwarded to client immediately
#     → Flush at end of LLM response → final audio arrives
# """

# import os
# import re
# import time
# import json
# import asyncio
# import aiohttp
# from dotenv import load_dotenv
# from openai import AsyncAzureOpenAI, APIConnectionError

# from tools import registry, ToolResult
# from tools.messaging import register_messaging_tools
# from tools.crm import register_crm_tools
# from tools.scheduling import register_scheduling_tools
# from tts_websocket import DeepgramTTSWebSocket, get_tts_ws, close_tts_ws

# load_dotenv()

# # ─── Configuration ───────────────────────────────────────────────────────────

# DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
# AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
# AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
# AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
# AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

# DEEPGRAM_STT_URL = "wss://api.deepgram.com/v1/listen"
# DEEPGRAM_TTS_URL = "https://api.deepgram.com/v1/speak"

# from datetime import datetime, timedelta

# today = datetime.now().strftime("%Y-%m-%d")
# tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

# SYSTEM_PROMPT = f"""You are a helpful, friendly voice assistant with access to tools.
# You can send SMS, WhatsApp messages, emails, create leads, log call summaries,
# check meeting availability, book meetings, and cancel meetings.

# Today's date is {today}. Tomorrow is {tomorrow}.
# When the user says "tomorrow" use {tomorrow}, "today" use {today}.

# Rules:
# - Keep spoken responses concise (1-3 sentences).
# - When using a tool, confirm what you're about to do, then do it.
# - After a tool executes, tell the user the result naturally.
# - If a tool fails, explain what went wrong and offer alternatives.
# - You're speaking out loud, so avoid bullet points, markdown, or code.
# - Be natural and human-like."""


# # ─── Initialize Tools ────────────────────────────────────────────────────────

# def init_tools():
#     register_messaging_tools()
#     register_crm_tools()
#     register_scheduling_tools()
#     print(f"[TOOLS] {len(registry.list_tools())} tools registered:")
#     print(registry.get_tool_descriptions())


# # ─── Persistent LLM Client ──────────────────────────────────────────────────

# _llm_client: AsyncAzureOpenAI | None = None


# def get_llm_client() -> AsyncAzureOpenAI:
#     global _llm_client
#     if _llm_client is None:
#         _llm_client = AsyncAzureOpenAI(
#             azure_endpoint=AZURE_OPENAI_ENDPOINT,
#             api_key=AZURE_OPENAI_API_KEY,
#             api_version=AZURE_OPENAI_API_VERSION,
#         )
#     return _llm_client


# # ─── Persistent REST TTS session (fallback for /api/text) ───────────────────

# _tts_session: aiohttp.ClientSession | None = None


# async def get_tts_session() -> aiohttp.ClientSession:
#     global _tts_session
#     if _tts_session is None or _tts_session.closed:
#         connector = aiohttp.TCPConnector(limit=5, keepalive_timeout=60)
#         timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=25)
#         _tts_session = aiohttp.ClientSession(timeout=timeout, connector=connector)
#     return _tts_session


# # ─── Latency Tracker ────────────────────────────────────────────────────────

# class LatencyTracker:
#     def __init__(self):
#         self.reset()

#     def reset(self):
#         self.t0_transcript = None
#         self.t1_llm_request = None
#         self.t2_llm_first_token = None
#         self.t3_tts_first_text = None     # first text sent to TTS WS
#         self.t4_tts_first_audio = None    # first audio chunk received back
#         self.t5_playback_start = None     # first audio sent to client
#         self.tool_execution_ms = 0
#         self.tts_ws_connect_ms = 0

#     def mark(self, stage: str):
#         ts = time.time()
#         if getattr(self, stage) is None:
#             setattr(self, stage, ts)
#         return ts

#     def report(self) -> dict:
#         r = {}
#         if self.t0_transcript and self.t5_playback_start:
#             r["total_voice_response_ms"] = round((self.t5_playback_start - self.t0_transcript) * 1000, 1)
#         if self.t1_llm_request and self.t2_llm_first_token:
#             r["llm_first_token_ms"] = round((self.t2_llm_first_token - self.t1_llm_request) * 1000, 1)
#         if self.t3_tts_first_text and self.t4_tts_first_audio:
#             r["tts_first_audio_ms"] = round((self.t4_tts_first_audio - self.t3_tts_first_text) * 1000, 1)
#         if self.tool_execution_ms:
#             r["tool_execution_ms"] = self.tool_execution_ms
#         if self.tts_ws_connect_ms:
#             r["tts_ws_connect_ms"] = self.tts_ws_connect_ms
#         return r


# # ─── Conversation History ───────────────────────────────────────────────────

# class ConversationContext:
#     def __init__(self, max_turns: int = 20):
#         self.max_turns = max_turns
#         self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
#         self._direct_reply = None

#     def add_user(self, text: str):
#         self.messages.append({"role": "user", "content": text})
#         self._trim()

#     def add_assistant(self, text: str):
#         self.messages.append({"role": "assistant", "content": text})
#         self._trim()

#     def add_tool_call(self, tool_call_id: str, name: str, arguments: str):
#         self.messages.append({
#             "role": "assistant", "content": None,
#             "tool_calls": [{"id": tool_call_id, "type": "function",
#                             "function": {"name": name, "arguments": arguments}}]
#         })

#     def add_tool_result(self, tool_call_id: str, result: str):
#         self.messages.append({"role": "tool", "tool_call_id": tool_call_id, "content": result})

#     def _trim(self):
#         if len(self.messages) > 1 + self.max_turns * 2:
#             self.messages = [self.messages[0]] + self.messages[-(self.max_turns * 2):]

#     def get_messages(self) -> list:
#         return self.messages.copy()

#     def clear(self):
#         self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]


# # ─── STT: Deepgram Streaming ────────────────────────────────────────────────

# async def transcribe_audio_stream(audio_queue: asyncio.Queue,
#                                    transcript_callback, partial_callback=None):
#     import websockets

#     params = (
#         "?encoding=linear16&sample_rate=16000&channels=1"
#         "&model=nova-2&punctuate=true"
#         "&interim_results=true&endpointing=300&vad_events=true"
#     )
#     url = DEEPGRAM_STT_URL + params
#     headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

#     async with websockets.connect(url, extra_headers=headers) as ws:
#         print("[STT] Connected to Deepgram")

#         async def send_audio():
#             try:
#                 while True:
#                     chunk = await audio_queue.get()
#                     if chunk is None:
#                         await ws.send(json.dumps({"type": "CloseStream"}))
#                         break
#                     await ws.send(chunk)
#             except Exception as e:
#                 print(f"[STT] Send error: {e}")

#         async def receive_transcripts():
#             try:
#                 async for msg in ws:
#                     data = json.loads(msg)
#                     if data.get("type") == "Results":
#                         alt = data["channel"]["alternatives"][0]
#                         transcript = alt.get("transcript", "").strip()
#                         is_final = data.get("is_final", False)
#                         if transcript:
#                             if is_final:
#                                 print(f"[STT] Final: {transcript}")
#                                 await transcript_callback(transcript)
#                             elif partial_callback:
#                                 await partial_callback(transcript)
#             except Exception as e:
#                 print(f"[STT] Receive error: {e}")

#         await asyncio.gather(send_audio(), receive_transcripts())


# # ─── LLM with Retry ─────────────────────────────────────────────────────────

# MAX_TOOL_ROUNDS = 5
# MAX_LLM_RETRIES = 3


# async def _call_llm(client, messages, tools, stream=False):
#     global _llm_client
#     for attempt in range(MAX_LLM_RETRIES):
#         try:
#             return await client.chat.completions.create(
#                 model=AZURE_OPENAI_DEPLOYMENT,
#                 messages=messages,
#                 tools=tools if tools else None,
#                 tool_choice="auto" if tools else None,
#                 max_tokens=300, temperature=0.7, stream=stream,
#             )
#         except APIConnectionError:
#             if attempt == MAX_LLM_RETRIES - 1:
#                 raise
#             print(f"[LLM] Connection error, retry {attempt+1}/{MAX_LLM_RETRIES}")
#             _llm_client = None
#             client = get_llm_client()
#             await asyncio.sleep(0.5 * (attempt + 1))


# # ─── Tool Calling Rounds (non-streaming) ────────────────────────────────────

# async def run_tool_rounds(conversation, user_text, tracker, tool_status_callback=None):
#     """
#     Handle tool calls. Returns True if tools were called (needs streaming follow-up),
#     False if LLM replied directly (text stored in conversation._direct_reply).
#     """
#     conversation.add_user(user_text)
#     tracker.mark("t1_llm_request")

#     client = get_llm_client()
#     tools = registry.get_openai_tools()
#     conversation._direct_reply = None

#     for round_num in range(MAX_TOOL_ROUNDS):
#         print(f"[LLM] Tool round {round_num+1}")
#         response = await _call_llm(client, conversation.get_messages(), tools, stream=False)
#         choice = response.choices[0]
#         message = choice.message

#         if round_num == 0:
#             tracker.mark("t2_llm_first_token")

#         if message.tool_calls:
#             for tc in message.tool_calls:
#                 fn_name = tc.function.name
#                 fn_args_str = tc.function.arguments
#                 tc_id = tc.id
#                 print(f"[LLM] Tool call: {fn_name}({fn_args_str})")

#                 if tool_status_callback:
#                     await tool_status_callback(f"Calling {fn_name}...")

#                 conversation.add_tool_call(tc_id, fn_name, fn_args_str)

#                 try:
#                     fn_args = json.loads(fn_args_str)
#                 except json.JSONDecodeError:
#                     fn_args = {}

#                 t_start = time.time()
#                 result = await registry.execute(fn_name, fn_args)
#                 tracker.tool_execution_ms += round((time.time() - t_start) * 1000, 1)

#                 result_str = json.dumps({"success": result.success, "result": result.result, "error": result.error})
#                 conversation.add_tool_result(tc_id, result_str)

#                 if tool_status_callback:
#                     await tool_status_callback(f"{fn_name} {'succeeded' if result.success else 'failed'}")
#             continue

#         reply = message.content or ""
#         conversation._direct_reply = reply
#         return False

#     return True


# # ─── Streaming LLM → WebSocket TTS Pipeline ─────────────────────────────────

# SENTENCE_ENDS = re.compile(r'(?<=[.!?])\s+')


# async def stream_llm_to_tts_ws(conversation, tracker, audio_callback,
#                                  session_id="default", voice="aura-asteria-en"):
#     """
#     Core optimized pipeline:
#       1. Get/reuse TTS WebSocket (already opened at transcript time)
#       2. Stream LLM response tokens
#       3. Send each sentence directly to TTS WebSocket
#       4. Audio chunks flow back via callback immediately
#       5. Flush at end to get remaining audio

#     Returns the full response text.
#     """
#     client = get_llm_client()
#     tts_ws = await get_tts_ws(session_id, voice)

#     # Wire up audio callback — every audio chunk from TTS goes to client
#     first_audio = True

#     async def on_audio(audio_bytes):
#         nonlocal first_audio
#         if first_audio:
#             tracker.mark("t4_tts_first_audio")
#             tracker.mark("t5_playback_start")
#             first_audio = False
#         await audio_callback(audio_bytes)

#     tts_ws.on_audio = on_audio

#     # Stream LLM response
#     stream = await _call_llm(client, conversation.get_messages(), tools=None, stream=True)

#     buffer = ""
#     full_response = ""
#     first_token = True

#     async for chunk in stream:
#         delta = chunk.choices[0].delta.content or ""
#         if not delta:
#             continue

#         buffer += delta
#         full_response += delta

#         if first_token:
#             tracker.mark("t2_llm_first_token")
#             first_token = False

#         # Split on sentence boundaries and send each to TTS
#         parts = SENTENCE_ENDS.split(buffer, maxsplit=1)
#         if len(parts) == 2:
#             sentence = parts[0].strip()
#             buffer = parts[1]

#             if sentence:
#                 tracker.mark("t3_tts_first_text")
#                 await tts_ws.send_text(sentence + " ")
#                 print(f"[PIPE] → TTS: '{sentence[:50]}...'")

#     # Flush remaining buffer
#     remainder = buffer.strip()
#     if remainder:
#         tracker.mark("t3_tts_first_text")
#         await tts_ws.send_text(remainder)
#         print(f"[PIPE] → TTS (final): '{remainder[:50]}'")

#     # Flush to get all remaining audio
#     await tts_ws.flush(timeout=15.0)

#     # Save to conversation
#     conversation.add_assistant(full_response)
#     print(f"[PIPE] Full response: {full_response[:80]}...")
#     return full_response


# # ─── Full Pipeline (WebSocket TTS) ──────────────────────────────────────────

# async def run_pipeline_with_tools(user_text, conversation, tracker,
#                                    audio_callback, tool_status_callback=None,
#                                    voice="aura-asteria-en", session_id="default"):
#     """
#     Full pipeline with supervisor's optimizations:
#       1. Transcript arrives → IMMEDIATELY ensure TTS WebSocket is open
#       2. Run tool rounds (non-streaming)
#       3. Stream final LLM response → WebSocket TTS → audio to client
#     """
#     tracker.reset()
#     tracker.mark("t0_transcript")

#     # ══════════════════════════════════════════════════════════════════
#     # STEP 0: Open TTS WebSocket NOW (before LLM even starts)
#     # This is the key insight from supervisor: "open as soon as
#     # transcript is committed" — don't wait for LLM to finish.
#     # ══════════════════════════════════════════════════════════════════
#     ws_start = time.time()
#     tts_ws = await get_tts_ws(session_id, voice)
#     tracker.tts_ws_connect_ms = round((time.time() - ws_start) * 1000, 1)
#     print(f"[PIPE] TTS WebSocket ready in {tracker.tts_ws_connect_ms}ms (reused={tracker.tts_ws_connect_ms < 10})")

#     # STEP 1: Tool calling rounds
#     tools_were_called = await run_tool_rounds(
#         conversation, user_text, tracker, tool_status_callback
#     )

#     if not tools_were_called and conversation._direct_reply is not None:
#         # LLM answered directly — send the text to TTS WebSocket
#         direct_text = conversation._direct_reply
#         conversation.add_assistant(direct_text)

#         if direct_text:
#             # Wire callback
#             first_audio = True

#             async def on_audio(audio_bytes):
#                 nonlocal first_audio
#                 if first_audio:
#                     tracker.mark("t4_tts_first_audio")
#                     tracker.mark("t5_playback_start")
#                     first_audio = False
#                 await audio_callback(audio_bytes)

#             tts_ws.on_audio = on_audio
#             tracker.mark("t3_tts_first_text")
#             await tts_ws.send_text(direct_text)
#             await tts_ws.flush(timeout=15.0)
#     else:
#         # STEP 2: Stream LLM → TTS WebSocket
#         await stream_llm_to_tts_ws(
#             conversation, tracker, audio_callback, session_id, voice
#         )

#     report = tracker.report()
#     print(f"[PIPE] Latency: {json.dumps(report)}")
#     return report


# # ─── REST TTS fallback (for /api/text endpoint) ─────────────────────────────

# async def synthesize_speech_bytes(text, voice="aura-asteria-en", session=None):
#     """REST TTS for text mode — kept as fallback."""
#     if not session:
#         session = await get_tts_session()

#     url = f"{DEEPGRAM_TTS_URL}?model={voice}&encoding=linear16&sample_rate=16000&container=none"
#     headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": "application/json"}
#     body = {"text": text}

#     try:
#         async with session.post(url, headers=headers, json=body) as resp:
#             if resp.status != 200:
#                 print(f"[TTS-REST] Error {resp.status}: {await resp.text()}")
#                 return b""
#             audio = await resp.read()
#             if audio[:4] == b'RIFF':
#                 audio = audio[44:]
#             return audio
#     except Exception as e:
#         print(f"[TTS-REST] Error: {e}")
#         return b""


# # ─── Legacy pipelines (for /api/text) ───────────────────────────────────────

# async def llm_with_tools(conversation, user_text, tracker, tool_status_callback=None):
#     """Non-streaming LLM with tools. Returns full text response."""
#     conversation.add_user(user_text)
#     tracker.mark("t1_llm_request")

#     client = get_llm_client()
#     tools = registry.get_openai_tools()

#     for round_num in range(MAX_TOOL_ROUNDS):
#         response = await _call_llm(client, conversation.get_messages(), tools, stream=False)
#         choice = response.choices[0]
#         message = choice.message

#         if round_num == 0:
#             tracker.mark("t2_llm_first_token")

#         if message.tool_calls:
#             for tc in message.tool_calls:
#                 fn_name, fn_args_str, tc_id = tc.function.name, tc.function.arguments, tc.id
#                 conversation.add_tool_call(tc_id, fn_name, fn_args_str)
#                 try:
#                     fn_args = json.loads(fn_args_str)
#                 except json.JSONDecodeError:
#                     fn_args = {}
#                 result = await registry.execute(fn_name, fn_args)
#                 conversation.add_tool_result(tc_id, json.dumps({"success": result.success, "result": result.result, "error": result.error}))
#             continue

#         reply = message.content or ""
#         conversation.add_assistant(reply)
#         return reply

#     fallback = "Done. Anything else?"
#     conversation.add_assistant(fallback)
#     return fallback


# async def run_pipeline(user_text, conversation, tracker, voice="aura-asteria-en"):
#     """REST pipeline for /api/text endpoint."""
#     tracker.reset()
#     tracker.mark("t0_transcript")

#     response_text = await llm_with_tools(conversation, user_text, tracker)
#     if not response_text:
#         return

#     tracker.mark("t3_tts_first_text")
#     session = await get_tts_session()
#     audio = await synthesize_speech_bytes(response_text, voice, session)
#     if audio:
#         tracker.mark("t4_tts_first_audio")
#         tracker.mark("t5_playback_start")
#         yield audio



"""
Voice AI Pipeline with Tool Calling + WebSocket TTS

Key latency optimizations per supervisor feedback:
  1. TTS WebSocket opened IMMEDIATELY when transcript commits (not after LLM)
  2. LLM tokens streamed directly to TTS WebSocket (no waiting for full sentence)
  3. Persistent TTS WebSocket stays open across conversation turns
  4. Audio chunks flow back to client as they're generated

Flow:
  transcript committed
    → open/reuse TTS WebSocket (if not already open)
    → run LLM (tool rounds if needed, then streaming response)
    → LLM tokens → sent to TTS WebSocket as text chunks
    → audio bytes stream back → forwarded to client immediately
    → Flush at end of LLM response → final audio arrives
"""

import os
import re
import time
import json
import asyncio
import aiohttp
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, APIConnectionError

from tools import registry, ToolResult
from tools.messaging import register_messaging_tools
from tools.crm import register_crm_tools
from tools.scheduling import register_scheduling_tools
from tts_websocket import DeepgramTTSWebSocket, get_tts_ws, close_tts_ws

load_dotenv()

# ─── Configuration ───────────────────────────────────────────────────────────

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

DEEPGRAM_STT_URL = "wss://api.deepgram.com/v1/listen"
DEEPGRAM_TTS_URL = "https://api.deepgram.com/v1/speak"

from datetime import datetime, timedelta

today = datetime.now().strftime("%Y-%m-%d")
tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

SYSTEM_PROMPT = f"""You are a helpful, friendly voice assistant with access to tools.
You can send SMS, WhatsApp messages, emails, create leads, log call summaries,
check meeting availability, book meetings, and cancel meetings.

Today's date is {today}. Tomorrow is {tomorrow}.
When the user says "tomorrow" use {tomorrow}, "today" use {today}.

Rules:
- Keep spoken responses concise (1-3 sentences).
- When using a tool, confirm what you're about to do, then do it.
- After a tool executes, tell the user the result naturally.
- If a tool fails, explain what went wrong and offer alternatives.
- You're speaking out loud, so avoid bullet points, markdown, or code.
- Be natural and human-like."""


# ─── Initialize Tools ────────────────────────────────────────────────────────

def init_tools():
    register_messaging_tools()
    register_crm_tools()
    register_scheduling_tools()
    print(f"[TOOLS] {len(registry.list_tools())} tools registered:")
    print(registry.get_tool_descriptions())


# ─── Persistent LLM Client ──────────────────────────────────────────────────

_llm_client: AsyncAzureOpenAI | None = None


def get_llm_client() -> AsyncAzureOpenAI:
    global _llm_client
    if _llm_client is None:
        _llm_client = AsyncAzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
        )
    return _llm_client


# ─── Persistent REST TTS session (fallback for /api/text) ───────────────────

_tts_session: aiohttp.ClientSession | None = None


async def get_tts_session() -> aiohttp.ClientSession:
    global _tts_session
    if _tts_session is None or _tts_session.closed:
        connector = aiohttp.TCPConnector(limit=5, keepalive_timeout=60)
        timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=25)
        _tts_session = aiohttp.ClientSession(timeout=timeout, connector=connector)
    return _tts_session


# ─── Latency Tracker ────────────────────────────────────────────────────────

class LatencyTracker:
    def __init__(self):
        self.reset()

    def reset(self):
        self.t0_transcript = None
        self.t1_llm_request = None
        self.t2_llm_first_token = None
        self.t3_tts_first_text = None     # first text sent to TTS WS
        self.t4_tts_first_audio = None    # first audio chunk received back
        self.t5_playback_start = None     # first audio sent to client
        self.tool_execution_ms = 0
        self.tts_ws_connect_ms = 0

    def mark(self, stage: str):
        ts = time.time()
        if getattr(self, stage) is None:
            setattr(self, stage, ts)
        return ts

    def report(self) -> dict:
        r = {}
        if self.t0_transcript and self.t5_playback_start:
            r["total_voice_response_ms"] = round((self.t5_playback_start - self.t0_transcript) * 1000, 1)
        if self.t1_llm_request and self.t2_llm_first_token:
            r["llm_first_token_ms"] = round((self.t2_llm_first_token - self.t1_llm_request) * 1000, 1)
        if self.t3_tts_first_text and self.t4_tts_first_audio:
            r["tts_first_audio_ms"] = round((self.t4_tts_first_audio - self.t3_tts_first_text) * 1000, 1)
        if self.tool_execution_ms:
            r["tool_execution_ms"] = self.tool_execution_ms
        if self.tts_ws_connect_ms:
            r["tts_ws_connect_ms"] = self.tts_ws_connect_ms
        return r


# ─── Conversation History ───────────────────────────────────────────────────

class ConversationContext:
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._direct_reply = None

    def add_user(self, text: str):
        self.messages.append({"role": "user", "content": text})
        self._trim()

    def add_assistant(self, text: str):
        self.messages.append({"role": "assistant", "content": text})
        self._trim()

    def add_tool_call(self, tool_call_id: str, name: str, arguments: str):
        self.messages.append({
            "role": "assistant", "content": None,
            "tool_calls": [{"id": tool_call_id, "type": "function",
                            "function": {"name": name, "arguments": arguments}}]
        })

    def add_tool_result(self, tool_call_id: str, result: str):
        self.messages.append({"role": "tool", "tool_call_id": tool_call_id, "content": result})

    def _trim(self):
        if len(self.messages) > 1 + self.max_turns * 2:
            self.messages = [self.messages[0]] + self.messages[-(self.max_turns * 2):]

    def get_messages(self) -> list:
        return self.messages.copy()

    def clear(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]


# ─── STT: Deepgram Streaming ────────────────────────────────────────────────

async def transcribe_audio_stream(audio_queue: asyncio.Queue,
                                   transcript_callback, partial_callback=None):
    import websockets

    params = (
        "?encoding=linear16&sample_rate=16000&channels=1"
        "&model=nova-2&punctuate=true"
        "&interim_results=true&endpointing=300&vad_events=true"
    )
    url = DEEPGRAM_STT_URL + params
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

    async with websockets.connect(url, extra_headers=headers) as ws:
        print("[STT] Connected to Deepgram")

        async def send_audio():
            try:
                while True:
                    chunk = await audio_queue.get()
                    if chunk is None:
                        await ws.send(json.dumps({"type": "CloseStream"}))
                        break
                    await ws.send(chunk)
            except Exception as e:
                print(f"[STT] Send error: {e}")

        async def receive_transcripts():
            try:
                async for msg in ws:
                    data = json.loads(msg)
                    if data.get("type") == "Results":
                        alt = data["channel"]["alternatives"][0]
                        transcript = alt.get("transcript", "").strip()
                        is_final = data.get("is_final", False)
                        if transcript:
                            if is_final:
                                print(f"[STT] Final: {transcript}")
                                await transcript_callback(transcript)
                            elif partial_callback:
                                await partial_callback(transcript)
            except Exception as e:
                print(f"[STT] Receive error: {e}")

        await asyncio.gather(send_audio(), receive_transcripts())


# ─── LLM with Retry ─────────────────────────────────────────────────────────

MAX_TOOL_ROUNDS = 5
MAX_LLM_RETRIES = 3


async def _call_llm(client, messages, tools, stream=False):
    global _llm_client
    for attempt in range(MAX_LLM_RETRIES):
        try:
            return await client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                max_tokens=300, temperature=0.7, stream=stream,
            )
        except APIConnectionError:
            if attempt == MAX_LLM_RETRIES - 1:
                raise
            print(f"[LLM] Connection error, retry {attempt+1}/{MAX_LLM_RETRIES}")
            _llm_client = None
            client = get_llm_client()
            await asyncio.sleep(0.5 * (attempt + 1))


# ─── Tool Calling Rounds (non-streaming) ────────────────────────────────────

async def run_tool_rounds(conversation, user_text, tracker, tool_status_callback=None):
    """
    Handle tool calls. Returns True if tools were called (needs streaming follow-up),
    False if LLM replied directly (text stored in conversation._direct_reply).
    """
    conversation.add_user(user_text)
    tracker.mark("t1_llm_request")

    client = get_llm_client()
    tools = registry.get_openai_tools()
    conversation._direct_reply = None

    for round_num in range(MAX_TOOL_ROUNDS):
        print(f"[LLM] Tool round {round_num+1}")
        response = await _call_llm(client, conversation.get_messages(), tools, stream=False)
        choice = response.choices[0]
        message = choice.message

        if round_num == 0:
            tracker.mark("t2_llm_first_token")

        if message.tool_calls:
            for tc in message.tool_calls:
                fn_name = tc.function.name
                fn_args_str = tc.function.arguments
                tc_id = tc.id
                print(f"[LLM] Tool call: {fn_name}({fn_args_str})")

                if tool_status_callback:
                    await tool_status_callback(f"Calling {fn_name}...")

                conversation.add_tool_call(tc_id, fn_name, fn_args_str)

                try:
                    fn_args = json.loads(fn_args_str)
                except json.JSONDecodeError:
                    fn_args = {}

                t_start = time.time()
                result = await registry.execute(fn_name, fn_args)
                tracker.tool_execution_ms += round((time.time() - t_start) * 1000, 1)

                result_str = json.dumps({"success": result.success, "result": result.result, "error": result.error})
                conversation.add_tool_result(tc_id, result_str)

                if tool_status_callback:
                    await tool_status_callback(f"{fn_name} {'succeeded' if result.success else 'failed'}")
            continue

        reply = message.content or ""
        conversation._direct_reply = reply
        return False

    return True


# ─── Streaming LLM → WebSocket TTS Pipeline ─────────────────────────────────

SENTENCE_ENDS = re.compile(r'(?<=[.!?])\s+')


async def stream_llm_to_tts_ws(conversation, tracker, audio_callback,
                                 session_id="default", voice="aura-asteria-en"):
    """
    Optimized pipeline: LLM tokens → TTS WebSocket → chunked audio to client.
    
    Audio buffering strategy:
      - Buffer incoming TTS audio chunks
      - Every time buffer reaches ~8KB (~0.25s of 16kHz PCM), merge and send to client
      - On flush (end of response), send whatever remains
      - No waiting for Deepgram Flushed response between sentences — just stream text in
      - Only flush once at the very end
    """
    client = get_llm_client()
    tts_ws = await get_tts_ws(session_id, voice)

    SEND_THRESHOLD = 8000  # ~0.25s of 16-bit 16kHz mono PCM
    audio_buffer = bytearray()
    first_audio_sent = False

    async def on_audio(audio_bytes):
        nonlocal audio_buffer, first_audio_sent
        tracker.mark("t4_tts_first_audio")
        audio_buffer.extend(audio_bytes)

        # Once we have enough audio, send a merged chunk to the client
        if len(audio_buffer) >= SEND_THRESHOLD:
            chunk_to_send = bytes(audio_buffer)
            audio_buffer = bytearray()

            if not first_audio_sent:
                tracker.mark("t5_playback_start")
                first_audio_sent = True

            await audio_callback(chunk_to_send)

    async def on_flushed():
        """Final flush — send any remaining buffered audio."""
        nonlocal audio_buffer, first_audio_sent
        if audio_buffer:
            chunk_to_send = bytes(audio_buffer)
            audio_buffer = bytearray()

            if not first_audio_sent:
                tracker.mark("t5_playback_start")
                first_audio_sent = True

            print(f"[PIPE] Flush: sending final {len(chunk_to_send)} bytes")
            await audio_callback(chunk_to_send)

    tts_ws.on_audio = on_audio
    tts_ws.on_flushed = on_flushed

    # Stream LLM response
    stream = await _call_llm(client, conversation.get_messages(), tools=None, stream=True)

    buffer = ""
    full_response = ""
    first_token = True
    sentence_count = 0

    async for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if not delta:
            continue

        buffer += delta
        full_response += delta

        if first_token:
            tracker.mark("t2_llm_first_token")
            first_token = False

        # Detect sentence boundaries → send text to TTS immediately (no flush between)
        parts = SENTENCE_ENDS.split(buffer, maxsplit=1)
        if len(parts) == 2:
            sentence = parts[0].strip()
            buffer = parts[1]

            if sentence:
                sentence_count += 1
                tracker.mark("t3_tts_first_text")
                await tts_ws.send_text(sentence + " ")
                print(f"[PIPE] Sentence {sentence_count} → TTS: '{sentence[:50]}'")

    # Send remaining text
    remainder = buffer.strip()
    if remainder:
        sentence_count += 1
        tracker.mark("t3_tts_first_text")
        await tts_ws.send_text(remainder)
        print(f"[PIPE] Final text → TTS: '{remainder[:50]}'")

    # ONE flush at the end to get remaining audio
    await tts_ws.flush(timeout=10.0)

    conversation.add_assistant(full_response)
    print(f"[PIPE] Done. {sentence_count} sentences. Response: {full_response[:80]}...")
    return full_response


# ─── Full Pipeline (WebSocket TTS) ──────────────────────────────────────────

async def run_pipeline_with_tools(user_text, conversation, tracker,
                                   audio_callback, tool_status_callback=None,
                                   voice="aura-asteria-en", session_id="default"):
    """
    Full pipeline with supervisor's optimizations:
      1. Transcript arrives → IMMEDIATELY ensure TTS WebSocket is open
      2. Run tool rounds (non-streaming)
      3. Stream final LLM response → WebSocket TTS → audio to client
    """
    tracker.reset()
    tracker.mark("t0_transcript")

    # ══════════════════════════════════════════════════════════════════
    # STEP 0: Open TTS WebSocket NOW (before LLM even starts)
    # This is the key insight from supervisor: "open as soon as
    # transcript is committed" — don't wait for LLM to finish.
    # ══════════════════════════════════════════════════════════════════
    ws_start = time.time()
    tts_ws = await get_tts_ws(session_id, voice)
    tracker.tts_ws_connect_ms = round((time.time() - ws_start) * 1000, 1)
    print(f"[PIPE] TTS WebSocket ready in {tracker.tts_ws_connect_ms}ms (reused={tracker.tts_ws_connect_ms < 10})")

    # STEP 1: Tool calling rounds
    tools_were_called = await run_tool_rounds(
        conversation, user_text, tracker, tool_status_callback
    )

    if not tools_were_called and conversation._direct_reply is not None:
        direct_text = conversation._direct_reply
        conversation.add_assistant(direct_text)

        if direct_text:
            SEND_THRESHOLD = 8000
            audio_buffer = bytearray()
            first_audio_sent = False

            async def on_audio(audio_bytes):
                nonlocal audio_buffer, first_audio_sent
                tracker.mark("t4_tts_first_audio")
                audio_buffer.extend(audio_bytes)

                if len(audio_buffer) >= SEND_THRESHOLD:
                    chunk = bytes(audio_buffer)
                    audio_buffer = bytearray()
                    if not first_audio_sent:
                        tracker.mark("t5_playback_start")
                        first_audio_sent = True
                    await audio_callback(chunk)

            async def on_flushed():
                nonlocal audio_buffer, first_audio_sent
                if audio_buffer:
                    chunk = bytes(audio_buffer)
                    audio_buffer = bytearray()
                    if not first_audio_sent:
                        tracker.mark("t5_playback_start")
                        first_audio_sent = True
                    await audio_callback(chunk)

            tts_ws.on_audio = on_audio
            tts_ws.on_flushed = on_flushed
            tracker.mark("t3_tts_first_text")
            await tts_ws.send_text(direct_text)
            await tts_ws.flush(timeout=15.0)
    else:
        # STEP 2: Stream LLM → TTS WebSocket
        await stream_llm_to_tts_ws(
            conversation, tracker, audio_callback, session_id, voice
        )

    report = tracker.report()
    print(f"[PIPE] Latency: {json.dumps(report)}")
    return report


# ─── REST TTS fallback (for /api/text endpoint) ─────────────────────────────

async def synthesize_speech_bytes(text, voice="aura-asteria-en", session=None):
    """REST TTS for text mode — kept as fallback."""
    if not session:
        session = await get_tts_session()

    url = f"{DEEPGRAM_TTS_URL}?model={voice}&encoding=linear16&sample_rate=16000&container=none"
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": "application/json"}
    body = {"text": text}

    try:
        async with session.post(url, headers=headers, json=body) as resp:
            if resp.status != 200:
                print(f"[TTS-REST] Error {resp.status}: {await resp.text()}")
                return b""
            audio = await resp.read()
            if audio[:4] == b'RIFF':
                audio = audio[44:]
            return audio
    except Exception as e:
        print(f"[TTS-REST] Error: {e}")
        return b""


# ─── Legacy pipelines (for /api/text) ───────────────────────────────────────

async def llm_with_tools(conversation, user_text, tracker, tool_status_callback=None):
    """Non-streaming LLM with tools. Returns full text response."""
    conversation.add_user(user_text)
    tracker.mark("t1_llm_request")

    client = get_llm_client()
    tools = registry.get_openai_tools()

    for round_num in range(MAX_TOOL_ROUNDS):
        response = await _call_llm(client, conversation.get_messages(), tools, stream=False)
        choice = response.choices[0]
        message = choice.message

        if round_num == 0:
            tracker.mark("t2_llm_first_token")

        if message.tool_calls:
            for tc in message.tool_calls:
                fn_name, fn_args_str, tc_id = tc.function.name, tc.function.arguments, tc.id
                conversation.add_tool_call(tc_id, fn_name, fn_args_str)
                try:
                    fn_args = json.loads(fn_args_str)
                except json.JSONDecodeError:
                    fn_args = {}
                result = await registry.execute(fn_name, fn_args)
                conversation.add_tool_result(tc_id, json.dumps({"success": result.success, "result": result.result, "error": result.error}))
            continue

        reply = message.content or ""
        conversation.add_assistant(reply)
        return reply

    fallback = "Done. Anything else?"
    conversation.add_assistant(fallback)
    return fallback


async def run_pipeline(user_text, conversation, tracker, voice="aura-asteria-en"):
    """REST pipeline for /api/text endpoint."""
    tracker.reset()
    tracker.mark("t0_transcript")

    response_text = await llm_with_tools(conversation, user_text, tracker)
    if not response_text:
        return

    tracker.mark("t3_tts_first_text")
    session = await get_tts_session()
    audio = await synthesize_speech_bytes(response_text, voice, session)
    if audio:
        tracker.mark("t4_tts_first_audio")
        tracker.mark("t5_playback_start")
        yield audio