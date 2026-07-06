"""
Voice Assistant Web Server - FastAPI + WebSocket
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
import base64
from typing import Dict, Set
from contextlib import asynccontextmanager

from src.voice_assistant.assistant import VoiceAssistant, VoiceConfig, AssistantState, EngineFactory
from src.voice_assistant.integration import create_voice_assistant_integration
from src.voice_assistant.audio import AudioManager, AudioConfig
from src.cognition.cognitive_bus import get_cognitive_bus
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# Global instances
voice_assistant: VoiceAssistant = None
integration = None
audio_manager: AudioManager | None = None
connected_clients: Set[WebSocket] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    global voice_assistant, integration, audio_manager, connected_clients

    settings = get_settings()

    # Initialize integration (all cognitive modules)
    logger.info("Initializing cognitive integration...")
    integration = await create_voice_assistant_integration(settings)

    # Initialize STT using Python whisper package (no binary needed)
    stt = EngineFactory.create_stt("faster-whisper", model_size="base")

    # Initialize TTS using edge-tts (no binary needed, high quality female voices)
    tts = EngineFactory.create_tts("edge-tts", voice="en-US-AriaNeural")

    # Initialize Audio Manager
    audio_config = AudioConfig(sample_rate=16000, channels=1, chunk_size=1024)
    audio_manager = AudioManager(audio_config)

    # Initialize Voice Assistant
    voice_config = VoiceConfig(
        sample_rate=16000, channels=1, chunk_size=1024, vad_threshold=0.01, silence_duration=1.5
    )

    cognitive_bus = get_cognitive_bus()
    llm_client = integration._get_llm_client()

    voice_assistant = VoiceAssistant(
        config=voice_config,
        stt_engine=stt,
        tts_engine=tts,
        cognitive_bus=cognitive_bus,
        llm_client=llm_client,
    )

    # Set up callbacks for UI updates
    async def on_transcript(text: str):
        await broadcast({"type": "transcript", "text": text})

    async def on_response(text: str):
        await broadcast({"type": "response", "text": text})

    async def on_state_change(state: AssistantState):
        await broadcast({"type": "state", "state": state.value})

    voice_assistant.on_transcript = on_transcript
    voice_assistant.on_response = on_response
    voice_assistant.on_state_change = on_state_change

    await voice_assistant.start_listening()
    logger.info("Voice Assistant ready!")

    yield

    # Shutdown
    logger.info("Shutting down...")
    if voice_assistant:
        await voice_assistant.stop()
    if integration:
        await integration.shutdown()
    await broadcast({"type": "shutdown"})


app = FastAPI(title="Voice Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def broadcast(message: dict):
    """Broadcast message to all connected WebSocket clients"""
    global connected_clients
    disconnected = set()
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.add(client)
    connected_clients -= disconnected


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time voice communication"""
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info(f"Client connected. Total: {len(connected_clients)}")

    try:
        # Send initial state
        await websocket.send_json(
            {
                "type": "init",
                "state": voice_assistant.state.value if voice_assistant else "initializing",
            }
        )

        while True:
            data = await websocket.receive()

            if "bytes" in data:
                # Audio chunk from client
                audio_bytes = data["bytes"]
                await voice_assistant.process_audio_chunk(audio_bytes)

            elif "text" in data:
                # Text message (commands, etc.)
                msg = json.loads(data["text"])
                await handle_text_message(msg, websocket)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connected_clients.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(connected_clients)}")


async def handle_text_message(msg: dict, websocket: WebSocket):
    """Handle text messages from client"""
    msg_type = msg.get("type")

    if msg_type == "text_input":
        # Direct text input (bypass voice)
        text = msg.get("text", "")
        if text:
            response = await integration.process_user_input(text)
            await websocket.send_json({"type": "response", "text": response})

    elif msg_type == "get_status":
        await websocket.send_json(
            {
                "type": "status",
                "state": voice_assistant.state.value,
                "tools": list(integration._tools.keys()),
                "active_plan": integration.context.active_plan_id,
            }
        )

    elif msg_type == "list_devices":
        devices = audio_manager.list_devices() if audio_manager else []
        await websocket.send_json({"type": "devices", "devices": devices})


@app.get("/")
async def root():
    """Serve the main UI"""
    return FileResponse("src/voice_assistant/ui/index.html")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "assistant_state": voice_assistant.state.value if voice_assistant else "not_ready",
    }


# Audio streaming endpoint for direct HTTP streaming
@app.post("/api/tts")
async def tts_endpoint(request: Request):
    """Generate TTS for given text"""
    data = await request.json()
    text = data.get("text", "")
    if not text:
        return {"error": "No text provided"}

    audio = await voice_assistant.tts.synthesize(text)
    if not audio:
        return {"error": "TTS failed"}

    # Return base64 encoded audio
    return {"audio": base64.b64encode(audio).decode()}


@app.post("/api/stt")
async def stt_endpoint(request: Request):
    """Transcribe audio"""
    data = await request.json()
    audio_b64 = data.get("audio", "")
    if not audio_b64:
        return {"error": "No audio provided"}

    audio_bytes = base64.b64decode(audio_b64)
    text = await voice_assistant.stt.transcribe(audio_bytes)

    return {"text": text}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
