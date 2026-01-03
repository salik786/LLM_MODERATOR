# ============================================================
# 📦 data_retriever.py — Local Story Loader
# ============================================================
from __future__ import annotations
import os
import json
import random
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("moderator-data")

# ============================================================
# 📘 Story File Cache Directory
# ============================================================
STORY_CACHE_DIR = os.path.join(os.getcwd(), "stories")
os.makedirs(STORY_CACHE_DIR, exist_ok=True)

# ============================================================
# 🧩 Fallback Story
# ============================================================
_FALLBACK = {
    "story_id": "fallback-lantern",
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
# 📂 Load Random Story from Local Files
# ============================================================
def get_data(story_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Load a story from local JSON files.

    Args:
        story_id: Optional specific story ID to load. If None, loads random story.

    Returns:
        Story dict with story_id, story_name, sentences, etc.
    """
    try:
        # Get all JSON files in stories directory
        files = [f for f in os.listdir(STORY_CACHE_DIR) if f.endswith(".json")]

        if not files:
            logger.warning("[Story] No cached stories found, using fallback")
            return dict(_FALLBACK)

        # If specific story requested, try to find it
        if story_id:
            matching_file = None
            for f in files:
                file_path = os.path.join(STORY_CACHE_DIR, f)
                try:
                    with open(file_path, "r", encoding="utf-8") as fp:
                        story = json.load(fp)
                        if story.get("story_id") == story_id or f.replace(".json", "") == story_id:
                            matching_file = file_path
                            break
                except:
                    continue

            if matching_file:
                with open(matching_file, "r", encoding="utf-8") as fp:
                    story = json.load(fp)
                logger.info(f"[Story] Loaded specific story: {story.get('story_id', story.get('story_name'))}")
                return story
            else:
                logger.warning(f"[Story] Story {story_id} not found, loading random")

        # Load random story
        random_file = random.choice(files)
        file_path = os.path.join(STORY_CACHE_DIR, random_file)

        with open(file_path, "r", encoding="utf-8") as fp:
            story = json.load(fp)

        # Ensure story_id exists
        if "story_id" not in story:
            story["story_id"] = random_file.replace(".json", "")

        logger.info(f"[Story] Loaded random story: {story.get('story_id', story.get('story_name'))} from {random_file}")
        return story

    except Exception as e:
        logger.error(f"[Story] Error loading story: {e}", exc_info=True)
        logger.warning("[Story] Using fallback story")
        return dict(_FALLBACK)

# ============================================================
# 🪄 Generate Story Intro
# ============================================================
def get_story_intro(story_block: dict) -> str:
    """Generate introduction text from story block"""
    story_name = story_block.get("story_name", "our story")
    context = story_block.get("context", "").strip()

    if context:
        # Use first sentence of context
        first_sentence = context.split(".")[0].strip() + "."
        return f"Welcome to '{story_name}'. {first_sentence}"

    story_text = story_block.get("story_text", "").strip()
    if story_text:
        first_sentence = story_text.split(".")[0].strip() + "."
        return f"Let's begin '{story_name}'. {first_sentence}"

    return f"Let's begin our story: {story_name}."

# ============================================================
# 🧱 Format Story Block (for debug)
# ============================================================
def format_story_block(story_block: dict, full: bool = False) -> str:
    """Format story block for display"""
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

# ============================================================
# 📋 List Available Stories
# ============================================================
def list_available_stories() -> list[str]:
    """List all available story IDs"""
    try:
        files = [f.replace(".json", "") for f in os.listdir(STORY_CACHE_DIR) if f.endswith(".json")]
        return sorted(files)
    except Exception as e:
        logger.error(f"[Story] Error listing stories: {e}")
        return []
