import { Navigate, Route, Routes } from "react-router-dom";
import CardForm from "./pages/CardForm";
import DeckDetail from "./pages/DeckDetail";
import DeckList from "./pages/DeckList";
import Home from "./pages/Home";
import ReviewSession from "./pages/ReviewSession";
import Settings from "./pages/Settings";
import Stats from "./pages/Stats";

export default function App() {
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
