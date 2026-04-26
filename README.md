# VoiceLens — AI Voice Memo Summariser
> Record a voice memo or call a phone number. VoiceLens transcribes it, extracts structured insights using Claude AI, and reads the summary back to you in a natural voice.
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi) ![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python) ![Deepgram](https://img.shields.io/badge/Deepgram-Nova--2-13EF93?style=flat-square) ![Claude](https://img.shields.io/badge/Anthropic-Claude-D97706?style=flat-square) ![ElevenLabs](https://img.shields.io/badge/ElevenLabs-TTS-8B5CF6?style=flat-square) ![Twilio](https://img.shields.io/badge/Twilio-Voice-F22F46?style=flat-square&logo=twilio)
---
## What It Does
VoiceLens is a full voice AI pipeline that turns raw audio into structured, actionable insight in seconds.
```
🎙 Audio Input  →  Deepgram Nova-2  →  Anthropic Claude  →  ElevenLabs TTS  →  ✅ Summary
```
Input options:
Upload an audio file directly via the web UI (mp3, wav, m4a, ogg, webm, flac)
Call a Twilio phone number and leave a voice memo
Output:
Full transcript with speaker diarisation
2-3 sentence summary
Extracted action items
Sentiment analysis (positive / neutral / negative)
Key topics
Audio readback of the summary via ElevenLabs
---
## Architecture
```
voice-memo-summariser/
├── backend/
│   ├── main.py                  # FastAPI app — all routes & webhooks
│   ├── services/
│   │   ├── transcriber.py       # Deepgram Nova-2 STT with diarisation
│   │   ├── summariser.py        # Claude AI — structured JSON extraction
│   │   ├── tts.py               # ElevenLabs neural TTS
│   │   └── twilio_handler.py    # TwiML builder + signature validation
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── index.html               # Single-file UI (HTML/CSS/JS)
└── tests/
    └── test_pipeline.py         # Unit + integration tests
```
---
## Quick Start
1. Clone the repo
```bash
git clone https://github.com/teejay-05/voice-memo-summariser
cd voice-memo-summariser/backend
```
2. Create a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python -m venv venv
source venv/bin/activate
```
3. Install dependencies
```bash
pip install fastapi uvicorn[standard] python-multipart httpx python-dotenv
```
4. Set up environment variables
```bash
cp .env.example .env
# Fill in your API keys in .env
```
5. Run the server
```bash
python -m uvicorn main:app --reload --port 8000
```
Open http://localhost:8000 — you're live. 🎉
---
## API Keys
All services have free tiers — total cost for a demo is ~£0-5.
Service	Purpose	Free tier	Sign up
Deepgram	Speech-to-text	$200 free credit	deepgram.com
Anthropic	Summarisation (Claude)	Pay-as-you-go, ~$0.01/call	console.anthropic.com
ElevenLabs	Text-to-speech	Free tier (paid for API)	elevenlabs.io
Twilio	Phone number + recording	Free trial + credit	twilio.com
Your `.env` file should look like this:
```env
DEEPGRAM_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here
TWILIO_ACCOUNT_SID=your_sid_here
TWILIO_AUTH_TOKEN=your_token_here
TWILIO_PHONE_NUMBER=+1234567890
BASE_URL=http://localhost:8000
```
---
## Twilio Phone Number Setup
To enable the phone number input feature:
1. Expose your local server with ngrok
```bash
pip install pyngrok
ngrok http 8000
# Copy the https://xxxx.ngrok.io URL
```
2. Configure your Twilio number
In the Twilio Console:
Go to Phone Numbers → Manage → Active Numbers
Click your number
Under Voice Configuration → A call comes in
Set to Webhook: `https://your-ngrok-url/api/twilio/incoming`
Method: `POST` → Save
3. Test it
Call your Twilio number → leave a memo after the beep → hang up. The pipeline runs automatically in the background.
---
## API Reference
`POST /api/summarise`
Upload an audio file for analysis.
Request: `multipart/form-data` with `file` field (audio/*)
Response:
```json
{
  "job_id": "uuid",
  "transcript": "Speaker 1: Hey, we need to finalise the proposal...",
  "summary": "The speaker discussed the Henderson project deadline and team coordination.",
  "action_items": [
    "Finalise proposal by Thursday",
    "Book meeting room for Friday at 2pm"
  ],
  "sentiment": "positive",
  "key_topics": ["project planning", "deadline", "team meeting"],
  "audio_url": "/api/audio/uuid_summary.mp3"
}
```
`GET /api/audio/{filename}`
Stream the ElevenLabs-generated summary audio.
`POST /api/twilio/incoming`
Twilio webhook — answers the call and starts recording.
`POST /api/twilio/recording`
Twilio webhook — receives the completed recording and runs the full pipeline.
`GET /api/health`
Health check.
```json
{ "status": "ok", "version": "1.0.0" }
```
`GET /docs`
Interactive API documentation (FastAPI Swagger UI).
---
## Running Tests
```bash
cd tests
pip install pytest pytest-asyncio
pytest test_pipeline.py -v
```
Tests cover:
Deepgram transcription (mocked + integration)
Claude summarisation with JSON validation
ElevenLabs TTS output
Twilio TwiML generation and signature validation
---
## Tech Stack
Layer	Technology	Why
Web framework	FastAPI	Async Python, automatic docs, fast
Speech-to-text	Deepgram Nova-2	Lower latency than Whisper, native diarisation
LLM	Anthropic Claude	Reliable structured JSON output
Text-to-speech	ElevenLabs	Most natural neural TTS available
Telephony	Twilio	Industry standard for voice/SMS
HTTP client	httpx	Async-native, production ready
---
## Design Decisions
Why Deepgram over Whisper?
Nova-2 has significantly lower latency and better accuracy on conversational audio, plus native speaker diarisation — all important for real-world voice memos.
Why structured JSON from Claude?
Prompting Claude to return strict JSON makes the output immediately consumable by the frontend and any downstream system without fragile string parsing.
Why async throughout?
All I/O (file upload, API calls to Deepgram/Claude/ElevenLabs) is async, so the server handles multiple concurrent requests without blocking.
Why a single-file frontend?
Zero build step, zero dependencies, instantly portable. The UI is served directly by FastAPI, making the project one-command to run.
---
🗺 What I'd Add Next
Database (PostgreSQL) to persist summaries and build a history view
User authentication so each user sees only their own memos
Twilio webhook dashboard to view and replay call recordings
Streaming responses so the UI updates in real time as each pipeline step completes
Export to Notion/Slack — send summaries directly to productivity tools
---
## Licence
MIT