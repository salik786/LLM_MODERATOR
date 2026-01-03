// =========================
// Shareable Links Component
// Shows quick join links for researchers to share
// =========================
import React, { useState } from 'react';
import { MdContentCopy, MdCheckCircle, MdPsychology, MdAutoMode } from 'react-icons/md';

export default function ShareableLinks() {
  const [copiedActive, setCopiedActive] = useState(false);
  const [copiedPassive, setCopiedPassive] = useState(false);

  const baseUrl = window.location.origin;
  const activeLink = `${baseUrl}/join/active`;
  const passiveLink = `${baseUrl}/join/passive`;

  const copyToClipboard = async (text, setterFunc) => {
    try {
      await navigator.clipboard.writeText(text);
      setterFunc(true);
      setTimeout(() => setterFunc(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
      alert('Failed to copy link');
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl p-8 mb-6">
      <div className="text-center mb-6">
        <h2 className="text-3xl font-bold text-gray-800 mb-2">
          Quick Join Links
        </h2>
        <p className="text-gray-600">
          Share these links with participants for instant access
        </p>
      </div>

      <div className="space-y-4">
        {/* Active Mode Link */}
        <div className="border-2 border-indigo-200 rounded-xl p-4 hover:border-indigo-400 transition">
          <div className="flex items-center mb-2">
            <MdPsychology className="text-2xl text-indigo-600 mr-2" />
            <h3 className="text-lg font-semibold text-gray-800">
              Active Mode
            </h3>
          </div>
          <p className="text-sm text-gray-600 mb-3">
            AI actively engages and asks questions
          </p>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={activeLink}
              readOnly
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm font-mono"
            />
            <button
              onClick={() => copyToClipboard(activeLink, setCopiedActive)}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition flex items-center gap-2"
            >
              {copiedActive ? (
                <>
                  <MdCheckCircle className="text-xl" />
                  Copied!
                </>
              ) : (
                <>
                  <MdContentCopy className="text-xl" />
                  Copy
                </>
              )}
            </button>
          </div>
        </div>

        {/* Passive Mode Link */}
        <div className="border-2 border-purple-200 rounded-xl p-4 hover:border-purple-400 transition">
          <div className="flex items-center mb-2">
            <MdAutoMode className="text-2xl text-purple-600 mr-2" />
            <h3 className="text-lg font-semibold text-gray-800">
              Passive Mode
            </h3>
          </div>
          <p className="text-sm text-gray-600 mb-3">
            Story auto-advances at intervals
          </p>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={passiveLink}
              readOnly
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm font-mono"
            />
            <button
              onClick={() => copyToClipboard(passiveLink, setCopiedPassive)}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition flex items-center gap-2"
            >
              {copiedPassive ? (
                <>
                  <MdCheckCircle className="text-xl" />
                  Copied!
                </>
              ) : (
                <>
                  <MdContentCopy className="text-xl" />
                  Copy
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <h4 className="font-semibold text-gray-800 mb-2">📋 How it works:</h4>
        <ul className="text-sm text-gray-700 space-y-1">
          <li>• Participants click the link to join automatically</li>
          <li>• Max 3 participants per room</li>
          <li>• New rooms created automatically when full</li>
          <li>• No signup or login required</li>
        </ul>
      </div>
    </div>
  );
}
