import React from "react";
import { useNavigate, useLocation } from "react-router-dom";

export default function FeedbackPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const feedback = location.state?.feedback || "No feedback available.";

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-yellow-50 to-blue-100 p-8">
      <div className="max-w-3xl bg-white shadow-lg rounded-2xl p-8">
        <h1 className="text-2xl font-bold text-blue-700 mb-4 text-center">
          🌟 Session Feedback
        </h1>
        <p className="text-gray-800 leading-relaxed whitespace-pre-line">
          {feedback}
        </p>
        <div className="flex justify-center mt-8">
          <button
            onClick={() => navigate("/")}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg shadow transition"
          >
            Back to Home
          </button>
        </div>
      </div>
    </div>
  );
}
