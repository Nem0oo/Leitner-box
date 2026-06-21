import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

export function Layout({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="app-shell">
      <header className="top-bar">
        <h1>{title}</h1>
      </header>
      <main className="app-content">{children}</main>
      <nav className="bottom-nav">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
          Accueil
        </NavLink>
        <NavLink to="/decks" className={({ isActive }) => (isActive ? "active" : "")}>
          Decks
        </NavLink>
        <NavLink to="/stats" className={({ isActive }) => (isActive ? "active" : "")}>
          Stats
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => (isActive ? "active" : "")}>
          Réglages
        </NavLink>
      </nav>
    </div>
  );
}
