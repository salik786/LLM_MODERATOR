# ============================================================
# 🔥🔥🔥  ULTRA DEBUG EDITION (No deletions, only additions)
# ============================================================
from __future__ import annotations

import os
import uuid
import logging
import time
import re
import threading
import sys
import traceback
from io import BytesIO
from typing import Dict, List, Any

from flask import Flask, request, send_file
from flask_socketio import SocketIO, join_room, emit
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
from pydub import AudioSegment

# ============================================================
# 💠 Import Unified Story System
# ============================================================
from data_retriever import (
    get_data,
    format_story_block,
    get_story_intro,
)

# ============================================================
# 💠 Import GPT Tools
# ============================================================
from prompts import (
    generate_moderator_reply,
    generate_passive_chunk,
    generate_gpt_nudge,
    classify_reply_semantic,
    llm,
    get_random_ending,
)

# ============================================================
# 🔵 ULTRA DEBUG LOGGER SETUP
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

logger = logging.getLogger("ULTRA_DEBUG_SERVER")
logger.info("🚀 Ultra Debug Logging Enabled")

def dbg(*msg):
    logger.debug(" ".join(str(m) for m in msg))

def room_log(room_id, *msg):
    with open(f"room-{room_id}.log", "a", encoding="utf-8") as f:
        f.write(
            time.strftime("[%Y-%m-%d %H:%M:%S] ")
            + " ".join(str(m) for m in msg)
            + "\n"
        )
    dbg(f"[ROOM {room_id}]", *msg)

# ============================================================
# 🎧 Force FFmpeg
# ============================================================
ffmpeg_dir = r"C:\Users\shaima\AppData\Local\ffmpegio\ffmpeg-downloader\ffmpeg\bin"
os.environ["PATH"] += os.pathsep + ffmpeg_dir

AudioSegment.converter = os.path.join(ffmpeg_dir, "ffmpeg.exe")
AudioSegment.ffprobe = os.path.join(ffmpeg_dir, "ffprobe.exe")

dbg("FFmpeg linked →", AudioSegment.converter, AudioSegment.ffprobe)

# ============================================================
# 🔧 App Setup
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
# 🔧 Configuration (NO REMOVALS)
# ============================================================
WELCOME_MESSAGE = os.getenv(
    "WELCOME_MESSAGE", "Welcome everyone! I’m the Moderator."
)

ACTIVE_STORY_STEP = int(os.getenv("ACTIVE_STORY_STEP", "1"))
PASSIVE_STORY_STEP = int(os.getenv("PASSIVE_STORY_STEP", "1"))

PASSIVE_SILENCE_SECONDS = int(os.getenv("PASSIVE_SILENCE_SECONDS", "10"))
ACTIVE_SILENCE_SECONDS = int(os.getenv("ACTIVE_SILENCE_SECONDS", "20"))

STORY_CHUNK_INTERVAL = int(os.getenv("STORY_CHUNK_INTERVAL", "10"))

# ============================================================
# 🔧 NEW — Intervention Windows (Added, not replacing)
# ============================================================
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

dbg("[Config] ACTIVE_INTERVENTION_WINDOW_SECONDS =", ACTIVE_INTERVENTION_WINDOW_SECONDS)
dbg("[Config] PASSIVE_INTERVENTION_WINDOW_SECONDS =", PASSIVE_INTERVENTION_WINDOW_SECONDS)
dbg("[Config] STORY_CHUNK_INTERVAL =", STORY_CHUNK_INTERVAL)

# ============================================================
# 🧩 Room Class
# ============================================================
class Room:
    def __init__(self, rid: str, creator: str, sid: str, active: bool = True):
        dbg(
            "[Room Init]",
            "ID=", rid,
            "Creator=", creator,
            "SID=", sid,
            "Active=", active,
        )
        self.id = rid
        self.participants: Dict[str, str] = {creator: sid}
        self.chat_history: List[Dict[str, Any]] = []
        self.last_active: Dict[str, float] = {}

        self.story_data: Dict[str, Any] | None = None
        self.story_started: bool = False
        self.story_progress: int = 0
        self.story_finished: bool = False

        self.active_moderator: bool = active

        self.silence_timer = None
        self.nudge_counter: int = 0

        self.created_at = time.time()
        self.last_story_advance = time.time()

    def add_msg(self, sender: str, msg: str):
        dbg(f"[Room {self.id}] add_msg sender={sender}")
        room_log(self.id, "ADD_MSG", sender, msg[:100])

        self.chat_history.append(
            {
                "sender": sender,
                "message": msg,
                "timestamp": time.time(),
            }
        )

        self.last_active[sender.lower()] = time.time()

    @property
    def student_names(self) -> List[str]:
        return [
            n
            for n in self.participants.keys()
            if n.lower() != "moderator"
        ]

# ============================================================
# 🧩 Rooms Registry
# ============================================================
rooms: Dict[str, Room] = {}

# ============================================================
# 🛑 ADDITION — HARD STORY STOP GUARD (NEW)
# ============================================================
def is_story_dead(room: Room) -> bool:
    return room.story_finished is True

# ============================================================
# 🧩 Safe Room Getter
# ============================================================
def require_room(rid: str, retries: int = 3, delay: float = 0.5) -> Room:
    dbg("[require_room] Looking for room", rid)
    for _ in range(retries):
        if rid in rooms:
            return rooms[rid]
        time.sleep(delay)
    raise KeyError(f"Room not found: {rid}")

# ============================================================
# 🔁 Passive Story Continuation
# ============================================================
def passive_continue_story(room: Room):
    if room.story_finished or room.active_moderator:
        return

    sentences = room.story_data["sentences"]
    total = len(sentences)

    start = room.story_progress
    end = min(start + PASSIVE_STORY_STEP, total)

    next_chunk = " ".join(sentences[start:end])

    is_last = end >= total
    msg = generate_passive_chunk(next_chunk, is_last_chunk=is_last)

    room.add_msg("Moderator", msg)
    socketio.emit(
        "receive_message",
        {"sender": "Moderator", "message": msg},
        room=room.id,
    )

    room.story_progress = end

    if is_last:
        room.story_finished = True
        ending = get_random_ending()
        room.add_msg("Moderator", ending)
        socketio.emit(
            "receive_message",
            {"sender": "Moderator", "message": ending},
            room=room.id,
        )

def start_passive_loop(room: Room):
    def loop():
        while not room.story_finished:
            passive_continue_story(room)
            socketio.sleep(STORY_CHUNK_INTERVAL)
    socketio.start_background_task(loop)

# ============================================================
# ⚡ Active Story Advancement (SINGLE MODERATOR MESSAGE)
# ============================================================
def advance_story_chunk(room: Room):

    # 🛑 ADDITION — HARD STOP
    if is_story_dead(room):
        return

    sentences = room.story_data["sentences"]
    total = len(sentences)

    start = room.story_progress
    end = min(start + ACTIVE_STORY_STEP, total)
    is_last = end >= total

    context = " ".join(sentences[:end])

    reply = generate_moderator_reply(
        room.student_names,
        room.chat_history,
        context,
        room.story_progress,
        is_last_chunk=is_last,
    )

    room.add_msg("Moderator", reply)
    socketio.emit(
        "receive_message",
        {"sender": "Moderator", "message": reply},
        room=room.id,
    )

    room.story_progress = end

    # 🏁 ADDITION — FINAL ENDING LOCK
    if is_last:
        room.story_finished = True
        ending = os.getenv(
            "ACTIVE_ENDING_MESSAGE",
            "✨ We have reached the end of the story."
        )
        room.add_msg("Moderator", ending)
        socketio.emit(
            "receive_message",
            {"sender": "Moderator", "message": ending},
            room=room.id,
        )
        return  # 🛑 STOP FOREVER

# ============================================================
# 🔕 Silence Monitor (ACTIVE only → routes to advance_story_chunk)
# ============================================================
def start_silence_monitor(room: Room):
    def loop():
        while True:
            time.sleep(5)

            # 🛑 ADDITION — STOP MONITOR IF STORY ENDED
            if is_story_dead(room):
                break

            now = time.time()

            student_times = [
                t
                for name, t in room.last_active.items()
                if name != "moderator"
            ]

            if not student_times:
                continue

            silence = now - max(student_times)

            if silence >= ACTIVE_INTERVENTION_WINDOW_SECONDS:
                advance_story_chunk(room)

                # 🔁 ADDITION — RESET INTERVAL WINDOW
                for k in room.last_active:
                    room.last_active[k] = time.time()

    socketio.start_background_task(loop)

# ============================================================
# 🎛 Socket Events
# ============================================================
@socketio.on("create_room")
def create_room(data):
    user = data.get("user_name")
    mode = data.get("moderatorMode", "active")
    active = mode == "active"

    rid = str(uuid.uuid4())
    room = Room(rid, user, request.sid, active=active)
    rooms[rid] = room

    join_room(rid)

    room.story_data = get_data()
    room.add_msg("Moderator", WELCOME_MESSAGE)

    emit("joined_room", {"room_id": rid}, to=request.sid)
    emit("room_created", {"room_id": rid, "mode": mode}, to=request.sid)
    emit(
        "receive_message",
        {"sender": "Moderator", "message": WELCOME_MESSAGE},
        room=rid,
    )

    if active:
        start_silence_monitor(room)

@socketio.on("join_room")
def join_room_event(data):
    rid = data.get("room_id")
    user = data.get("user_name")

    room = require_room(rid)
    room.participants[user] = request.sid
    join_room(rid)

    emit("joined_room", {"room_id": rid}, room=request.sid)
    emit(
        "chat_history",
        {"chat_history": room.chat_history},
        to=request.sid,
    )

    if len(room.student_names) >= 2 and not room.story_started:
        room.story_started = True
        intro = get_story_intro(room.story_data)
        room.add_msg("Moderator", intro)
        emit(
            "receive_message",
            {"sender": "Moderator", "message": intro},
            room=rid,
        )

        if not room.active_moderator:
            start_passive_loop(room)

# ============================================================
# 💬 SEND MESSAGE
# ============================================================
@socketio.on("send_message")
def send_message(data):
    rid = data.get("room_id")
    sender = data.get("sender")
    msg = (data.get("message") or "").strip()

    room = require_room(rid)

    # 🛑 ADDITION — IGNORE ALL AFTER END
    if is_story_dead(room):
        return

    room.add_msg(sender, msg)

    emit(
        "receive_message",
        {"sender": sender, "message": msg},
        room=rid,
    )

    # ❌ no moderator reply here (interval only)

# ============================================================
# 🔊 TTS
# ============================================================
@app.route("/tts", methods=["POST"])
def tts():
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
        dbg("[TTS ERROR]", e)
        return {"error": str(e)}, 500

# ============================================================
# 🎙️ STT
# ============================================================
@app.route("/stt", methods=["POST"])
def stt():
    if "file" not in request.files:
        return {"error": "no file"}, 400

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

# ============================================================
# 🚀 Server Start
# ============================================================
if __name__ == "__main__":
    dbg("🚀 Moderator server running (Ultra Debug Mode — FINAL)")
    socketio.run(app, host="0.0.0.0", port=5000)