// ============================================================
// path: src/socket.js
// 🔥 FULL FIXED VERSION — NO .env REQUIRED — Guaranteed Connect
// ============================================================

import { io } from "socket.io-client";

// ============================================================
// 🔥 Ultra Debug Logger
// ============================================================
const DEBUG_SOCKET = (...args) => {
  const timestamp = new Date().toISOString();
  console.log(
    `%c[SOCKET DEBUG ${timestamp}]`,
    "color:#ff0066; font-weight:bold;",
    ...args
  );
};

DEBUG_SOCKET("Initializing socket…");

// ============================================================
// 🟦 FORCE SOCKET TO USE POLLING FIRST, THEN UPGRADE
// ============================================================

const SERVER_URL = "http://localhost:5000";

DEBUG_SOCKET("FORCED SERVER_URL =", SERVER_URL);

export const socket = io(SERVER_URL, {
  transports: ["polling", "websocket"], // 💥 مهم جدًا: يبدأ بـ polling
  upgrade: true, // يسمح بالترقية إلى websocket
  autoConnect: true,
  reconnection: true,
  reconnectionDelay: 500,
  reconnectionAttempts: Infinity
});

// ============================================================
// 🔥 SOCKET LIFECYCLE LOGGING
// ============================================================

socket.on("connect", () => {
  DEBUG_SOCKET("CONNECTED ✓ socket.id =", socket.id);
  DEBUG_SOCKET("Transport Now →", socket.io.engine.transport.name);
});

socket.on("connect_error", (err) => {
  DEBUG_SOCKET("CONNECT ERROR →", err?.message || err);
});

socket.on("disconnect", (reason) => {
  DEBUG_SOCKET("DISCONNECTED →", reason);
});

socket.on("reconnect_attempt", (attempt) => {
  DEBUG_SOCKET("RECONNECT ATTEMPT #", attempt);
});

socket.on("reconnect", () => {
  DEBUG_SOCKET("RECONNECTED ✓ New ID =", socket.id);
});

socket.onAny((event, ...args) => {
  DEBUG_SOCKET(`📥 EVENT RECEIVED → "${event}"`, args);
});

// ============================================================
// 📤 GLOBAL EMIT PATCH
// ============================================================
const originalEmit = socket.emit.bind(socket);

socket.emit = (eventName, payload, ...rest) => {
  DEBUG_SOCKET(`📤 EMIT → "${eventName}"`, payload);
  return originalEmit(eventName, payload, ...rest);
};

DEBUG_SOCKET("Ultra debug patch loaded ✓");
