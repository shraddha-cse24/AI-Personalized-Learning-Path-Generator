import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { mockQuestions } from "../data/mockData";
import { useAuth } from "../context/AuthContext";
import { submitAttempt } from "../services/api";

export default function Assessment() {
  const nav = useNavigate();
  const { user } = useAuth();
  const [i, setI] = useState(0);
  const [picked, setPicked] = useState(null);
  const [error, setError] = useState("");
  const q = mockQuestions[i];
  const isLast = i === mockQuestions.length - 1;

  async function next() {
    try {
      await submitAttempt(user.id, q.ucid, picked === q.answer);
      if (isLast) return nav("/path");
      setI(i + 1); setPicked(null); setError("");
    } catch {
      setError("Couldn't save your answer. Check your connection and try again.");
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <p className="text-sm text-new">Question {i + 1} of {mockQuestions.length}</p>
      <div className="mt-2 h-2 rounded-full bg-line"><div className="h-2 rounded-full bg-brand" style={{ width: `${((i + 1) / mockQuestions.length) * 100}%` }} /></div>
      <h1 className="mt-6 text-xl font-semibold">{q.text}</h1>
      <div className="mt-5 space-y-3">
        {q.options.map((o) => (
          <button key={o} onClick={() => setPicked(o)} aria-pressed={picked === o}
            className={`w-full rounded-md border px-4 py-3 text-left ${picked === o ? "border-brand bg-brand/10 font-medium" : "border-line bg-white hover:bg-paper"}`}>{o}</button>
        ))}
      </div>
      {error && <p role="alert" className="mt-4 text-sm text-weak">{error}</p>}
      <button disabled={!picked} onClick={next} className="mt-6 rounded-md bg-brand px-6 py-2.5 font-medium text-white disabled:opacity-40">
        {isLast ? "See my path" : "Next question"}
      </button>
    </div>
  );
}
