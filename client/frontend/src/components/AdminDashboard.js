// =========================
// Admin Dashboard
// Professional admin panel with vertical navigation
// =========================
import React, { useState, useEffect } from 'react';
import { MdSettings, MdPeople, MdLink, MdDelete, MdRefresh, MdVisibility, MdContentCopy } from 'react-icons/md';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
const FRONTEND_URL = window.location.origin;

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('rooms');
  const [rooms, setRooms] = useState([]);
  const [settings, setSettings] = useState([]);
  const [selectedRoom, setSelectedRoom] = useState(null);
  const [loading, setLoading] = useState(false);

  // Load initial data
  useEffect(() => {
    loadRooms();
    loadSettings();
  }, []);

  // Auto-refresh rooms every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      if (activeTab === 'rooms') {
        loadRooms();
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [activeTab]);

  const loadRooms = async (status = null) => {
    try {
      const url = status ? `${API_URL}/admin/rooms?status=${status}` : `${API_URL}/admin/rooms`;
      const res = await fetch(url);
      const data = await res.json();
      setRooms(data.rooms || []);
    } catch (err) {
      console.error('Failed to load rooms:', err);
    }
  };

  const loadSettings = async () => {
    try {
      const res = await fetch(`${API_URL}/admin/settings`);
      const data = await res.json();
      setSettings(data.settings || []);
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  };

  const updateSetting = async (key, value) => {
    try {
      setLoading(true);
      await fetch(`${API_URL}/admin/settings/${key}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value, updated_by: 'admin' })
      });
      await loadSettings();
      alert(`✅ Setting "${key}" updated successfully. Restart backend to apply.`);
    } catch (err) {
      console.error('Failed to update setting:', err);
      alert(`❌ Failed to update setting: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const deleteRoom = async (roomId) => {
    if (!window.confirm('Are you sure you want to delete this room? This cannot be undone.')) {
      return;
    }

    try {
      const res = await fetch(`${API_URL}/admin/rooms/${roomId}`, {
        method: 'DELETE'
      });

      if (!res.ok) {
        throw new Error('Failed to delete room');
      }

      alert('✅ Room deleted successfully');
      await loadRooms();
      if (selectedRoom?.room?.id === roomId) {
        setSelectedRoom(null);
        setActiveTab('rooms');
      }
    } catch (err) {
      console.error('Failed to delete room:', err);
      alert(`❌ Failed to delete room: ${err.message}`);
    }
  };

  const viewRoomDetails = async (roomId) => {
    try {
      const res = await fetch(`${API_URL}/admin/rooms/${roomId}`);
      const data = await res.json();
      setSelectedRoom(data);
      setActiveTab('room-detail');
    } catch (err) {
      console.error('Failed to load room details:', err);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Vertical Sidebar */}
      <aside className="w-64 bg-white shadow-lg">
        <div className="p-6 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-800">Admin Panel</h1>
          <p className="text-xs text-gray-500 mt-1">LLM Moderator</p>
        </div>

        <nav className="p-4">
          <NavItem
            active={activeTab === 'links'}
            onClick={() => setActiveTab('links')}
            icon={<MdLink size={20} />}
            label="Shareable Links"
          />
          <NavItem
            active={activeTab === 'rooms'}
            onClick={() => setActiveTab('rooms')}
            icon={<MdPeople size={20} />}
            label="Rooms"
          />
          <NavItem
            active={activeTab === 'settings'}
            onClick={() => setActiveTab('settings')}
            icon={<MdSettings size={20} />}
            label="Settings"
          />
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">
          {activeTab === 'links' && <LinksView />}

          {activeTab === 'rooms' && (
            <RoomsView
              rooms={rooms}
              onViewDetails={viewRoomDetails}
              onDeleteRoom={deleteRoom}
              onFilterChange={loadRooms}
              onRefresh={loadRooms}
            />
          )}

          {activeTab === 'settings' && (
            <SettingsView
              settings={settings}
              onUpdate={updateSetting}
              loading={loading}
            />
          )}

          {activeTab === 'room-detail' && selectedRoom && (
            <RoomDetailView
              room={selectedRoom}
              onBack={() => setActiveTab('rooms')}
              onDelete={() => deleteRoom(selectedRoom.room.id)}
            />
          )}
        </div>
      </main>
    </div>
  );
}

// Vertical Nav Item Component
function NavItem({ active, onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-3 mb-2 rounded-lg transition-all ${
        active
          ? 'bg-indigo-600 text-white shadow-md'
          : 'text-gray-700 hover:bg-gray-100'
      }`}
    >
      {icon}
      <span className="font-medium">{label}</span>
    </button>
  );
}

// Shareable Links View
function LinksView() {
  const activeLink = `${FRONTEND_URL}/join/active`;
  const passiveLink = `${FRONTEND_URL}/join/passive`;

  const copyToClipboard = (text, type) => {
    navigator.clipboard.writeText(text);
    alert(`✅ ${type} link copied to clipboard!`);
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Shareable Links</h2>

      <div className="space-y-4">
        {/* Active Mode Link */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold text-gray-800">Active Mode Link</h3>
            <span className="px-3 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-full">
              Active
            </span>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Share this link with participants to auto-join Active mode rooms.
            AI actively moderates and asks questions.
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              value={activeLink}
              readOnly
              className="flex-1 px-4 py-2 bg-gray-50 border border-gray-300 rounded-lg font-mono text-sm"
            />
            <button
              onClick={() => copyToClipboard(activeLink, 'Active mode')}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 flex items-center gap-2"
            >
              <MdContentCopy /> Copy
            </button>
          </div>
        </div>

        {/* Passive Mode Link */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold text-gray-800">Passive Mode Link</h3>
            <span className="px-3 py-1 bg-purple-100 text-purple-800 text-xs font-medium rounded-full">
              Passive
            </span>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Share this link with participants to auto-join Passive mode rooms.
            Story progresses automatically at intervals.
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              value={passiveLink}
              readOnly
              className="flex-1 px-4 py-2 bg-gray-50 border border-gray-300 rounded-lg font-mono text-sm"
            />
            <button
              onClick={() => copyToClipboard(passiveLink, 'Passive mode')}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 flex items-center gap-2"
            >
              <MdContentCopy /> Copy
            </button>
          </div>
        </div>

        {/* Instructions */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mt-6">
          <h4 className="font-semibold text-blue-900 mb-2">How It Works</h4>
          <ul className="text-sm text-blue-800 space-y-2">
            <li>• Participants clicking these links are auto-assigned anonymous names (Student 1, Student 2, etc.)</li>
            <li>• Users are automatically placed in available rooms (max 3 per room)</li>
            <li>• When a room fills to capacity, a new room is created for the next participants</li>
            <li>• Story starts automatically when the first user joins (configurable in Settings)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

// Rooms List View
function RoomsView({ rooms, onViewDetails, onDeleteRoom, onFilterChange, onRefresh }) {
  const [filter, setFilter] = useState('all');

  const handleFilterChange = (newFilter) => {
    setFilter(newFilter);
    onFilterChange(newFilter === 'all' ? null : newFilter);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Rooms</h2>
        <div className="flex gap-2">
          <select
            value={filter}
            onChange={(e) => handleFilterChange(e.target.value)}
            className="border border-gray-300 rounded-lg px-4 py-2 bg-white"
          >
            <option value="all">All Rooms</option>
            <option value="waiting">Waiting</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
          </select>
          <button
            onClick={() => onRefresh()}
            className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700"
          >
            <MdRefresh /> Refresh
          </button>
        </div>
      </div>

      {rooms.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <p className="text-gray-500">No rooms found</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Room ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Mode</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Participants</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Story</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {rooms.map((room) => (
                <tr key={room.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-mono text-gray-500">
                    {room.id.substring(0, 8)}...
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      room.mode === 'active' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
                    }`}>
                      {room.mode}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      room.status === 'active' ? 'bg-green-100 text-green-800' :
                      room.status === 'waiting' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {room.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {room.current_participants} / {room.max_participants}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {room.story_id || 'N/A'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {new Date(room.created_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <div className="flex gap-2">
                      <button
                        onClick={() => onViewDetails(room.id)}
                        className="text-indigo-600 hover:text-indigo-900 flex items-center gap-1"
                      >
                        <MdVisibility /> View
                      </button>
                      <button
                        onClick={() => onDeleteRoom(room.id)}
                        className="text-red-600 hover:text-red-900 flex items-center gap-1"
                      >
                        <MdDelete /> Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// Settings Editor View
function SettingsView({ settings, onUpdate, loading }) {
  const [editingKey, setEditingKey] = useState(null);
  const [editValue, setEditValue] = useState('');

  const groupedSettings = settings.reduce((acc, setting) => {
    const cat = setting.category || 'general';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(setting);
    return acc;
  }, {});

  const handleEdit = (setting) => {
    setEditingKey(setting.key);
    setEditValue(setting.value);
  };

  const handleSave = async (key) => {
    await onUpdate(key, editValue);
    setEditingKey(null);
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Settings</h2>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
        <p className="text-sm text-yellow-800">
          ⚠️ <strong>Important:</strong> After changing settings, restart the backend server to apply changes.
        </p>
      </div>

      {Object.entries(groupedSettings).map(([category, categorySettings]) => (
        <div key={category} className="mb-8">
          <h3 className="text-lg font-semibold text-gray-700 mb-4 capitalize">
            {category} Settings
          </h3>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Setting</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Value</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {categorySettings.map((setting) => (
                  <tr key={setting.key}>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      {setting.key}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {editingKey === setting.key ? (
                        <input
                          type="text"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          className="border border-indigo-300 rounded px-3 py-1 w-full"
                          autoFocus
                        />
                      ) : (
                        <code className="bg-gray-100 px-2 py-1 rounded">{setting.value}</code>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {setting.data_type}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {setting.description}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {editingKey === setting.key ? (
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleSave(setting.key)}
                            disabled={loading}
                            className="text-green-600 hover:text-green-900 font-medium"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => setEditingKey(null)}
                            className="text-gray-600 hover:text-gray-900"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleEdit(setting)}
                          className="text-indigo-600 hover:text-indigo-900 font-medium"
                        >
                          Edit
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}

// Room Detail View
function RoomDetailView({ room, onBack, onDelete }) {
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <button
          onClick={onBack}
          className="text-indigo-600 hover:text-indigo-900 font-medium"
        >
          ← Back to Rooms
        </button>
        <button
          onClick={onDelete}
          className="flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700"
        >
          <MdDelete /> Delete Room
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-2xl font-bold mb-4">Room Details</h2>
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div>
            <p className="text-sm text-gray-600">Room ID</p>
            <p className="font-mono text-sm">{room.room.id}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Mode</p>
            <p className="font-semibold">{room.room.mode}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Status</p>
            <p className="font-semibold">{room.room.status}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Participants</p>
            <p className="font-semibold">{room.stats.participant_count}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Messages</p>
            <p className="font-semibold">{room.stats.message_count}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Story Progress</p>
            <p className="font-semibold">{room.room.story_progress}</p>
          </div>
        </div>

        <h3 className="text-lg font-semibold mb-3">Participants</h3>
        <div className="space-y-2 mb-6">
          {room.participants.map((p) => (
            <div key={p.id} className="flex justify-between items-center bg-gray-50 p-3 rounded">
              <span className="font-medium">{p.display_name}</span>
              <span className="text-sm text-gray-500">
                Joined: {new Date(p.joined_at).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>

        <h3 className="text-lg font-semibold mb-3">Conversation ({room.messages.length} messages)</h3>
        <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
          {room.messages.map((msg, idx) => (
            <div
              key={idx}
              className={`mb-3 p-3 rounded ${
                msg.sender_name === 'Moderator' ? 'bg-indigo-100' : 'bg-white'
              }`}
            >
              <div className="flex justify-between items-start mb-1">
                <span className="font-semibold text-sm">{msg.sender_name}</span>
                <span className="text-xs text-gray-500">
                  {new Date(msg.created_at).toLocaleTimeString()}
                </span>
              </div>
              <p className="text-sm text-gray-700">{msg.message_text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
