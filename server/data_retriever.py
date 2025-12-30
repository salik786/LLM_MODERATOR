# ============================================================
# 📦 data_retriever.py — Unified Story Loader (v5.0)
# ============================================================
from __future__ import annotations
import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger("moderator-data")

# ============================================================
# 🆕 ADDITION — Force new story flag
# ============================================================
# True  → always build a new story (no repetition)
# False → allow cached story reuse
FORCE_NEW_STORY = True

# ============================================================
# 🔍 Try Import: GPT Story Constructor (if available)
# ============================================================
_STORY_CONSTRUCTOR = None

try:
    from story_constructor import build_story_block
    _STORY_CONSTRUCTOR = build_story_block
    logger.info("[Story] GPT story_constructor detected and will be used.")
except Exception as e:
    logger.warning(f"[Story] story_constructor not found, will use fallback. {e}")
    _STORY_CONSTRUCTOR = None

# ============================================================
# 🧩 Fallback Story
# ============================================================
_FALLBACK = {
    "story_name": "The Lantern and the Little Dragon",
    "context": (
        "On the edge of a misty village, a paper lantern flickered to life each dusk. "
        "One evening, a tiny dragon curled around its handle, sneezing sparks that "
        "drew curious eyes. The villagers, once afraid, learned the dragon was "
        "lonely, not dangerous. They left bowls of rice outside their doors to keep "
        "its flame warm."
    ),
    "story_text": (
        "On the edge of a misty village stood a flickering lantern. One night, a tiny "
        "dragon wrapped around it, sneezing sparks. The villagers discovered it was "
        "lonely, not dangerous, so they fed it warm rice. Over time, the dragon "
        "became their quiet guardian, lighting paths at night. The village grew safe "
        "and peaceful as its golden flame glowed."
    ),
    "sentences": [
        "On the edge of a misty village stood a flickering lantern.",
        "One night, a tiny dragon wrapped around it, sneezing sparks.",
        "The villagers discovered it was lonely, not dangerous.",
        "They fed it warm rice.",
        "The dragon became their quiet guardian, lighting paths at night.",
        "Its golden flame kept the village peaceful."
    ]
}

# ============================================================
# 📘 Story File Cache Directory
# ============================================================
STORY_CACHE_DIR = os.path.join(os.getcwd(), "stories")
os.makedirs(STORY_CACHE_DIR, exist_ok=True)

# ============================================================
# 📜 Save Story Block Locally
# ============================================================
def save_story_to_file(story: Dict[str, Any]) -> str:
    try:
        name = story.get("story_name", "UnknownStory").replace(" ", "_")
        file_path = os.path.join(STORY_CACHE_DIR, f"{name}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(story, f, ensure_ascii=False, indent=2)
        logger.info(f"[Story] Saved new story → {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"[Story] Could not save story: {e}")
        return ""

# ============================================================
# 📂 Load Cached Story
# ============================================================
def load_cached_story() -> Dict[str, Any] | None:
    try:
        files = [f for f in os.listdir(STORY_CACHE_DIR) if f.endswith(".json")]
        if not files:
            return None
        files.sort(
            key=lambda x: os.path.getmtime(os.path.join(STORY_CACHE_DIR, x)),
            reverse=True
        )
        latest_file = os.path.join(STORY_CACHE_DIR, files[0])
        with open(latest_file, "r", encoding="utf-8") as f:
            story = json.load(f)
        logger.info(f"[Story] Loaded cached story → {latest_file}")
        return story
    except Exception as e:
        logger.warning(f"[Story] Could not load cached story: {e}")
        return None

# ============================================================
# 🎭 Main Entry — Get Story Block
# ============================================================
def get_data() -> Dict[str, Any]:

    # ========================================================
    # 🆕 ADDITION — optionally bypass cache
    # ========================================================
    if not FORCE_NEW_STORY:
        cached = load_cached_story()
        if cached:
            return cached

    if _STORY_CONSTRUCTOR:
        try:
            story_block = _STORY_CONSTRUCTOR()
            save_story_to_file(story_block)
            return story_block
        except Exception as e:
            logger.error(f"[Story] GPT constructor failed: {e}")

    logger.warning("[Story] Using fallback story.")
    save_story_to_file(_FALLBACK)
    return dict(_FALLBACK)

# ============================================================
# 🪄 Generate Story Intro
# ============================================================
def get_story_intro(story_block: dict) -> str:
    text = story_block.get("story_text", "").strip()
    if not text:
        return "Let’s begin our story."
    return text.split(".")[0].strip() + "."

# ============================================================
# 🧱 Format Story Block (for debug)
# ============================================================
def format_story_block(story_block: dict, full: bool = False) -> str:
    name = story_block.get("story_name", "Unknown Story")
    story_text = story_block.get("story_text", "")
    context = story_block.get("context", "")
    sentences = story_block.get("sentences", [])

    if not full:
        return f"Story: {name}\n\n{context}"

    return (
        f"Story: {name}\n\n"
        f"{context}\n\n"
        f"Full text:\n{story_text}\n\n"
        f"Sentences ({len(sentences)}):\n"
        + "\n".join(f"- {s}" for s in sentences)
    )
