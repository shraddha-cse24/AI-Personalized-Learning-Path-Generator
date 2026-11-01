import { Routes, Route, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Home from "./pages/Home";
import Auth from "./pages/Auth";
import Onboarding from "./pages/Onboarding";
import Assessment from "./pages/Assessment";
import LearningPath from "./pages/LearningPath";
import Dashboard from "./pages/Dashboard";

const nav = ({ isActive }) => (isActive ? "font-semibold text-brand" : "text-new hover:text-ink");

export default function App() {
  const { user, logout } = useAuth();
  const go = useNavigate();
  const P = ({ children }) => <ProtectedRoute>{children}</ProtectedRoute>;

  return (
    <>
      <header className="border-b border-line bg-white">
        <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <NavLink to="/" className="text-lg font-semibold">PathFinder</NavLink>
          <div className="flex items-center gap-5 text-sm">
            {user ? (
              <>
                <NavLink to="/path" className={nav}>My path</NavLink>
                <NavLink to="/dashboard" className={nav}>Progress</NavLink>
                <button onClick={() => { logout(); go("/"); }} className="text-new hover:text-ink">Log out ({user.name})</button>
              </>
            ) : (
              <>
                <NavLink to="/login" className={nav}>Log in</NavLink>
                <NavLink to="/register" className={nav}>Sign up</NavLink>
              </>
            )}
          </div>
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Auth mode="login" />} />
          <Route path="/register" element={<Auth mode="register" />} />
          <Route path="/start" element={<P><Onboarding /></P>} />
          <Route path="/assessment" element={<P><Assessment /></P>} />
          <Route path="/path" element={<P><LearningPath /></P>} />
          <Route path="/dashboard" element={<P><Dashboard /></P>} />
        </Routes>
      </main>
    </>
  );
}
