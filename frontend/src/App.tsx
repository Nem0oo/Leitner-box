import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import CardForm from "./pages/CardForm";
import DeckDetail from "./pages/DeckDetail";
import DeckList from "./pages/DeckList";
import Home from "./pages/Home";
import Login from "./pages/Login";
import ReviewSession from "./pages/ReviewSession";
import Settings from "./pages/Settings";
import Stats from "./pages/Stats";
import { api, UNAUTHORIZED_EVENT } from "./lib/api";

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/decks" element={<DeckList />} />
      <Route path="/decks/:deckId" element={<DeckDetail />} />
      <Route path="/cards/new" element={<CardForm />} />
      <Route path="/cards/:cardId/edit" element={<CardForm />} />
      <Route path="/review" element={<ReviewSession />} />
      <Route path="/review/:deckId" element={<ReviewSession />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/stats" element={<Stats />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    api
      .authStatus()
      .then((s) => setAuthed(s.authenticated))
      .catch(() => setAuthed(true));
  }, []);

  useEffect(() => {
    function onUnauthorized() {
      setAuthed(false);
    }
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  if (authed === null) return null;
  if (!authed) return <Login onSuccess={() => setAuthed(true)} />;
  return <AppRoutes />;
}
