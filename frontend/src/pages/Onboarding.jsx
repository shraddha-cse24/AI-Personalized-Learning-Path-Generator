import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { updateProfile } from "../services/api";
import { AVAILABLE_SUBJECTS, SUBJECTS } from "../config/subjects";
import { ErrorBox } from "../components/ui";

const LEVELS = [
  ["beginner", "Beginner", "Start from the basics: counting, number sense, simple operations."],
  ["intermediate", "Intermediate", "I'm comfortable with elementary maths and want to move on."],
  ["advanced", "Advanced", "I've covered most of the junior-level material already."],
];

export default function Onboarding() {
  const { user, profile, refreshProfile } = useAuth();
  const nav = useNavigate();
  const [subject, setSubject] = useState(AVAILABLE_SUBJECTS[0].id);
  const [level, setLevel] = useState("beginner");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (profile?.onboarding_completed) return <Navigate to="/path" replace />;

  async function submit(e) {
    e.preventDefault(); setBusy(true); setError("");
    try { await updateProfile(subject, level); await refreshProfile(); nav("/practice"); }
    catch (err) { setError(err.message); setBusy(false); }
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Welcome, {user.name}</h1>
        <p className="mt-1 text-new">Two quick choices and you're ready to practise.</p>
      </div>
      <label className="block text-sm font-medium">What do you want to learn?
        <select value={subject} onChange={(e) => setSubject(e.target.value)} className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2">
          {SUBJECTS.map((s) => <option key={s.id} value={s.id} disabled={!s.available}>{s.label}{s.available ? "" : " (coming soon)"}</option>)}
        </select>
        <span className="mt-1 block text-xs font-normal text-new">Computer science tracks need their own exercise data and model, so they're not available yet.</span>
      </label>
      <fieldset>
        <legend className="text-sm font-medium">Where should we start?</legend>
        <div className="mt-2 space-y-3">
          {LEVELS.map(([id, title, desc]) => (
            <label key={id} className={`block cursor-pointer rounded-xl border p-4 ${level === id ? "border-brand bg-brand/5" : "border-line bg-white hover:bg-paper"}`}>
              <input type="radio" name="level" className="sr-only" checked={level === id} onChange={() => setLevel(id)} />
              <span className="font-semibold">{title}</span><span className="mt-0.5 block text-sm text-new">{desc}</span>
            </label>
          ))}
        </div>
      </fieldset>
      {error && <ErrorBox message={error} />}
      <button disabled={busy} className="w-full rounded-md bg-brand py-3 font-medium text-white disabled:opacity-50">{busy ? "Saving…" : "Start practising"}</button>
    </form>
  );
}
