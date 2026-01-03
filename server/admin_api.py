"""
Admin API Endpoints
===================
Backend API for admin panel to manage rooms, settings, and data.
"""

import logging
from flask import Blueprint, jsonify, request
from supabase_client import (
    supabase,
    get_room,
    get_participants,
    get_chat_history,
)

logger = logging.getLogger("ADMIN_API")

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ============================================================
# Settings Management
# ============================================================

@admin_bp.route('/settings', methods=['GET'])
def get_all_settings():
    """Get all configuration settings grouped by category"""
    try:
        response = supabase.table('settings').select('*').order('category').execute()

        settings = response.data if response.data else []

        # Group by category
        grouped = {}
        for setting in settings:
            category = setting.get('category', 'general')
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(setting)

        logger.info(f"📊 Admin: Retrieved {len(settings)} settings")
        return jsonify({
            "settings": settings,
            "grouped": grouped,
            "count": len(settings)
        })

    except Exception as e:
        logger.error(f"❌ Error getting settings: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/settings/<key>', methods=['GET'])
def get_setting(key: str):
    """Get specific setting by key"""
    try:
        response = supabase.table('settings').select('*').eq('key', key).single().execute()

        if not response.data:
            return jsonify({"error": "Setting not found"}), 404

        return jsonify(response.data)

    except Exception as e:
        logger.error(f"❌ Error getting setting {key}: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/settings/<key>', methods=['PUT'])
def update_setting(key: str):
    """Update a setting value"""
    try:
        data = request.json
        new_value = data.get('value')

        if new_value is None:
            return jsonify({"error": "Value is required"}), 400

        # Update setting
        response = supabase.table('settings').update({
            'value': str(new_value),
            'updated_by': data.get('updated_by', 'admin')
        }).eq('key', key).execute()

        if not response.data:
            return jsonify({"error": "Setting not found"}), 404

        # Log the change
        log_admin_action('update_setting', 'setting', None, {
            'key': key,
            'old_value': data.get('old_value'),
            'new_value': new_value
        }, data.get('admin_user', 'unknown'))

        logger.info(f"✅ Admin: Updated setting {key} = {new_value}")
        return jsonify(response.data[0])

    except Exception as e:
        logger.error(f"❌ Error updating setting {key}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ============================================================
# Room Management
# ============================================================

@admin_bp.route('/rooms', methods=['GET'])
def get_all_rooms():
    """Get all rooms with filters"""
    try:
        # Get query parameters
        status = request.args.get('status')  # waiting, active, completed
        mode = request.args.get('mode')  # active, passive
        limit = int(request.args.get('limit', 50))

        # Build query
        query = supabase.table('rooms').select('*')

        if status:
            query = query.eq('status', status)
        if mode:
            query = query.eq('mode', mode)

        query = query.order('created_at', desc=True).limit(limit)

        response = query.execute()
        rooms = response.data if response.data else []

        # Enrich with participant count
        for room in rooms:
            participants = get_participants(room['id'])
            room['participant_list'] = participants
            room['actual_participant_count'] = len(participants)

        logger.info(f"📊 Admin: Retrieved {len(rooms)} rooms (status={status}, mode={mode})")
        return jsonify({
            "rooms": rooms,
            "count": len(rooms),
            "filters": {"status": status, "mode": mode}
        })

    except Exception as e:
        logger.error(f"❌ Error getting rooms: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/rooms/<room_id>', methods=['GET'])
def get_room_details(room_id: str):
    """Get detailed room information including participants and messages"""
    try:
        room = get_room(room_id)
        if not room:
            return jsonify({"error": "Room not found"}), 404

        participants = get_participants(room_id)
        messages = get_chat_history(room_id)

        # Get session info
        session_response = supabase.table('sessions').select('*').eq('room_id', room_id).execute()
        sessions = session_response.data if session_response.data else []

        logger.info(f"📊 Admin: Viewed room {room_id}")
        return jsonify({
            "room": room,
            "participants": participants,
            "messages": messages,
            "sessions": sessions,
            "stats": {
                "participant_count": len(participants),
                "message_count": len(messages),
                "session_count": len(sessions)
            }
        })

    except Exception as e:
        logger.error(f"❌ Error getting room details: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/rooms/<room_id>', methods=['DELETE'])
def delete_room(room_id: str):
    """Delete a room and all associated data"""
    try:
        # Check if room exists
        room = get_room(room_id)
        if not room:
            return jsonify({"error": "Room not found"}), 404

        # Delete associated data in order (due to foreign key constraints)
        # 1. Delete messages
        supabase.table('messages').delete().eq('room_id', room_id).execute()

        # 2. Delete participants
        supabase.table('participants').delete().eq('room_id', room_id).execute()

        # 3. Delete sessions
        supabase.table('sessions').delete().eq('room_id', room_id).execute()

        # 4. Delete research data
        supabase.table('research_data').delete().eq('room_id', room_id).execute()

        # 5. Finally delete the room
        supabase.table('rooms').delete().eq('id', room_id).execute()

        # Log the deletion
        log_admin_action('delete_room', 'room', room_id, {'room_mode': room.get('mode')})

        logger.info(f"🗑️ Admin: Deleted room {room_id}")
        return jsonify({"success": True, "message": "Room deleted successfully"})

    except Exception as e:
        logger.error(f"❌ Error deleting room: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/rooms/<room_id>/messages', methods=['GET'])
def get_room_messages(room_id: str):
    """Get messages for a specific room (for live monitoring)"""
    try:
        messages = get_chat_history(room_id)

        return jsonify({
            "room_id": room_id,
            "messages": messages,
            "count": len(messages)
        })

    except Exception as e:
        logger.error(f"❌ Error getting room messages: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================
# Statistics & Analytics
# ============================================================

@admin_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get overall statistics"""
    try:
        # Room stats
        rooms_response = supabase.table('rooms').select('id, status, mode, current_participants').execute()
        rooms = rooms_response.data if rooms_response.data else []

        # Session stats
        sessions_response = supabase.table('sessions').select('id, mode, participant_count, message_count, duration_seconds').execute()
        sessions = sessions_response.data if sessions_response.data else []

        # Message stats
        messages_response = supabase.table('messages').select('id, message_type').execute()
        messages = messages_response.data if messages_response.data else []

        # Calculate stats
        stats = {
            "rooms": {
                "total": len(rooms),
                "waiting": len([r for r in rooms if r['status'] == 'waiting']),
                "active": len([r for r in rooms if r['status'] == 'active']),
                "completed": len([r for r in rooms if r['status'] == 'completed']),
                "active_mode": len([r for r in rooms if r['mode'] == 'active']),
                "passive_mode": len([r for r in rooms if r['mode'] == 'passive']),
            },
            "sessions": {
                "total": len(sessions),
                "active_mode": len([s for s in sessions if s['mode'] == 'active']),
                "passive_mode": len([s for s in sessions if s['mode'] == 'passive']),
                "avg_participants": sum(s.get('participant_count', 0) for s in sessions) / len(sessions) if sessions else 0,
                "avg_messages": sum(s.get('message_count', 0) for s in sessions) / len(sessions) if sessions else 0,
                "avg_duration": sum(s.get('duration_seconds', 0) for s in sessions) / len(sessions) if sessions else 0,
            },
            "messages": {
                "total": len(messages),
                "chat": len([m for m in messages if m['message_type'] == 'chat']),
                "system": len([m for m in messages if m['message_type'] == 'system']),
                "moderator": len([m for m in messages if m['message_type'] == 'moderator']),
                "story": len([m for m in messages if m['message_type'] == 'story']),
            }
        }

        logger.info(f"📊 Admin: Retrieved statistics")
        return jsonify(stats)

    except Exception as e:
        logger.error(f"❌ Error getting stats: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ============================================================
# Data Export
# ============================================================

@admin_bp.route('/export/sessions', methods=['GET'])
def export_sessions():
    """Export session data for research"""
    try:
        # Get date range if provided
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        query = supabase.table('sessions').select('*')

        if start_date:
            query = query.gte('started_at', start_date)
        if end_date:
            query = query.lte('started_at', end_date)

        response = query.order('started_at', desc=True).execute()
        sessions = response.data if response.data else []

        # Log export
        log_admin_action('export_sessions', 'session', None, {
            'count': len(sessions),
            'start_date': start_date,
            'end_date': end_date
        })

        logger.info(f"📊 Admin: Exported {len(sessions)} sessions")
        return jsonify({
            "sessions": sessions,
            "count": len(sessions),
            "filters": {"start_date": start_date, "end_date": end_date}
        })

    except Exception as e:
        logger.error(f"❌ Error exporting sessions: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ============================================================
# Admin Logs
# ============================================================

def log_admin_action(action: str, entity_type: str = None, entity_id: str = None,
                     details: dict = None, admin_user: str = 'admin'):
    """Log an admin action"""
    try:
        supabase.table('admin_logs').insert({
            'action': action,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'details': details or {},
            'admin_user': admin_user,
            'ip_address': request.remote_addr if request else None
        }).execute()
    except Exception as e:
        logger.error(f"Failed to log admin action: {e}")


@admin_bp.route('/logs', methods=['GET'])
def get_admin_logs():
    """Get admin activity logs"""
    try:
        limit = int(request.args.get('limit', 100))

        response = (
            supabase.table('admin_logs')
            .select('*')
            .order('created_at', desc=True)
            .limit(limit)
            .execute()
        )

        logs = response.data if response.data else []

        return jsonify({
            "logs": logs,
            "count": len(logs)
        })

    except Exception as e:
        logger.error(f"❌ Error getting admin logs: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================
# Helper: Get Setting Value
# ============================================================

def get_setting_value(key: str, default=None):
    """
    Get a setting value from database with type conversion.
    Used by main app to load settings.
    """
    try:
        response = supabase.table('settings').select('*').eq('key', key).single().execute()

        if not response.data:
            return default

        setting = response.data
        value_str = setting['value']
        data_type = setting.get('data_type', 'string')

        # Convert based on type
        if data_type == 'integer':
            return int(value_str)
        elif data_type == 'float':
            return float(value_str)
        elif data_type == 'boolean':
            return value_str.lower() in ('true', '1', 'yes')
        else:
            return value_str

    except Exception as e:
        logger.warning(f"Failed to get setting {key}, using default: {e}")
        return default
