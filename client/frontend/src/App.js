// =========================
// path: src/App.jsx
// =========================
import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import RoomCreation from './components/RoomCreation';
import ChatRoom from './components/ChatRoom';
import FeedbackPage from './components/FeedbackPage';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<RoomCreation />} />
        <Route path="/chat/:roomId" element={<ChatRoom />} />
        <Route path="/feedback" element={<FeedbackPage />} />
      </Routes>
    </Router>
  );
}
