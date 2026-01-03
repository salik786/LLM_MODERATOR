// ============================================================
// path: src/components/RoomCreation.jsx
// FULL VERSION — WITH ULTRA DEBUG LOGS
// (No deletions. Only added debug logs everywhere.)
// ============================================================

import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { socket } from "../socket";
import ShareableLinks from "./ShareableLinks";
import {
  MdPerson,
  MdMeetingRoom,
  MdPlayArrow,
  MdLogin,
  MdPsychology,
} from "react-icons/md";

// ============================================================
// 🔥 ULTRA DEBUG LOGGER
// ============================================================
const DEBUG = (...args) => {
  const timestamp = new Date().toISOString();
  console.log(`%c[ROOMCREATION DEBUG] ${timestamp}`, "color:#aa00ff;", ...args);
};

export default function RoomCreation() {
  const [roomId, setRoomId] = useState("");
  const [userName, setUserName] = useState("");
  const [major, setMajor] = useState("computer_science");
  const [activeModerator, setActiveModerator] = useState(true);
  const [loading, setLoading] = useState(false);
  const mountedRef = useRef(true);
  const navigate = useNavigate();

  // ------------------------------------------------------------
  // 🔌 Socket Lifecycle Debug
  // ------------------------------------------------------------
  useEffect(() => {
    mountedRef.current = true;

    DEBUG("RoomCreation mounted → socket.id:", socket.id);

    const onConnect = () => DEBUG("[socket] CONNECTED:", socket.id);
    const onConnectErr = (e) =>
      DEBUG("[socket] CONNECT_ERROR:", e?.message || e);
    const onDisconnect = (r) =>
      DEBUG("[socket] DISCONNECTED:", r, "socket.id:", socket.id);

    socket.on("connect", onConnect);
    socket.on("connect_error", onConnectErr);
    socket.on("disconnect", onDisconnect);

    return () => {
      DEBUG("RoomCreation unmounted → cleaning socket listeners");
      mountedRef.current = false;
      socket.off("connect", onConnect);
      socket.off("connect_error", onConnectErr);
      socket.off("disconnect", onDisconnect);
    };
  }, []);

  // ------------------------------------------------------------
  // 🚀 Create Room
  // ------------------------------------------------------------
  const createRoom = () => {
    DEBUG("createRoom CLICKED");

    if (loading) {
      DEBUG("Already loading → returning");
      return;
    }

    const name = userName.trim();
    if (!name) {
      DEBUG("UserName empty → alert triggered");
      alert("Please enter your name first.");
      return;
    }

    setLoading(true);

    DEBUG("Creating room with:", {
      userName: name,
      major,
      activeModerator,
    });

    const cleanup = () => {
      DEBUG("Cleanup listeners for createRoom");
      socket.off("room_created", onCreated);
      socket.off("error", onError);
    };

    const onCreated = ({ room_id }) => {
      DEBUG("room_created RECEIVED:", room_id);

      cleanup();
      if (!mountedRef.current) {
        DEBUG("Component unmounted → abort navigation");
        return;
      }

      setLoading(false);

      DEBUG("Navigation to ChatRoom:", room_id);

      navigate(
        `/chat/${room_id}?userName=${encodeURIComponent(
          name
        )}&major=${major}&activeModerator=${activeModerator}`
      );
    };

    const onError = (err) => {
      DEBUG("ERROR received on createRoom:", err);

      cleanup();
      if (!mountedRef.current) return;

      setLoading(false);
      alert(err?.message || "Failed to create room.");
    };

    socket.on("room_created", onCreated);
    socket.on("error", onError);

    DEBUG("EMITTING create_room:", {
      user_name: name,
      major,
      moderatorMode: activeModerator ? "active" : "passive",
    });

    socket.emit("create_room", {
      user_name: name,
      major,
      moderatorMode: activeModerator ? "active" : "passive",
    });
  };

  // ------------------------------------------------------------
  // 🔗 Join Room (no socket.emit here)
  // ------------------------------------------------------------
  const joinRoom = () => {
    DEBUG("joinRoom CLICKED");

    if (loading) {
      DEBUG("Currently loading → cancelled");
      return;
    }

    const name = userName.trim();
    const id = roomId.trim();

    if (!name) {
      DEBUG("UserName empty → alert");
      alert("Enter your name.");
      return;
    }
    if (!id) {
      DEBUG("RoomID empty → alert");
      alert("Enter Room ID.");
      return;
    }

    DEBUG("Navigating to chat → join_room will be emitted inside ChatRoom.jsx");

    setLoading(true);
    setLoading(false);

    navigate(
      `/chat/${encodeURIComponent(
        id
      )}?userName=${encodeURIComponent(name)}&major=${major}&activeModerator=${
        activeModerator
      }`
    );
  };

  // ------------------------------------------------------------
  // 🎨 UI
  // ------------------------------------------------------------
  return (
    <div className="min-h-screen w-screen overflow-y-auto bg-gradient-to-br from-green-50 via-blue-50 to-green-100 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Shareable Links Section */}
        <ShareableLinks />

        {/* Original Create/Join Room Section */}
        <div className="bg-white/90 backdrop-blur-md p-6 rounded-2xl shadow-lg max-w-md mx-auto border border-blue-100 hover:shadow-[0_0_25px_rgba(59,130,246,0.3)] transition">
          <h1 className="text-xl font-semibold mb-6 text-center text-blue-700">
            Or Create / Join Room Manually
          </h1>

        {/* 👤 User Name */}
        <div className="relative mb-4">
          <MdPerson className="absolute left-2 top-3 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Enter your name"
            value={userName}
            onChange={(e) => {
              DEBUG("Typing userName:", e.target.value);
              setUserName(e.target.value);
            }}
            className="pl-8 border border-gray-200 p-2 w-full rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-green-300"
            disabled={loading}
          />
        </div>

        {/* 🎓 Major */}
        <label className="block mb-1 text-gray-700 text-sm font-medium">
          Select your major
        </label>

        <select
          value={major}
          onChange={(e) => {
            DEBUG("Major changed:", e.target.value);
            setMajor(e.target.value);
          }}
          className="border border-gray-200 p-2 w-full rounded-md mb-4 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
          disabled={loading}
        >
          <optgroup label="STEM">
            <option value="computer_science">Computer Science</option>
            <option value="data_science">Data Science</option>
            <option value="engineering">Engineering</option>
            <option value="mathematics">Mathematics</option>
          </optgroup>

          <optgroup label="Humanities">
            <option value="education">Education</option>
            <option value="psychology">Psychology</option>
            <option value="sociology">Sociology</option>
          </optgroup>

          <optgroup label="Business">
            <option value="business">Business</option>
            <option value="economics">Economics</option>
          </optgroup>

          <optgroup label="Creative / Design">
            <option value="media">Media</option>
            <option value="design">Design</option>
            <option value="architecture">Architecture</option>
          </optgroup>

          <optgroup label="Health">
            <option value="nursing">Nursing</option>
            <option value="health_science">Health Science</option>
          </optgroup>
        </select>

        {/* 🧩 Enable Active Moderator */}
        <div className="flex items-center mb-4">
          <input
            id="active-moderator-toggle"
            type="checkbox"
            checked={activeModerator}
            onChange={(e) => {
              DEBUG("Active moderator toggled:", e.target.checked);
              setActiveModerator(e.target.checked);
            }}
            className="mr-2 accent-green-500"
          />
          <label
            htmlFor="active-moderator-toggle"
            className="text-sm text-gray-700 flex items-center gap-1"
          >
            <MdPsychology className="text-green-500" /> Enable Active Moderator
          </label>
        </div>

        {/* 🏗 Create Room */}
        <button
          onClick={createRoom}
          className={`flex items-center justify-center gap-2 text-white px-3 py-2 rounded-md w-full mb-4 text-sm font-medium transition shadow-md ${
            loading
              ? "bg-green-200 cursor-not-allowed"
              : "bg-gradient-to-r from-green-400 to-green-500 hover:from-green-500 hover:to-green-600 hover:shadow-lg hover:shadow-green-300/50"
          }`}
          disabled={loading}
        >
          <MdPlayArrow size={16} />
          {loading ? "Please wait…" : "Create Room"}
        </button>

        {/* Room ID Input */}
        <div className="relative mb-4">
          <MdMeetingRoom
            className="absolute left-2 top-3 text-gray-400"
            size={18}
          />
          <input
            type="text"
            placeholder="Enter Room ID"
            value={roomId}
            onChange={(e) => {
              DEBUG("Typing roomId:", e.target.value);
              setRoomId(e.target.value);
            }}
            className="pl-8 border border-gray-200 p-2 w-full rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
            disabled={loading}
          />
        </div>

        {/* 🔗 Join Room */}
        <button
          onClick={joinRoom}
          className={`flex items-center justify-center gap-2 text-white px-3 py-2 rounded-md w-full text-sm font-medium transition shadow-md ${
            loading
              ? "bg-blue-200 cursor-not-allowed"
              : "bg-gradient-to-r from-blue-400 to-blue-500 hover:from-blue-500 hover:to-blue-600 hover:shadow-lg hover:shadow-blue-300/50"
          }`}
          disabled={loading}
        >
          <MdLogin size={16} />
          {loading ? "Joining…" : "Join Room"}
        </button>
        </div>
      </div>
    </div>
  );
}
