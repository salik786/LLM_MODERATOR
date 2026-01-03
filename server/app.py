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
from pydub import AudioSegment

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
)

# ============================================================
# Logger Setup
# ============================================================
DEBUG_LOG_FILE = "server_debug.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(DEBUG_LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("SUPABASE_SERVER")
logger.info("🚀 Server with Supabase Integration Starting")

def dbg(*msg):
    logger.debug(" ".join(str(m) for m in msg))

# ============================================================
# FFmpeg Configuration (for TTS/STT)
# ============================================================
# Note: Update this path for your system if needed
try:
    ffmpeg_dir = r"C:\Users\shaima\AppData\Local\ffmpegio\ffmpeg-downloader\ffmpeg\bin"
    if os.path.exists(ffmpeg_dir):
        os.environ["PATH"] += os.pathsep + ffmpeg_dir
        AudioSegment.converter = os.path.join(ffmpeg_dir, "ffmpeg.exe")
        AudioSegment.ffprobe = os.path.join(ffmpeg_dir, "ffprobe.exe")
        dbg("FFmpeg configured")
except Exception as e:
    logger.warning(f"FFmpeg configuration skipped: {e}")

# ============================================================
# App Setup
# ============================================================
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================================================
# Configuration
# ============================================================
WELCOME_MESSAGE = os.getenv(
    "WELCOME_MESSAGE", "Welcome everyone! I'm the Moderator."
)

ACTIVE_STORY_STEP = int(os.getenv("ACTIVE_STORY_STEP", "1"))
PASSIVE_STORY_STEP = int(os.getenv("PASSIVE_STORY_STEP", "1"))

PASSIVE_SILENCE_SECONDS = int(os.getenv("PASSIVE_SILENCE_SECONDS", "10"))
ACTIVE_SILENCE_SECONDS = int(os.getenv("ACTIVE_SILENCE_SECONDS", "20"))

STORY_CHUNK_INTERVAL = int(os.getenv("STORY_CHUNK_INTERVAL", "10"))

ACTIVE_INTERVENTION_WINDOW_SECONDS = int(
    os.getenv(
        "ACTIVE_INTERVENTION_WINDOW_SECONDS",
        ACTIVE_SILENCE_SECONDS,
    )
)

PASSIVE_INTERVENTION_WINDOW_SECONDS = int(
    os.getenv(
        "PASSIVE_INTERVENTION_WINDOW_SECONDS",
        PASSIVE_SILENCE_SECONDS,
    )
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# ============================================================
# In-Memory Cache for Active Monitors
# (Database stores persistent data, this tracks runtime state)
# ============================================================
active_monitors: Dict[str, threading.Thread] = {}
room_sessions: Dict[str, str] = {}  # room_id -> session_id

# ============================================================
# Helper: Get Room Story Data
# ============================================================
def get_room_story_data(room_id: str) -> Optional[Dict[str, Any]]:
    """Load story data for room (cached in memory per room)"""
    room = get_room(room_id)
    if not room or not room.get('story_id'):
        return None

    # In production, you might cache this
    return get_data(room['story_id'])

# ============================================================
# Auto Room Assignment Endpoint
# ============================================================
@app.route("/join/<mode>")
def auto_join_room(mode: str):
    """
    Auto-assign user to available room or create new one.
    Returns room_id for frontend to use.
    """
    if mode not in ['active', 'passive']:
        return jsonify({"error": "Invalid mode. Use 'active' or 'passive'"}), 400

    try:
        # Get or create room with space
        story_data = get_data()  # Get random story
        story_id = story_data.get('story_id', 'default-story')

        room = get_or_create_room(mode=mode, story_id=story_id)

        logger.info(f"Auto-assigned to room {room['id']} (mode: {mode})")

        return jsonify({
            "room_id": room['id'],
            "mode": room['mode'],
            "redirect_url": f"{FRONTEND_URL}/chat/{room['id']}"
        })

    except Exception as e:
        logger.error(f"Error in auto_join_room: {e}")
        return jsonify({"error": "Failed to assign room"}), 500

# ============================================================
# Get Room Info Endpoint
# ============================================================
@app.route("/api/room/<room_id>")
def get_room_info(room_id: str):
    """Get room information"""
    try:
        room = get_room(room_id)
        if not room:
            return jsonify({"error": "Room not found"}), 404

        participants = get_participants(room_id)

        return jsonify({
            "room": room,
            "participants": participants,
            "participant_count": len(participants)
        })

    except Exception as e:
        logger.error(f"Error getting room info: {e}")
        return jsonify({"error": "Failed to get room info"}), 500

# ============================================================
# Passive Story Continuation
# ============================================================
def passive_continue_story(room_id: str):
    """Continue story in passive mode"""
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
    msg = generate_passive_chunk(next_chunk, is_last_chunk=is_last)

    # Store message in database
    add_message(
        room_id=room_id,
        sender_name="Moderator",
        message_text=msg,
        message_type="story",
        metadata={"story_progress": end, "is_last": is_last}
    )

    # Broadcast to room
    socketio.emit(
        "receive_message",
        {"sender": "Moderator", "message": msg},
        room=room_id,
    )

    # Update progress
    update_story_progress(room_id, end, is_last)

    if is_last:
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

        # End session
        end_session(room_id, metadata={"completion_type": "story_finished"})
        update_room_status(room_id, "completed")

def start_passive_loop(room_id: str):
    """Start background task for passive story advancement"""
    def loop():
        while True:
            room = get_room(room_id)
            if not room or room['story_finished'] or room['status'] == 'completed':
                break

            passive_continue_story(room_id)
            socketio.sleep(STORY_CHUNK_INTERVAL)

    socketio.start_background_task(loop)

# ============================================================
# Active Story Advancement
# ============================================================
def advance_story_chunk(room_id: str):
    """Advance story in active mode"""
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

    context = " ".join(sentences[:end])

    # Get participants for AI context
    participants = get_participants(room_id)
    student_names = [p['display_name'] for p in participants if not p['is_moderator']]

    # Get chat history
    history = get_chat_history(room_id)

    # Convert to format expected by prompts
    chat_history = [
        {"sender": msg['sender_name'], "message": msg['message_text']}
        for msg in history
    ]

    # Generate AI response
    reply = generate_moderator_reply(
        student_names,
        chat_history,
        context,
        room['story_progress'],
        is_last_chunk=is_last,
    )

    # Store message
    add_message(
        room_id=room_id,
        sender_name="Moderator",
        message_text=reply,
        message_type="moderator",
        metadata={"story_progress": end, "is_last": is_last}
    )

    # Broadcast
    socketio.emit(
        "receive_message",
        {"sender": "Moderator", "message": reply},
        room=room_id,
    )

    # Update progress
    update_story_progress(room_id, end, is_last)

    if is_last:
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

        # End session
        end_session(room_id, metadata={"completion_type": "story_finished"})
        update_room_status(room_id, "completed")

# ============================================================
# Silence Monitor (Active Mode)
# ============================================================
def start_silence_monitor(room_id: str):
    """Monitor silence and trigger interventions in active mode"""
    def loop():
        last_intervention = time.time()

        while True:
            time.sleep(5)

            room = get_room(room_id)
            if not room or room['story_finished'] or room['status'] == 'completed':
                break

            now = time.time()

            # Check if enough time has passed since last intervention
            if now - last_intervention >= ACTIVE_INTERVENTION_WINDOW_SECONDS:
                advance_story_chunk(room_id)
                last_intervention = now

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    active_monitors[room_id] = thread

# ============================================================
# Socket.IO Events
# ============================================================
@socketio.on("create_room")
def create_room_handler(data):
    """Handle room creation (legacy - now use /join/{mode})"""
    user = data.get("user_name", "Student")
    mode = data.get("moderatorMode", "active")

    try:
        # Create room
        story_data = get_data()
        story_id = story_data.get('story_id', 'default-story')

        from supabase_client import create_room
        room = create_room(mode=mode, story_id=story_id)
        room_id = room['id']

        # Add creator as participant
        participant = add_participant(
            room_id=room_id,
            display_name=user,
            socket_id=request.sid,
            is_moderator=False
        )

        join_room(room_id)

        # Send welcome message
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

        logger.info(f"Room created: {room_id} by {user}")

    except Exception as e:
        logger.error(f"Error creating room: {e}")
        emit("error", {"message": "Failed to create room"})

@socketio.on("join_room")
def join_room_handler(data):
    """Handle user joining existing room"""
    room_id = data.get("room_id")
    user_name = data.get("user_name")

    try:
        # Get room
        room = get_room(room_id)
        if not room:
            emit("error", {"message": "Room not found"})
            return

        # Generate name if not provided
        if not user_name:
            user_name = get_next_participant_name(room_id)

        # Add participant
        participant = add_participant(
            room_id=room_id,
            display_name=user_name,
            socket_id=request.sid,
            is_moderator=False
        )

        join_room(room_id)

        # Send chat history
        history = get_chat_history(room_id)

        # Convert to format expected by frontend
        chat_history = [
            {
                "sender": msg['sender_name'],
                "message": msg['message_text'],
                "timestamp": msg['created_at']
            }
            for msg in history
        ]

        emit("joined_room", {"room_id": room_id}, to=request.sid)
        emit("chat_history", {"chat_history": chat_history}, to=request.sid)

        # Check if we should start the story
        participants = get_participants(room_id)
        student_count = len([p for p in participants if not p['is_moderator']])

        if student_count >= 2 and room['status'] == 'waiting':
            # Update room status
            update_room_status(room_id, 'active')

            # Create session
            session = create_session(
                room_id=room_id,
                mode=room['mode'],
                participant_count=student_count,
                story_id=room['story_id']
            )
            room_sessions[room_id] = session['id']

            # Send story intro
            story_data = get_room_story_data(room_id)
            if story_data:
                intro = get_story_intro(story_data)
                add_message(
                    room_id=room_id,
                    sender_name="Moderator",
                    message_text=intro,
                    message_type="story"
                )
                emit(
                    "receive_message",
                    {"sender": "Moderator", "message": intro},
                    room=room_id,
                )

                # Start appropriate mode
                if room['mode'] == 'passive':
                    start_passive_loop(room_id)
                else:  # active mode
                    start_silence_monitor(room_id)

        logger.info(f"User {user_name} joined room {room_id}")

    except Exception as e:
        logger.error(f"Error joining room: {e}")
        emit("error", {"message": "Failed to join room"})

@socketio.on("send_message")
def send_message_handler(data):
    """Handle user message"""
    room_id = data.get("room_id")
    sender = data.get("sender")
    msg = (data.get("message") or "").strip()

    if not msg:
        return

    try:
        # Get room
        room = get_room(room_id)
        if not room or room['story_finished']:
            return

        # Get participant
        participant = get_participant_by_socket(request.sid)

        # Store message
        add_message(
            room_id=room_id,
            participant_id=participant['id'] if participant else None,
            sender_name=sender,
            message_text=msg,
            message_type="chat"
        )

        # Broadcast to room
        emit(
            "receive_message",
            {"sender": sender, "message": msg},
            room=room_id,
        )

        logger.debug(f"Message from {sender} in room {room_id}")

    except Exception as e:
        logger.error(f"Error sending message: {e}")

# ============================================================
# TTS Endpoint
# ============================================================
@app.route("/tts", methods=["POST"])
def tts():
    """Text-to-speech endpoint"""
    text = (request.json.get("text") or "").strip() or "Hello"

    try:
        res = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
        )
        audio = res.read()
        return send_file(BytesIO(audio), mimetype="audio/mpeg")
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return {"error": str(e)}, 500

# ============================================================
# STT Endpoint
# ============================================================
@app.route("/stt", methods=["POST"])
def stt():
    """Speech-to-text endpoint"""
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

        return {"text": res.text.strip()}

    except Exception as e:
        logger.error(f"STT error: {e}")
        return {"error": str(e)}, 500

# ============================================================
# Server Start
# ============================================================
if __name__ == "__main__":
    logger.info("🚀 LLM Moderator server with Supabase starting...")
    logger.info(f"Frontend URL: {FRONTEND_URL}")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
