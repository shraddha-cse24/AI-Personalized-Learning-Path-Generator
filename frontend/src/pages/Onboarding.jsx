import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { SUBJECTS } from "../config/subjects";

export default function Onboarding() {
  const nav = useNavigate();
  const [subject, setSubject] = useState(SUBJECTS[0].id);
  const [level, setLevel] = useState("beginner");

  function submit(e) {
    e.preventDefault();
    localStorage.setItem("profile", JSON.stringify({ subject, level }));
    nav("/assessment");
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-lg space-y-5 rounded-lg border border-line bg-white p-6">
      <h1 className="text-2xl font-bold">Set up your path</h1>
      <label className="block text-sm font-medium">What do you want to learn?
        <select value={subject} onChange={(e) => setSubject(e.target.value)} className="mt-1 w-full rounded-md border border-line px-3 py-2">
          {SUBJECTS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
      </label>
      <fieldset>
        <legend className="text-sm font-medium">Your current level</legend>
        <div className="mt-2 flex gap-4 text-sm">
          {["beginner", "intermediate", "advanced"].map((l) => (
            <label key={l} className="flex items-center gap-2"><input type="radio" checked={level === l} onChange={() => setLevel(l)} />{l}</label>
          ))}
        </div>
      </fieldset>
      <button className="w-full rounded-md bg-brand py-2.5 font-medium text-white hover:opacity-90">Start quiz</button>
    </form>
  );
}
