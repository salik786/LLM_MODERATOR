# ============================================================
# LLM Moderator Server with Supabase Integration
# ============================================================
from __future__ import annotations

import os
import uuid
import logging
import time
import threading
import sys
from io import BytesIO
from typing import Dict, List, Any, Optional

from flask import Flask, request, send_file, jsonify, redirect
from flask_socketio import SocketIO, join_room, emit
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

# Optional audio support (disabled on Python 3.13+)
try:
    from pydub import AudioSegment
    AUDIO_SUPPORT = True
except ImportError:
    AUDIO_SUPPORT = False

# ============================================================
# Import Supabase Client
# ============================================================
from supabase_client import (
    get_or_create_room,
    get_room,
    update_room_status,
    update_story_progress,
    add_participant,
    get_participants,
    get_participant_by_socket,
    get_next_participant_name,
    add_message,
    get_chat_history,
    create_session,
    end_session,
)

# ============================================================
# Import Story System
# ============================================================
from data_retriever import (
    get_data,
    format_story_block,
    get_story_intro,
)

# ============================================================
# Import GPT Tools
# ============================================================
from prompts import (
    generate_moderator_reply,
    generate_passive_chunk,
    generate_gpt_nudge,
    get_random_ending,
    generate_engagement_response,
    should_advance_story,
)

# ============================================================
# Logger Setup
# ============================================================
DEBUG_LOG_FILE = "server_debug.log"

logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO for cleaner logs
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(DEBUG_LOG_FILE, mode="a", encoding="utf-8"),  # Append mode
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("LLM_MODERATOR")
logger.info("="*60)
logger.info("🚀 LLM Moderator Server Starting")
logger.info("="*60)

# ============================================================
# FFmpeg Configuration (for TTS/STT)
# ============================================================
if AUDIO_SUPPORT:
    try:
        ffmpeg_dir = r"C:\Users\shaima\AppData\Local\ffmpegio\ffmpeg-downloader\ffmpeg\bin"
        if os.path.exists(ffmpeg_dir):
            os.environ["PATH"] += os.pathsep + ffmpeg_dir
            AudioSegment.converter = os.path.join(ffmpeg_dir, "ffmpeg.exe")
            AudioSegment.ffprobe = os.path.join(ffmpeg_dir, "ffprobe.exe")
            logger.info("✅ FFmpeg configured")
    except Exception as e:
        logger.warning(f"⚠️ FFmpeg not configured: {e}")
else:
    logger.warning("⚠️ Audio support disabled (pydub not available)")

# ============================================================
# App Setup
# ============================================================
load_dotenv()

# Get frontend URL first (needed for CORS)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Allow both localhost (dev) and production frontend
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    FRONTEND_URL
]

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": allowed_origins}}, supports_credentials=True)

socketio = SocketIO(
    app,
    cors_allowed_origins=allowed_origins,
    async_mode="threading",
    logger=True,
    engineio_logger=True
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================================================
# Register Admin API Blueprint
# ============================================================
from admin_api import admin_bp, get_setting_value

app.register_blueprint(admin_bp)
logger.info("✅ Admin API registered at /admin")

# ============================================================
# Configuration - Load from Database
# ============================================================
logger.info("📝 Loading configuration from database...")

WELCOME_MESSAGE = get_setting_value("WELCOME_MESSAGE", "Welcome everyone! I'm the Moderator.")
ACTIVE_STORY_STEP = get_setting_value("ACTIVE_STORY_STEP", 1)
PASSIVE_STORY_STEP = get_setting_value("PASSIVE_STORY_STEP", 1)
PASSIVE_SILENCE_SECONDS = get_setting_value("PASSIVE_SILENCE_SECONDS", 10)
ACTIVE_SILENCE_SECONDS = get_setting_value("ACTIVE_SILENCE_SECONDS", 20)
STORY_CHUNK_INTERVAL = get_setting_value("STORY_CHUNK_INTERVAL", 10)
ACTIVE_INTERVENTION_WINDOW_SECONDS = get_setting_value("ACTIVE_INTERVENTION_WINDOW_SECONDS", 20)
PASSIVE_INTERVENTION_WINDOW_SECONDS = get_setting_value("PASSIVE_INTERVENTION_WINDOW_SECONDS", 10)

logger.info(f"📝 Config: Active Step={ACTIVE_STORY_STEP}, Passive Step={PASSIVE_STORY_STEP}")
logger.info(f"📝 Config: Story Interval={STORY_CHUNK_INTERVAL}s")
logger.info(f"📝 Frontend URL: {FRONTEND_URL}")

# ============================================================
# In-Memory Cache for Active Monitors
# ============================================================
active_monitors: Dict[str, threading.Thread] = {}
room_sessions: Dict[str, str] = {}  # room_id -> session_id

# ============================================================
# Helper: Get Room Story Data
# ============================================================
def get_room_story_data(room_id: str) -> Optional[Dict[str, Any]]:
    """Load story data for room"""
    room = get_room(room_id)
    if not room or not room.get('story_id'):
        logger.warning(f"⚠️ No story data for room {room_id}")
        return None

    return get_data(room['story_id'])

# ============================================================
# Helper: Start Story
# ============================================================
def start_story_for_room(room_id: str):
    """Start story for a room when conditions are met"""
    try:
        room = get_room(room_id)
        if not room:
            logger.error(f"❌ Room {room_id} not found")
            return

        participants = get_participants(room_id)
        student_count = len([p for p in participants if not p['is_moderator']])

        logger.info(f"📊 Room {room_id}: {student_count} students, status={room['status']}")

        # Check if we should start
        if room['status'] != 'waiting':
            logger.info(f"ℹ️ Room {room_id} already started (status={room['status']})")
            return

        if student_count < 1:  # Allow single user for testing
            logger.info(f"ℹ️ Room {room_id} waiting for participants (current: {student_count})")
            return

        logger.info(f"🎬 Starting story for room {room_id} with {student_count} students")

        # Update room status
        update_room_status(room_id, 'active')
        logger.info(f"✅ Room {room_id} status → active")

        # Create session
        session = create_session(
            room_id=room_id,
            mode=room['mode'],
            participant_count=student_count,
            story_id=room['story_id']
        )
        room_sessions[room_id] = session['id']
        logger.info(f"✅ Session created: {session['id']}")

        # Send story intro
        story_data = get_room_story_data(room_id)
        if story_data:
            intro = get_story_intro(story_data)
            logger.info(f"📖 Sending story intro to room {room_id}")

            add_message(
                room_id=room_id,
                sender_name="Moderator",
                message_text=intro,
                message_type="story"
            )

            socketio.emit(
                "receive_message",
                {"sender": "Moderator", "message": intro},
                room=room_id,
            )

            # Start appropriate mode
            if room['mode'] == 'passive':
                logger.info(f"🔄 Starting passive loop for room {room_id}")
                start_passive_loop(room_id)
            else:  # active mode
                logger.info(f"👁️ Starting silence monitor for room {room_id}")
                start_silence_monitor(room_id)
        else:
            logger.error(f"❌ No story data found for room {room_id}")

    except Exception as e:
        logger.error(f"❌ Error starting story for room {room_id}: {e}", exc_info=True)

# ============================================================
# Auto Room Assignment Endpoint
# ============================================================
@app.route("/join/<mode>")
def auto_join_room(mode: str):
    """Auto-assign user to available room or create new one"""
    logger.info(f"🔗 /join/{mode} - Auto-join request received")

    if mode not in ['active', 'passive']:
        logger.warning(f"⚠️ Invalid mode: {mode}")
        return jsonify({"error": "Invalid mode. Use 'active' or 'passive'"}), 400

    try:
        # Get random story
        story_data = get_data()
        story_id = story_data.get('story_id', 'default-story')
        logger.info(f"📚 Selected story: {story_id}")

        # Get or create room
        room = get_or_create_room(mode=mode, story_id=story_id)
        room_id = room['id']

        logger.info(f"✅ Room assigned: {room_id} (mode={mode}, participants={room['current_participants']})")

        return jsonify({
            "room_id": room_id,
            "mode": room['mode'],
            "redirect_url": f"{FRONTEND_URL}/chat/{room_id}"
        })

    except Exception as e:
        logger.error(f"❌ Error in auto_join_room: {e}", exc_info=True)
        return jsonify({"error": "Failed to assign room"}), 500

# ============================================================
# Get Room Info Endpoint
# ============================================================
@app.route("/api/room/<room_id>")
def get_room_info(room_id: str):
    """Get room information"""
    logger.info(f"ℹ️ Room info requested: {room_id}")

    try:
        room = get_room(room_id)
        if not room:
            logger.warning(f"⚠️ Room not found: {room_id}")
            return jsonify({"error": "Room not found"}), 404

        participants = get_participants(room_id)
        logger.info(f"✅ Room {room_id}: {len(participants)} participants")

        return jsonify({
            "room": room,
            "participants": participants,
            "participant_count": len(participants)
        })

    except Exception as e:
        logger.error(f"❌ Error getting room info: {e}", exc_info=True)
        return jsonify({"error": "Failed to get room info"}), 500

# ============================================================
# Passive Story Continuation
# ============================================================
def passive_continue_story(room_id: str):
    """Continue story in passive mode"""
    try:
        room = get_room(room_id)
        if not room or room['story_finished'] or room['mode'] != 'passive':
            return

        story_data = get_room_story_data(room_id)
        if not story_data:
            return

        sentences = story_data.get("sentences", [])
        total = len(sentences)

        start = room['story_progress']
        end = min(start + PASSIVE_STORY_STEP, total)

        next_chunk = " ".join(sentences[start:end])
        is_last = end >= total

        logger.info(f"📖 Passive story chunk {start}→{end}/{total} for room {room_id}")

        msg = generate_passive_chunk(next_chunk, is_last_chunk=is_last)

        add_message(
            room_id=room_id,
            sender_name="Moderator",
            message_text=msg,
            message_type="story",
            metadata={"story_progress": end, "is_last": is_last}
        )

        socketio.emit(
            "receive_message",
            {"sender": "Moderator", "message": msg},
            room=room_id,
        )

        update_story_progress(room_id, end, is_last)

        if is_last:
            logger.info(f"🏁 Story finished for room {room_id}")
            ending = get_random_ending()

            add_message(
                room_id=room_id,
                sender_name="Moderator",
                message_text=ending,
                message_type="system"
            )

            socketio.emit(
                "receive_message",
                {"sender": "Moderator", "message": ending},
                room=room_id,
            )

            end_session(room_id, metadata={"completion_type": "story_finished"})
            update_room_status(room_id, "completed")
            logger.info(f"✅ Session ended for room {room_id}")

    except Exception as e:
        logger.error(f"❌ Error in passive_continue_story: {e}", exc_info=True)

def start_passive_loop(room_id: str):
    """Start background task for passive story advancement"""
    def loop():
        logger.info(f"🔄 Passive loop started for room {room_id}")
        while True:
            room = get_room(room_id)
            if not room or room['story_finished'] or room['status'] == 'completed':
                logger.info(f"⏹️ Passive loop stopped for room {room_id}")
                break

            passive_continue_story(room_id)
            socketio.sleep(STORY_CHUNK_INTERVAL)

    socketio.start_background_task(loop)

# ============================================================
# Active Story Advancement
# ============================================================
def advance_story_chunk(room_id: str):
    """Advance story in active mode"""
    try:
        room = get_room(room_id)
        if not room or room['story_finished']:
            return

        story_data = get_room_story_data(room_id)
        if not story_data:
            return

        sentences = story_data.get("sentences", [])
        total = len(sentences)

        start = room['story_progress']
        end = min(start + ACTIVE_STORY_STEP, total)
        is_last = end >= total

        logger.info(f"📖 Active story chunk {start}→{end}/{total} for room {room_id}")

        context = " ".join(sentences[:end])

        participants = get_participants(room_id)
        student_names = [p['display_name'] for p in participants if not p['is_moderator']]

        history = get_chat_history(room_id)
        chat_history = [
            {"sender": msg['sender_name'], "message": msg['message_text']}
            for msg in history
        ]

        reply = generate_moderator_reply(
            student_names,
            chat_history,
            context,
            room['story_progress'],
            is_last_chunk=is_last,
        )

        add_message(
            room_id=room_id,
            sender_name="Moderator",
            message_text=reply,
            message_type="moderator",
            metadata={"story_progress": end, "is_last": is_last}
        )

        socketio.emit(
            "receive_message",
            {"sender": "Moderator", "message": reply},
            room=room_id,
        )

        update_story_progress(room_id, end, is_last)

        if is_last:
            logger.info(f"🏁 Story finished for room {room_id}")
            ending = os.getenv(
                "ACTIVE_ENDING_MESSAGE",
                "✨ We have reached the end of the story."
            )

            add_message(
                room_id=room_id,
                sender_name="Moderator",
                message_text=ending,
                message_type="system"
            )

            socketio.emit(
                "receive_message",
                {"sender": "Moderator", "message": ending},
                room=room_id,
            )

            end_session(room_id, metadata={"completion_type": "story_finished"})
            update_room_status(room_id, "completed")
            logger.info(f"✅ Session ended for room {room_id}")

    except Exception as e:
        logger.error(f"❌ Error in advance_story_chunk: {e}", exc_info=True)

# ============================================================
# Engagement Response (without advancing story)
# ============================================================
def send_engagement_response(room_id: str):
    """Send an engagement response (question/discussion) without advancing story"""
    try:
        room = get_room(room_id)
        if not room or room['story_finished']:
            return

        story_data = get_room_story_data(room_id)
        if not story_data:
            return

        sentences = story_data.get("sentences", [])
        current_progress = room['story_progress']

        # Get story context up to current point
        context = " ".join(sentences[:current_progress])

        participants = get_participants(room_id)
        student_names = [p['display_name'] for p in participants if not p['is_moderator']]

        history = get_chat_history(room_id)
        chat_history = [
            {"sender": msg['sender_name'], "message": msg['message_text']}
            for msg in history
        ]

        # Generate engagement response (question, not story advancement)
        response = generate_engagement_response(
            student_names,
            chat_history,
            context,
            current_progress
        )

        logger.info(f"💭 Engagement response for room {room_id}: {response[:50]}...")

        # Send engagement message
        add_message(
            room_id=room_id,
            sender_name="Moderator",
            message_text=response,
            message_type="moderator",
            metadata={"type": "engagement", "story_progress": current_progress}
        )

        socketio.emit(
            "receive_message",
            {"sender": "Moderator", "message": response},
            room=room_id,
        )

    except Exception as e:
        logger.error(f"❌ Error in send_engagement_response: {e}", exc_info=True)


# ============================================================
# Silence Monitor (Active Mode) - TWO-PHASE SYSTEM
# ============================================================
def start_silence_monitor(room_id: str):
    """Monitor silence and trigger intelligent interventions in active mode"""
    def loop():
        logger.info(f"👁️ Silence monitor started for room {room_id}")
        last_intervention = time.time()
        last_story_advance = time.time()

        while True:
            time.sleep(5)

            room = get_room(room_id)
            if not room or room['story_finished'] or room['status'] == 'completed':
                logger.info(f"⏹️ Silence monitor stopped for room {room_id}")
                break

            now = time.time()
            time_since_intervention = now - last_intervention
            time_since_advance = now - last_story_advance

            # Check if it's time to intervene (20 seconds of silence)
            if time_since_intervention >= ACTIVE_INTERVENTION_WINDOW_SECONDS:
                logger.info(f"🔔 Silence detected in room {room_id} ({time_since_intervention:.0f}s)")

                # PHASE 1: Check if story should advance
                history = get_chat_history(room_id)
                chat_history = [
                    {"sender": msg['sender_name'], "message": msg['message_text']}
                    for msg in history
                ]

                story_data = get_room_story_data(room_id)
                if story_data:
                    sentences = story_data.get("sentences", [])
                    current_progress = room['story_progress']
                    context = " ".join(sentences[:current_progress])

                    # Ask AI: should we advance or engage?
                    should_advance = should_advance_story(
                        chat_history,
                        context,
                        int(time_since_advance)
                    )

                    if should_advance:
                        # PHASE 2A: Advance the story
                        logger.info(f"📖 AI Decision: ADVANCE story in room {room_id}")
                        advance_story_chunk(room_id)
                        last_story_advance = now
                    else:
                        # PHASE 2B: Engage with questions/discussion
                        logger.info(f"💬 AI Decision: ENGAGE students in room {room_id}")
                        send_engagement_response(room_id)

                last_intervention = now

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    active_monitors[room_id] = thread

# ============================================================
# Socket.IO Events
# ============================================================
@socketio.on("connect")
def handle_connect():
    logger.info(f"🔌 Client connected: {request.sid}")

@socketio.on("disconnect")
def handle_disconnect():
    logger.info(f"🔌 Client disconnected: {request.sid}")

@socketio.on("create_room")
def create_room_handler(data):
    """Handle room creation"""
    user = data.get("user_name", "Student")
    mode = data.get("moderatorMode", "active")

    logger.info(f"🏗️ Creating room: user={user}, mode={mode}, sid={request.sid}")

    try:
        story_data = get_data()
        story_id = story_data.get('story_id', 'default-story')

        from supabase_client import create_room
        room = create_room(mode=mode, story_id=story_id)
        room_id = room['id']

        logger.info(f"✅ Room created: {room_id}")

        participant = add_participant(
            room_id=room_id,
            display_name=user,
            socket_id=request.sid,
            is_moderator=False
        )
        logger.info(f"✅ Participant added: {user} → room {room_id}")

        join_room(room_id)

        add_message(
            room_id=room_id,
            sender_name="Moderator",
            message_text=WELCOME_MESSAGE,
            message_type="system"
        )

        emit("joined_room", {"room_id": room_id}, to=request.sid)
        emit("room_created", {"room_id": room_id, "mode": mode}, to=request.sid)
        emit(
            "receive_message",
            {"sender": "Moderator", "message": WELCOME_MESSAGE},
            room=room_id,
        )

        # Try to start story
        start_story_for_room(room_id)

    except Exception as e:
        logger.error(f"❌ Error creating room: {e}", exc_info=True)
        emit("error", {"message": "Failed to create room"})

@socketio.on("join_room")
def join_room_handler(data):
    """Handle user joining existing room"""
    room_id = data.get("room_id")
    user_name = data.get("user_name")

    logger.info(f"🚪 Join room request: room={room_id}, user={user_name}, sid={request.sid}")

    try:
        room = get_room(room_id)
        if not room:
            logger.warning(f"⚠️ Room not found: {room_id}")
            emit("error", {"message": "Room not found"})
            return

        if not user_name:
            user_name = get_next_participant_name(room_id)
            logger.info(f"📝 Auto-generated name: {user_name}")

        participant = add_participant(
            room_id=room_id,
            display_name=user_name,
            socket_id=request.sid,
            is_moderator=False
        )
        logger.info(f"✅ Participant added: {user_name} → room {room_id}")

        join_room(room_id)

        history = get_chat_history(room_id)
        chat_history = [
            {
                "sender": msg['sender_name'],
                "message": msg['message_text'],
                "timestamp": msg['created_at']
            }
            for msg in history
        ]

        logger.info(f"📜 Sending {len(chat_history)} messages to {user_name}")

        emit("joined_room", {"room_id": room_id}, to=request.sid)
        emit("chat_history", {"chat_history": chat_history}, to=request.sid)

        # Try to start story
        start_story_for_room(room_id)

    except Exception as e:
        logger.error(f"❌ Error joining room: {e}", exc_info=True)
        emit("error", {"message": "Failed to join room"})

@socketio.on("send_message")
def send_message_handler(data):
    """Handle user message"""
    room_id = data.get("room_id")
    sender = data.get("sender")
    msg = (data.get("message") or "").strip()

    if not msg:
        return

    logger.info(f"💬 Message from {sender} in room {room_id}: {msg[:50]}...")

    try:
        room = get_room(room_id)
        if not room or room['story_finished']:
            logger.warning(f"⚠️ Cannot send message - room {room_id} finished or not found")
            return

        participant = get_participant_by_socket(request.sid)

        add_message(
            room_id=room_id,
            participant_id=participant['id'] if participant else None,
            sender_name=sender,
            message_text=msg,
            message_type="chat"
        )

        emit(
            "receive_message",
            {"sender": sender, "message": msg},
            room=room_id,
        )

        logger.info(f"✅ Message sent to room {room_id}")

    except Exception as e:
        logger.error(f"❌ Error sending message: {e}", exc_info=True)

# ============================================================
# TTS & STT Endpoints
# ============================================================
@app.route("/tts", methods=["POST"])
def tts():
    """Text-to-speech endpoint"""
    text = (request.json.get("text") or "").strip() or "Hello"
    logger.info(f"🔊 TTS request: {text[:30]}...")

    try:
        res = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
        )
        audio = res.read()
        logger.info(f"✅ TTS generated")
        return send_file(BytesIO(audio), mimetype="audio/mpeg")
    except Exception as e:
        logger.error(f"❌ TTS error: {e}")
        return {"error": str(e)}, 500

@app.route("/stt", methods=["POST"])
def stt():
    """Speech-to-text endpoint"""
    logger.info(f"🎤 STT request")

    if not AUDIO_SUPPORT:
        logger.warning(f"⚠️ STT not available - pydub not installed")
        return {"error": "STT not available (audio support disabled)"}, 503

    if "file" not in request.files:
        return {"error": "no file"}, 400

    try:
        f = request.files["file"]
        audio = AudioSegment.from_file(
            BytesIO(f.read()),
            format="webm",
        )

        temp_path = os.path.join(os.getcwd(), "temp.wav")
        audio.export(
            temp_path,
            format="wav",
            parameters=["-acodec", "pcm_s16le"],
        )

        with open(temp_path, "rb") as w:
            buf = BytesIO(w.read())
            buf.name = "recording.wav"

        res = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=buf,
        )

        logger.info(f"✅ STT result: {res.text[:50]}...")
        return {"text": res.text.strip()}

    except Exception as e:
        logger.error(f"❌ STT error: {e}")
        return {"error": str(e)}, 500

# ============================================================
# Server Start
# ============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info("="*60)
    logger.info("🚀 Starting Flask-SocketIO server")
    logger.info(f"📍 Host: 0.0.0.0:{port}")
    logger.info(f"🌐 Frontend: {FRONTEND_URL}")
    logger.info("="*60)
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
