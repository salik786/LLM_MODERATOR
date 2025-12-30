// ============================================================
// path: src/components/ChatRoom.jsx
// FULL FIXED VERSION — WITH ULTRA DEBUG LOGS
// (No deletions. No modifications. Only added logging.)
// ============================================================

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useLocation, useNavigate } from "react-router-dom";
import { socket } from "../socket";
import {
  MdSend,
  MdMic,
  MdExitToApp,
  MdContentCopy,
  MdVolumeUp,
} from "react-icons/md";

// ============================================================
// 🔥 GLOBAL ULTRA DEBUG LOGGER
// ============================================================
const DEBUG = (...args) => {
  const timestamp = new Date().toISOString();
  console.log(`%c[CHATROOM DEBUG] ${timestamp}`, "color:#0088ff;", ...args);
};

export default function ChatRoom() {
  const { roomId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const userName = useMemo(
    () => new URLSearchParams(location.search).get("userName") || "",
    [location.search]
  );

  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState("");
  const [ready, setReady] = useState(false);
  const [recording, setRecording] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isLoadingFeedback, setIsLoadingFeedback] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recognitionRef = useRef(null);
  const bottomRef = useRef(null);
  const lastFinalTranscriptRef = useRef("");
  const usingSpeechRecognitionRef = useRef(false);

  // ============================================================
  // 🔔 Local Send Sound
  // ============================================================
  const [sendSound] = useState(() => {
    DEBUG("Initializing local send sound...");
    const audio = new Audio();
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    audio.play = () => {
      DEBUG("Send sound played");
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "triangle";
      osc.frequency.value = 440;
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.1);
      return ctx.resume();
    };
    return audio;
  });

  // ============================================================
  // ⚡ SOCKET HANDLING — WITH FULL LOGS
  // ============================================================
  useEffect(() => {
    DEBUG("useEffect triggered → roomId:", roomId, "userName:", userName);

    if (!roomId || !userName) {
      DEBUG("No roomId or userName. Returning...");
      return;
    }

    // Step 1: Remove old listeners
    DEBUG("Removing previous listeners...");
    socket.off("joined_room");
    socket.off("chat_history");
    socket.off("receive_message");

    // Step 2: Add listeners BEFORE emitting join_room
    DEBUG("Attaching listeners...");

    socket.on("joined_room", () => {
      DEBUG("joined_room RECEIVED → ready=true");
      setReady(true);
    });

    socket.on("chat_history", (d) => {
      DEBUG("chat_history RECEIVED:", d);
      setMessages(d.chat_history || []);
    });

    socket.on("receive_message", (d) => {
      DEBUG("receive_message RECEIVED:", d);

      setMessages((prev) => {
        const dup =
          prev.length > 0 &&
          prev[prev.length - 1].sender === d.sender &&
          prev[prev.length - 1].message === d.message;

        DEBUG("Duplicate message?", dup);

        return dup ? prev : [...prev, d];
      });
    });

    // Step 3: Emit join_room AFTER attaching listeners
    DEBUG("Emitting join_room:", { roomId, userName });
    socket.emit("join_room", { room_id: roomId, user_name: userName });

    return () => {
      DEBUG("Cleanup: removing listeners...");
      socket.off("joined_room");
      socket.off("chat_history");
      socket.off("receive_message");
    };
  }, [roomId, userName]);

  // Auto scroll
  useEffect(() => {
    DEBUG("Scrolling to bottom...");
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ============================================================
  // 💬 SEND MESSAGE
  // ============================================================
  const sendMessage = useCallback(() => {
    const trimmed = message.trim();

    DEBUG("SendMessage clicked. Trimmed:", trimmed);

    if (!trimmed) {
      DEBUG("Message empty → cancelled");
      return;
    }

    sendSound.play().catch(() => DEBUG("Send sound error"));

    setMessages((p) => [...p, { sender: userName, message: trimmed }]);

    DEBUG("Emitting send_message:", {
      room_id: roomId,
      sender: userName,
      message: trimmed,
    });

    socket.emit("send_message", {
      room_id: roomId,
      message: trimmed,
      sender: userName,
    });

    setMessage("");
  }, [message, roomId, userName, sendSound]);

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      DEBUG("Enter pressed → sending message");
      e.preventDefault();
      sendMessage();
    }
  };

  // ============================================================
  // 🎙️ RECORDING + TRANSCRIBING
  // ============================================================
  const shouldAppendText = (base, incoming) => {
    DEBUG("Checking shouldAppendText →", { base, incoming });

    if (!incoming || !incoming.trim()) return false;

    const cleanBase = base.trim().toLowerCase();
    const cleanIncoming = incoming.trim().toLowerCase();

    const result =
      cleanIncoming.length > 2 &&
      !cleanBase.endsWith(cleanIncoming) &&
      !cleanBase.includes(cleanIncoming.slice(0, 15));

    DEBUG("shouldAppendText result:", result);
    return result;
  };

  const animateTextAddition = (newText) => {
    DEBUG("Animating text addition:", newText);

    let i = 0;
    const interval = setInterval(() => {
      setMessage((prev) => prev + newText[i]);
      i++;
      if (i >= newText.length) {
        DEBUG("Animation done.");
        clearInterval(interval);
      }
    }, 40);
  };

  const toggleRecording = async () => {
    DEBUG("toggleRecording clicked → current state:", recording);

    if (!recording) {
      try {
        setIsTranscribing(true);

        const SpeechRecognition =
          window.SpeechRecognition || window.webkitSpeechRecognition;

        if (SpeechRecognition) {
          DEBUG("Using SpeechRecognition API");

          usingSpeechRecognitionRef.current = true;
          const recognition = new SpeechRecognition();
          recognition.lang = "en-US";
          recognition.continuous = true;
          recognition.interimResults = true;

          recognition.onresult = (event) => {
            DEBUG("SpeechRecognition.onresult:", event);

            let interim = "";

            for (let i = event.resultIndex; i < event.results.length; ++i) {
              const transcript = event.results[i][0].transcript.trim();

              DEBUG("Recognized transcript:", transcript);

              if (event.results[i].isFinal) {
                DEBUG("Final transcript:", transcript);

                if (
                  shouldAppendText(message, transcript) &&
                  transcript !== lastFinalTranscriptRef.current
                ) {
                  animateTextAddition(" " + transcript);
                  lastFinalTranscriptRef.current = transcript;
                }
              } else {
                interim += transcript;
              }
            }

            if (interim) {
              DEBUG("Interim transcript:", interim);
              setMessage(interim);
            }
          };

          recognition.onerror = (e) =>
            DEBUG("[SpeechRecognition ERROR]", e.error);

          recognition.onend = () => {
            DEBUG("SpeechRecognition ended");
            setIsTranscribing(false);
          };

          recognition.start();
          recognitionRef.current = recognition;

          setRecording(true);
          return;
        }

        // Fallback MediaRecorder
        DEBUG("Using MediaRecorder fallback");

        usingSpeechRecognitionRef.current = false;

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        DEBUG("MediaRecorder stream acquired");

        const rec = new MediaRecorder(stream, {
          mimeType: "audio/webm;codecs=opus",
        });

        audioChunksRef.current = [];

        rec.ondataavailable = (e) => {
          DEBUG("MediaRecorder dataavailable:", e.data?.size);
          if (e.data.size > 0) audioChunksRef.current.push(e.data);
        };

        rec.onstop = async () => {
          DEBUG("MediaRecorder STOP");

          const blob = new Blob(audioChunksRef.current, {
            type: "audio/webm",
          });

          const form = new FormData();
          form.append("file", blob, "rec.webm");

          try {
            DEBUG("Sending blob to STT API...");

            const response = await fetch(
              `${import.meta.env?.VITE_API_URL || "http://localhost:5000"}/stt`,
              { method: "POST", body: form }
            );

            const data = await response.json();
            DEBUG("STT RESPONSE:", data);

            if (
              data.text &&
              shouldAppendText(message, data.text) &&
              data.text !== lastFinalTranscriptRef.current
            ) {
              animateTextAddition(" " + data.text);
              lastFinalTranscriptRef.current = data.text;
            }
          } catch (err) {
            DEBUG("[STT ERROR]", err);
          } finally {
            setIsTranscribing(false);
          }
        };

        rec.start();
        mediaRecorderRef.current = rec;
        setRecording(true);
      } catch (err) {
        DEBUG("[MIC ERROR]", err);
        setIsTranscribing(false);
      }
    } else {
      DEBUG("Stopping recording...");

      if (usingSpeechRecognitionRef.current) {
        recognitionRef.current?.stop();
      } else {
        mediaRecorderRef.current?.stop();
      }

      usingSpeechRecognitionRef.current = false;
      setRecording(false);
      setIsTranscribing(false);
    }
  };

  // ============================================================
  // 🔊 TTS — Moderator Voice
  // ============================================================
  const playTTS = async (text) => {
    DEBUG("TTS REQUEST:", text);

    try {
      const cleaned = (text || "")
        .replace(/Moderator[:\-]?\s*/gi, "")
        .replace(/[^\p{L}\p{N}\s.,!?'"()\-]/gu, "")
        .replace(/\s{2,}/g, " ")
        .trim();

      DEBUG("TTS cleaned text:", cleaned);

      const response = await fetch(
        `${import.meta.env?.VITE_API_URL || "http://localhost:5000"}/tts`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: cleaned || text || "Hello!" }),
        }
      );

      DEBUG("TTS response.ok =", response.ok);

      if (!response.ok) return;

      const blob = await response.blob();
      DEBUG("TTS audio blob received");

      const audioURL = URL.createObjectURL(blob);
      const audio = new Audio(audioURL);
      audio.volume = 0.9;

      audio.onended = () => {
        DEBUG("TTS audio finished");
        URL.revokeObjectURL(audioURL);
      };

      audio.play();
    } catch (err) {
      DEBUG("[TTS ERROR]", err);
    }
  };

  // ============================================================
  // 🧾 END SESSION
  // ============================================================
  const endSession = () => {
    DEBUG("endSession CLICKED");

    setIsLoadingFeedback(true);

    socket.emit("end_session", { room_id: roomId, sender: userName });

    socket.once("feedback_generated", (d) => {
      DEBUG("feedback_generated RECEIVED:", d);

      setIsLoadingFeedback(false);

      if (d?.feedback) navigate("/feedback", { state: { feedback: d.feedback } });
    });
  };

  useEffect(() => {
    socket.on("session_ended", (d) => {
      DEBUG("session_ended RECEIVED:", d);

      const fbs = d?.feedbacks || {};
      const fb = fbs[userName] || "Session ended.";

      navigate("/feedback", { state: { feedback: fb } });
    });

    return () => socket.off("session_ended");
  }, [userName, navigate]);

  // ============================================================
  // UI
  // ============================================================
  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-green-50 via-blue-50 to-green-100">

      {/* Header */}
      <div className="bg-white border-b py-2 px-3 flex justify-between items-center shadow-sm text-xs text-gray-700">
        <span className="font-semibold text-blue-700">Room: {roomId}</span>

        <button
          onClick={() => {
            DEBUG("Room ID copied:", roomId);
            navigator.clipboard.writeText(roomId);
            setCopied(true);
            setTimeout(() => setCopied(false), 1200);
          }}
          className="flex items-center gap-1 px-2 h-7 text-[11px] bg-blue-500 hover:bg-blue-600 text-white rounded-md shadow transition"
        >
          <MdContentCopy size={13} />
          {copied ? "Copied!" : "Copy ID"}
        </button>
      </div>

      {/* Chat Area */}
      <div className="flex-grow overflow-auto p-3 space-y-3 text-sm">
        {messages.map((m, i) => {
          const key = `${m.sender}-${i}-${m.message.slice(0, 10)}`;
          const isMod = m.sender === "Moderator";
          const isMe = m.sender === userName;

          const bg = isMod
            ? "bg-yellow-100 border border-yellow-300"
            : isMe
            ? "bg-blue-200"
            : "bg-gray-200";

          const justify = isMod
            ? "justify-center"
            : isMe
            ? "justify-end"
            : "justify-start";

          return (
            <div key={key} className={`flex flex-col ${justify}`}>
              <div className={`flex items-start gap-2 ${justify}`}>
                {!isMe && !isMod && (
                  <img
                    src="https://api.dicebear.com/7.x/thumbs/png?seed=a"
                    className="w-7 h-7 rounded-full border border-gray-300"
                  />
                )}

                {isMod && (
                  <img
                    src="https://api.dicebear.com/7.x/bottts-neutral/png?seed=moderator"
                    className="w-9 h-9 rounded-full border border-yellow-400"
                  />
                )}

                <div
                  className={`px-3 py-2 rounded-lg shadow text-sm max-w-xs ${bg} relative`}
                >
                  {m.message}

                  {isMod && (
                    <button
                      onClick={() => {
                        DEBUG("Moderator TTS clicked for message:", m.message);
                        playTTS(m.message);
                      }}
                      className="absolute -bottom-2 -right-2 flex items-center justify-center w-7 h-7 rounded-full border text-white shadow-md bg-amber-500 hover:bg-amber-600 border-amber-700"
                      style={{ transform: "translate(6px, 6px)" }}
                    >
                      <MdVolumeUp size={14} />
                    </button>
                  )}
                </div>

                {isMe && !isMod && (
                  <img
                    src="https://api.dicebear.com/7.x/thumbs/png?seed=b"
                    className="w-7 h-7 rounded-full border border-blue-400"
                  />
                )}
              </div>

              <div
                className={`text-[10px] mt-1 text-gray-600 font-semibold ${
                  isMe
                    ? "text-right pr-8"
                    : isMod
                    ? "text-center"
                    : "text-left pl-8"
                }`}
              >
                {m.sender}
              </div>
            </div>
          );
        })}

        <div ref={bottomRef} />
      </div>

      {/* Input Area */}
      <div className="p-2 border-t bg-white flex justify-center">
        <div className="relative flex items-center gap-2 w-full max-w-2xl">
          <textarea
            rows={2}
            disabled={!ready}
            value={message}
            onChange={(e) => {
              DEBUG("Message typing:", e.target.value);
              setMessage(e.target.value);
            }}
            onKeyDown={handleKey}
            placeholder={
              !ready
                ? "Waiting..."
                : isTranscribing
                ? "🎧 Transcribing..."
                : "Type..."
            }
            className="flex-grow border px-2 py-1 rounded-lg text-sm focus:ring-2 focus:ring-blue-300 resize-none"
          />

          <button
            onClick={sendMessage}
            disabled={!message.trim() || !ready}
            className={`flex items-center justify-center w-16 h-7 rounded-md text-xs shadow transition ${
              ready
                ? "bg-blue-500 hover:bg-blue-600 text-white"
                : "bg-gray-300 text-gray-600"
            }`}
          >
            <MdSend size={13} className="mr-1" /> Send
          </button>

          <button
            onClick={toggleRecording}
            disabled={!ready}
            className={`flex items-center justify-center w-16 h-7 rounded-md text-xs shadow transition ${
              ready
                ? "bg-green-500 hover:bg-green-600 text-white"
                : "bg-gray-300 text-gray-600"
            }`}
          >
            <MdMic size={13} className="mr-1" />
            {recording ? "Stop" : "Mic"}
          </button>

          <button
            onClick={endSession}
            disabled={isLoadingFeedback}
            className="flex items-center justify-center w-20 h-7 bg-red-500 hover:bg-red-600 text-white rounded-md text-xs shadow transition"
          >
            {isLoadingFeedback ? "⏳..." : (
              <>
                <MdExitToApp size={13} className="mr-1" /> End
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
