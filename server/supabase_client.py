"""
Supabase Client Configuration and Database Operations
========================================================
This module handles all database interactions with Supabase.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("SUPABASE_CLIENT")

# ============================================================
# Supabase Configuration
# ============================================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for server-side

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env"
    )

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

logger.info("✅ Supabase client initialized")


# ============================================================
# Room Operations
# ============================================================

def find_available_room(mode: str) -> Optional[Dict[str, Any]]:
    """
    Find a room with available space for the given mode.
    Looks for rooms in 'waiting' or 'active' status with < 3 participants.

    Args:
        mode: 'active' or 'passive'

    Returns:
        Room dict if found, None otherwise
    """
    try:
        response = (
            supabase.table("rooms")
            .select("*")
            .eq("mode", mode)
            .in_("status", ["waiting", "active"])  # Find rooms that are waiting OR active
            .lt("current_participants", 3)  # max_participants is 3
            .order("created_at", desc=False)
            .limit(1)
            .execute()
        )

        if response.data and len(response.data) > 0:
            room = response.data[0]
            logger.info(f"✅ Found available room: {room['id']} (status={room['status']}, participants={room['current_participants']}/3)")
            return room

        logger.info(f"ℹ️ No available room found for mode: {mode}, will create new room")
        return None

    except Exception as e:
        logger.error(f"❌ Error finding available room: {e}")
        return None


def create_room(mode: str, story_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new room.

    Args:
        mode: 'active' or 'passive'
        story_id: Story identifier

    Returns:
        Created room dict
    """
    try:
        response = (
            supabase.table("rooms")
            .insert({
                "mode": mode,
                "story_id": story_id,
                "status": "waiting"
            })
            .execute()
        )

        room = response.data[0]
        logger.info(f"Created room: {room['id']} (mode: {mode})")
        return room

    except Exception as e:
        logger.error(f"Error creating room: {e}")
        raise


def get_room(room_id: str) -> Optional[Dict[str, Any]]:
    """Get room by ID."""
    try:
        response = (
            supabase.table("rooms")
            .select("*")
            .eq("id", room_id)
            .single()
            .execute()
        )
        return response.data

    except Exception as e:
        logger.error(f"Error getting room {room_id}: {e}")
        return None


def update_room_status(room_id: str, status: str) -> Optional[Dict[str, Any]]:
    """
    Update room status.

    Args:
        room_id: Room ID
        status: 'waiting', 'active', or 'completed'
    """
    try:
        update_data = {"status": status}

        if status == "active":
            update_data["started_at"] = datetime.utcnow().isoformat()
        elif status == "completed":
            update_data["completed_at"] = datetime.utcnow().isoformat()

        response = (
            supabase.table("rooms")
            .update(update_data)
            .eq("id", room_id)
            .execute()
        )

        logger.info(f"Updated room {room_id} status to {status}")
        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Error updating room status: {e}")
        return None


def update_story_progress(room_id: str, progress: int, finished: bool = False):
    """Update story progress in room."""
    try:
        supabase.table("rooms").update({
            "story_progress": progress,
            "story_finished": finished
        }).eq("id", room_id).execute()

        logger.debug(f"Updated story progress for room {room_id}: {progress}")

    except Exception as e:
        logger.error(f"Error updating story progress: {e}")


# ============================================================
# Participant Operations
# ============================================================

def add_participant(
    room_id: str,
    display_name: str,
    socket_id: str,
    is_moderator: bool = False
) -> Dict[str, Any]:
    """
    Add participant to room.

    Args:
        room_id: Room ID
        display_name: Participant name
        socket_id: Socket.IO connection ID
        is_moderator: Whether this is the AI moderator

    Returns:
        Created participant dict
    """
    try:
        response = (
            supabase.table("participants")
            .insert({
                "room_id": room_id,
                "display_name": display_name,
                "socket_id": socket_id,
                "is_moderator": is_moderator
            })
            .execute()
        )

        participant = response.data[0]
        logger.info(f"Added participant {display_name} to room {room_id}")
        return participant

    except Exception as e:
        logger.error(f"Error adding participant: {e}")
        raise


def get_next_participant_name(room_id: str) -> str:
    """Generate next available participant name (Student 1, Student 2, etc.)."""
    try:
        response = (
            supabase.table("participants")
            .select("id")
            .eq("room_id", room_id)
            .eq("is_moderator", False)
            .execute()
        )

        count = len(response.data) if response.data else 0
        return f"Student {count + 1}"

    except Exception as e:
        logger.error(f"Error getting next participant name: {e}")
        return "Student 1"


def get_participants(room_id: str) -> List[Dict[str, Any]]:
    """Get all participants in room."""
    try:
        response = (
            supabase.table("participants")
            .select("*")
            .eq("room_id", room_id)
            .order("joined_at", desc=False)
            .execute()
        )

        return response.data if response.data else []

    except Exception as e:
        logger.error(f"Error getting participants: {e}")
        return []


def get_participant_by_socket(socket_id: str) -> Optional[Dict[str, Any]]:
    """Get participant by Socket.IO ID."""
    try:
        response = (
            supabase.table("participants")
            .select("*")
            .eq("socket_id", socket_id)
            .single()
            .execute()
        )
        return response.data

    except Exception as e:
        logger.debug(f"Participant not found for socket {socket_id}")
        return None


def update_participant_activity(participant_id: str):
    """Update participant's last activity timestamp."""
    try:
        supabase.table("participants").update({
            "last_active_at": datetime.utcnow().isoformat()
        }).eq("id", participant_id).execute()

    except Exception as e:
        logger.error(f"Error updating participant activity: {e}")


# ============================================================
# Message Operations
# ============================================================

def add_message(
    room_id: str,
    sender_name: str,
    message_text: str,
    participant_id: Optional[str] = None,
    message_type: str = "chat",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Add message to room.

    Args:
        room_id: Room ID
        sender_name: Display name of sender
        message_text: Message content
        participant_id: Participant ID (if applicable)
        message_type: 'chat', 'system', 'story', or 'moderator'
        metadata: Additional metadata

    Returns:
        Created message dict
    """
    try:
        response = (
            supabase.table("messages")
            .insert({
                "room_id": room_id,
                "participant_id": participant_id,
                "sender_name": sender_name,
                "message_text": message_text,
                "message_type": message_type,
                "metadata": metadata or {}
            })
            .execute()
        )

        message = response.data[0]
        logger.debug(f"Added message from {sender_name} in room {room_id}")
        return message

    except Exception as e:
        logger.error(f"Error adding message: {e}")
        raise


def get_chat_history(room_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get chat history for room.

    Args:
        room_id: Room ID
        limit: Maximum messages to retrieve (None for all)

    Returns:
        List of message dicts
    """
    try:
        query = (
            supabase.table("messages")
            .select("*")
            .eq("room_id", room_id)
            .order("created_at", desc=False)
        )

        if limit:
            query = query.limit(limit)

        response = query.execute()
        return response.data if response.data else []

    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return []


# ============================================================
# Session Operations
# ============================================================

def create_session(
    room_id: str,
    mode: str,
    participant_count: int,
    story_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create new session."""
    try:
        response = (
            supabase.table("sessions")
            .insert({
                "room_id": room_id,
                "mode": mode,
                "participant_count": participant_count,
                "story_id": story_id,
                "started_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            })
            .execute()
        )

        session = response.data[0]
        logger.info(f"Created session {session['id']} for room {room_id}")
        return session

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise


def end_session(room_id: str, metadata: Optional[Dict[str, Any]] = None):
    """End active session for room."""
    try:
        # Get message count
        messages = get_chat_history(room_id)
        message_count = len(messages)

        # Calculate duration and update session
        update_data = {
            "ended_at": datetime.utcnow().isoformat(),
            "message_count": message_count
        }

        if metadata:
            update_data["metadata"] = metadata

        response = (
            supabase.table("sessions")
            .update(update_data)
            .eq("room_id", room_id)
            .is_("ended_at", "null")
            .execute()
        )

        if response.data:
            logger.info(f"Ended session for room {room_id}")

    except Exception as e:
        logger.error(f"Error ending session: {e}")


# ============================================================
# Auto Room Assignment
# ============================================================

def get_or_create_room(mode: str, story_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get available room or create new one.
    This is the main function for auto-room assignment.

    Args:
        mode: 'active' or 'passive'
        story_id: Story to use

    Returns:
        Room dict
    """
    # Try to find available room
    room = find_available_room(mode)

    # Create new room if none available
    if not room:
        room = create_room(mode, story_id)

    return room
