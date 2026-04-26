"""
Voice Memo Summariser — FastAPI Backend
Stack: Twilio → Deepgram → Claude → ElevenLabs
"""

import os
import uuid
import httpx
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from services.transcriber import transcribe_audio
from services.summariser import summarise_transcript
from services.tts import speak_summary
from services.twilio_handler import build_twiml_response

from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# DEBUG - remove later
import os
print("DEEPGRAM KEY:", os.getenv("DEEPGRAM_API_KEY"))

app = FastAPI(title="Voice Memo Summariser", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Serve frontend
app.mount("/static", StaticFiles(directory="../frontend"), name="static")


@app.get("/")
async def root():
    return FileResponse("../frontend/index.html")


@app.post("/api/summarise")
async def summarise_upload(file: UploadFile = File(...)):
    """
    Accept an audio file upload, transcribe it, summarise it, and return
    a structured JSON response with an ElevenLabs audio summary.
    """
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file.")

    job_id = str(uuid.uuid4())
    audio_path = UPLOAD_DIR / f"{job_id}_{file.filename}"

    # Save uploaded file
    with open(audio_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        # Step 1: Transcribe
        transcript = await transcribe_audio(str(audio_path))

        # Step 2: Summarise with Claude
        summary_data = await summarise_transcript(transcript)

        # Step 3: ElevenLabs TTS on the summary
        audio_filename = f"{job_id}_summary.mp3"
        audio_output_path = OUTPUT_DIR / audio_filename
        await speak_summary(summary_data["summary"], str(audio_output_path))

        return JSONResponse({
            "job_id": job_id,
            "transcript": transcript,
            "summary": summary_data["summary"],
            "action_items": summary_data["action_items"],
            "sentiment": summary_data["sentiment"],
            "key_topics": summary_data["key_topics"],
            "audio_url": f"/api/audio/{audio_filename}",
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up uploaded file
        if audio_path.exists():
            audio_path.unlink()


@app.get("/api/audio/{filename}")
async def get_audio(filename: str):
    """Serve generated summary audio files."""
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return FileResponse(str(path), media_type="audio/mpeg")


@app.post("/api/twilio/incoming")
async def twilio_incoming(request: Request):
    """
    Twilio webhook — called when someone dials your Twilio number.
    Instructs Twilio to record the call.
    """
    return build_twiml_response(
        message="Hello! Please leave your voice memo after the beep. Press any key or hang up when done.",
        record=True,
        recording_callback="/api/twilio/recording",
    )


@app.post("/api/twilio/recording")
async def twilio_recording(request: Request, background_tasks: BackgroundTasks):
    """
    Twilio webhook — called when a recording is ready.
    Downloads the recording and processes it.
    """
    form = await request.form()
    recording_url = form.get("RecordingUrl")
    recording_sid = form.get("RecordingSid")

    if not recording_url:
        raise HTTPException(status_code=400, detail="No recording URL received.")

    # Process in background so Twilio doesn't time out
    background_tasks.add_task(process_twilio_recording, recording_url, recording_sid)

    return JSONResponse({"status": "processing", "recording_sid": recording_sid})


async def process_twilio_recording(recording_url: str, recording_sid: str):
    """Download Twilio recording and run the full pipeline."""
    twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    audio_path = UPLOAD_DIR / f"{recording_sid}.wav"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{recording_url}.wav",
            auth=(twilio_account_sid, twilio_auth_token),
        )
        with open(audio_path, "wb") as f:
            f.write(response.content)

    transcript = await transcribe_audio(str(audio_path))
    summary_data = await summarise_transcript(transcript)
    audio_output_path = OUTPUT_DIR / f"{recording_sid}_summary.mp3"
    await speak_summary(summary_data["summary"], str(audio_output_path))

    if audio_path.exists():
        audio_path.unlink()

    print(f"✅ Processed Twilio recording {recording_sid}")
    print(f"   Summary: {summary_data['summary'][:100]}...")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
