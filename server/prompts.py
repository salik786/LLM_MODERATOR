from __future__ import annotations

# ============================================================
# 📦 Imports
# ============================================================
from typing import List, Dict, Any, Optional
import os
import re
import logging
import random
import traceback
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from chatbot import Chatbot

# ============================================================
# 🔧 Environment Setup
# ============================================================
load_dotenv()
logger = logging.getLogger("moderator-prompts")

# ============================================================
# ⚙️ Config Loader (Single Source of Truth)
# ============================================================
def get_env(name: str, cast=str, required: bool = False):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        msg = f"[Config] Missing env var: {name}"
        if required:
            raise EnvironmentError(msg)
        logger.warning(msg)
        return None
    try:
        return cast(value)
    except Exception:
        logger.error(f"[Config] Failed to cast {name}")
        return None

# ============================================================
# 🌍 Core Model Configuration
# ============================================================
OPENAI_MODEL = get_env("OPENAI_CHAT_MODEL", str, True)
TEMPERATURE = get_env("OPENAI_TEMPERATURE", float, True)
MAX_TOKENS = get_env("OPENAI_MAX_TOKENS", int, True)

ACTIVE_MODE = get_env("ACTIVE_MODE", str, True).lower().strip()
PASSIVE_MODE = get_env("PASSIVE_MODE", str, True).lower().strip()

ACTIVE_STORY_STEP = get_env("ACTIVE_STORY_STEP", int, True)
PASSIVE_STORY_STEP = get_env("PASSIVE_STORY_STEP", int, True)

CHAT_HISTORY_LIMIT = get_env("CHAT_HISTORY_LIMIT", int, True)

ACTIVE_ENDING_STYLE = get_env("ACTIVE_ENDING_STYLE", str, True).lower().strip()
PASSIVE_ENDING_STYLE = get_env("PASSIVE_ENDING_STYLE", str, True).lower().strip()

WELCOME_MESSAGE = get_env("WELCOME_MESSAGE", str, True)
ACTIVE_ENDING_MESSAGE = get_env("ACTIVE_ENDING_MESSAGE", str, True)
PASSIVE_ENDING_MESSAGE = get_env("PASSIVE_ENDING_MESSAGE", str, True)

# ============================================================
# 🧠 LLM Initialization
# ============================================================
llm = ChatOpenAI(
    model=OPENAI_MODEL,
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS,
)

fallback_chatbot = Chatbot(
    system_prompt=(
        "You are a warm, emotionally intelligent classroom moderator "
        "who guides students gently and keeps them engaged."
    )
)

# ============================================================
# 🧩 ACTIVE MODE PROMPTS — ENHANCED (NO DELETIONS)
# ============================================================
ACTIVE_MODE_PROMPTS = {

    "story": """
You are a warm, supportive classroom Moderator guiding students through a FIXED, pre-written story.

Your personality:
- Kind, encouraging, emotionally aware
- You sound like a caring teacher reading a story aloud
- You value student voices and participation

Your responsibility:
- The story already exists and must be followed exactly.
- You guide students through it step by step until its natural ending.
- You do not invent, rewrite, or change story events.

How you treat students:
- You acknowledge their ideas warmly, even when they are incorrect.
- You encourage participation and gently invite quiet students.
- You validate feelings, curiosity, and effort.
- You never shame, criticize, or dismiss students.

Story control (very important):
- The story is the authority; student input is secondary.
- You NEVER change the plot based on student ideas.
- If a student idea conflicts with the story, you kindly redirect.
- If a student is silly, wrong, off-topic, or inappropriate, you respond calmly and continue the story.

How to respond:
- 1–2 short sentences only.
- First: a gentle acknowledgment or encouragement.
- Then: continue the NEXT sentence(s) of the story as written.
- Each response advances the story by ONE step only.

Behavior rules:
- You are a guide, not a co-author.
- You never stall, loop, or drift away from the story.
- You speak once per interval, then pause.

Ending:
- When the final story sentence is reached, you deliver the ending gently.
- After the ending, you stop completely.


""",

    "discussion": """
You are the Moderator guiding a structured discussion.

Tone:
- Calm, respectful, encouraging

Rules:
- Short responses
- Summarize key ideas gently
- Encourage quieter students by name when appropriate
- Keep momentum without pressure
""",

    "teacher": """
You are a supportive teacher-moderator.

Tone:
- Patient, kind, reassuring

Rules:
- Explain simply
- Encourage curiosity
- Correct gently through examples
- Always move forward positively
"""
}

# ============================================================
# 🧭 Tone Adaptation (Optional Context Layer)
# ============================================================
def generate_style_hint(majors: List[str]) -> str:
    joined = ", ".join(majors).lower()
    if any(x in joined for x in ["computer", "engineering", "data", "math"]):
        return "Logical but friendly tone."
    if any(x in joined for x in ["education", "psychology", "social"]):
        return "Warm, empathetic tone."
    if any(x in joined for x in ["art", "design", "media"]):
        return "Imaginative, expressive tone."
    return "Balanced, friendly classroom tone."

# ============================================================
# 🧠 INTERNAL ANALYSIS PROMPT (Hidden Layer — unchanged)
# ============================================================
def _internal_story_analysis(chat_history, story_block):
    try:
        prompt = f"""
Analyze the classroom interaction silently.
Do NOT generate output for students.

Story context:
{story_block}

Recent interaction:
{chat_history[-5:]}

Determine:
- Is the story progressing?
- Is gentle intervention needed?
"""
        llm.invoke([SystemMessage(content=prompt)])
    except Exception:
        pass

# ============================================================
# 💬 ACTIVE MODERATOR REPLY
# ============================================================
def generate_moderator_reply(
    participants: List[str],
    chat_history: List[Dict[str, Any]],
    story_block: str,
    story_progress: int = 0,
    extra_context: Optional[Dict[str, Any]] = None,
    is_last_chunk: bool = False,
) -> str:
    try:
        style_prompt = ACTIVE_MODE_PROMPTS.get(
            ACTIVE_MODE, ACTIVE_MODE_PROMPTS["story"]
        )

        trimmed_history = chat_history[-CHAT_HISTORY_LIMIT:]
        names = ", ".join(participants) if participants else "everyone"

        prompt = f"""
{style_prompt}

Story so far:
{story_block}

Recent chat (last interval):
{trimmed_history}

Participants:
{names}

Instructions:
- Respond once only
- Move the story forward by ONE step
- Be warm and encouraging
"""

        resp = llm.invoke(
            [
                SystemMessage(content="You are a warm classroom story moderator."),
                HumanMessage(content=prompt),
            ]
        )

        text = (resp.content or "").strip()
        text = re.sub(r"^\s*Moderator[:\-–]?\s*", "", text)
        text = " ".join(text.split()[:140])

        if is_last_chunk:
            return ACTIVE_ENDING_MESSAGE

        return text or "The story continues gently."

    except Exception as e:
        logger.error("[generate_moderator_reply]", e)
        logger.debug(traceback.format_exc())
        fb = fallback_chatbot.send_message(str(chat_history[-5:]))
        return fb.content if fb else "Let’s continue together."

# ============================================================
# 🕯 PASSIVE STORYTELLER
# ============================================================
def generate_passive_chunk(
    paragraph: str,
    mode: str = None,
    is_last_chunk: bool = False,
) -> str:
    clean = paragraph.strip()
    if not clean:
        return ""

    if is_last_chunk:
        return PASSIVE_ENDING_MESSAGE

    if PASSIVE_ENDING_STYLE == "question":
        return f"{clean} What do you feel might happen next?"
    elif PASSIVE_ENDING_STYLE == "pause":
        return f"{clean} The story pauses softly."
    elif PASSIVE_ENDING_STYLE == "end":
        return PASSIVE_ENDING_MESSAGE
    else:
        return clean

# ============================================================
# 💡 NUDGE GENERATOR
# ============================================================
def generate_gpt_nudge(
    chat_history: List[Dict[str, Any]],
    story_block: str,
    nudge_count: int = 1,
) -> str:
    try:
        prompt = f"""
You are a kind classroom moderator.

Students are quiet.
Generate ONE warm, gentle encouragement:
- 1 sentence
- Soft, human tone
- Invite without pressure
- Feel like part of the story

Story context:
{story_block}
"""
        resp = llm.invoke([HumanMessage(content=prompt)])
        text = (resp.content or "").strip()
        return re.sub(r"^\s*Moderator[:\-–]?\s*", "", text)

    except Exception:
        return "Take your time—your ideas are welcome whenever you’re ready."

# ============================================================
# 🧠 SEMANTIC CLASSIFIER
# ============================================================
def classify_reply_semantic(
    chat_history: List[Dict[str, Any]],
    message: str,
    llm,
) -> str:
    try:
        prompt = f"""
Classify the student's reply into ONE category:

symbolic
neutral
reflective
questioning
emotional
imaginative
causal
meta
off-topic
group

Reply:
"{message}"
"""
        resp = llm.invoke([HumanMessage(content=prompt)])
        label = (resp.content or "").strip().lower()

        allowed = {
            "symbolic", "neutral", "reflective", "questioning",
            "emotional", "imaginative", "causal",
            "meta", "off-topic", "group"
        }

        return label if label in allowed else "neutral"

    except Exception:
        return "neutral"

# ============================================================
# 🍃 RANDOM ENDINGS (UNCHANGED)
# ============================================================
def get_random_ending() -> str:
    endings = [
        "And so the story gently came to an end.",
        "With that, the adventure softly concluded.",
        "The tale settled into a peaceful ending.",
        "And the story rested, complete at last.",
        "The journey ended quietly, leaving smiles behind.",
        "The night grew calm as the story closed.",
        "The final moment arrived, soft and warm.",
    ]
    return random.choice(endings)
