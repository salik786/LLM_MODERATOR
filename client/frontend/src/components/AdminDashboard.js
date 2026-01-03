// =========================
// Admin Dashboard
// Comprehensive admin panel for managing rooms, settings, and viewing data
// =========================
import React, { useState, useEffect } from 'react';
import { MdSettings, MdPeople, MdChat, MdBarChart, MdRefresh } from 'react-icons/md';

const API_URL = 'http://localhost:5000';

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [stats, setStats] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [settings, setSettings] = useState([]);
  const [selectedRoom, setSelectedRoom] = useState(null);
  const [loading, setLoading] = useState(false);

  // Load initial data
  useEffect(() => {
    loadStats();
    loadRooms();
    loadSettings();
  }, []);

  // Auto-refresh stats and rooms every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      if (activeTab === 'dashboard' || activeTab === 'rooms') {
        loadStats();
        loadRooms();
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [activeTab]);

  const loadStats = async () => {
    try {
      const res = await fetch(`${API_URL}/admin/stats`);
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

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
      alert(`✅ Setting "${key}" updated successfully`);
    } catch (err) {
      console.error('Failed to update setting:', err);
      alert(`❌ Failed to update setting: ${err.message}`);
    } finally {
      setLoading(false);
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
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-indigo-600 text-white shadow-lg">
        <div className="container mx-auto px-6 py-4">
          <h1 className="text-3xl font-bold">LLM Moderator - Admin Panel</h1>
          <p className="text-indigo-200 text-sm">Manage rooms, settings, and view research data</p>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="bg-white shadow">
        <div className="container mx-auto px-6">
          <nav className="flex space-x-4">
            <TabButton
              active={activeTab === 'dashboard'}
              onClick={() => setActiveTab('dashboard')}
              icon={<MdBarChart />}
              label="Dashboard"
            />
            <TabButton
              active={activeTab === 'rooms'}
              onClick={() => setActiveTab('rooms')}
              icon={<MdPeople />}
              label="Rooms"
            />
            <TabButton
              active={activeTab === 'settings'}
              onClick={() => setActiveTab('settings')}
              icon={<MdSettings />}
              label="Settings"
            />
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-6 py-8">
        {activeTab === 'dashboard' && (
          <DashboardView stats={stats} onRefresh={loadStats} />
        )}

        {activeTab === 'rooms' && (
          <RoomsView
            rooms={rooms}
            onViewDetails={viewRoomDetails}
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
          />
        )}
      </div>
    </div>
  );
}

// Tab Button Component
function TabButton({ active, onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium transition ${
        active
          ? 'border-indigo-600 text-indigo-600'
          : 'border-transparent text-gray-600 hover:text-indigo-600 hover:border-gray-300'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

// Dashboard View with Stats
function DashboardView({ stats, onRefresh }) {
  if (!stats) {
    return <div className="text-center py-12">Loading statistics...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Dashboard</h2>
        <button
          onClick={onRefresh}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700"
        >
          <MdRefresh /> Refresh
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatCard
          title="Total Rooms"
          value={stats.rooms.total}
          breakdown={[
            { label: 'Active', value: stats.rooms.active, color: 'green' },
            { label: 'Waiting', value: stats.rooms.waiting, color: 'yellow' },
            { label: 'Completed', value: stats.rooms.completed, color: 'gray' }
          ]}
        />
        <StatCard
          title="Total Sessions"
          value={stats.sessions.total}
          breakdown={[
            { label: 'Active Mode', value: stats.sessions.active_mode, color: 'blue' },
            { label: 'Passive Mode', value: stats.sessions.passive_mode, color: 'purple' }
          ]}
        />
        <StatCard
          title="Total Messages"
          value={stats.messages.total}
          breakdown={[
            { label: 'Chat', value: stats.messages.chat, color: 'blue' },
            { label: 'Moderator', value: stats.messages.moderator, color: 'indigo' }
          ]}
        />
      </div>

      {/* Session Averages */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Session Averages</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-gray-600">Avg Participants</p>
            <p className="text-2xl font-bold text-indigo-600">
              {stats.sessions.avg_participants.toFixed(1)}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Avg Messages</p>
            <p className="text-2xl font-bold text-indigo-600">
              {stats.sessions.avg_messages.toFixed(1)}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Avg Duration</p>
            <p className="text-2xl font-bold text-indigo-600">
              {Math.round(stats.sessions.avg_duration / 60)} min
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Stat Card Component
function StatCard({ title, value, breakdown }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-sm font-medium text-gray-600 mb-2">{title}</h3>
      <p className="text-3xl font-bold text-gray-800 mb-4">{value}</p>
      {breakdown && (
        <div className="space-y-1">
          {breakdown.map((item, idx) => (
            <div key={idx} className="flex justify-between text-sm">
              <span className="text-gray-600">{item.label}</span>
              <span className={`font-semibold text-${item.color}-600`}>
                {item.value}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Rooms List View
function RoomsView({ rooms, onViewDetails, onFilterChange, onRefresh }) {
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
            className="border border-gray-300 rounded-lg px-4 py-2"
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
                    <button
                      onClick={() => onViewDetails(room.id)}
                      className="text-indigo-600 hover:text-indigo-900 flex items-center gap-1"
                    >
                      <MdChat /> View
                    </button>
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
                            className="text-green-600 hover:text-green-900"
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
                          className="text-indigo-600 hover:text-indigo-900"
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
function RoomDetailView({ room, onBack }) {
  return (
    <div>
      <button
        onClick={onBack}
        className="mb-4 text-indigo-600 hover:text-indigo-900"
      >
        ← Back to Rooms
      </button>

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
