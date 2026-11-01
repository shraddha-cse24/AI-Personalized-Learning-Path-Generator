const STATUS = {
  weak:       { label: "Needs revision", color: "text-weak",     bar: "bg-weak" },
  learning:   { label: "In progress",    color: "text-learning", bar: "bg-learning" },
  proficient: { label: "Almost there",   color: "text-good",     bar: "bg-good" },
  mastered:   { label: "Mastered",       color: "text-good",     bar: "bg-good" },
  new:        { label: "Not started",    color: "text-new",      bar: "bg-new" },
};
const ACTION = { revise: "Start revision", practice: "Practice", advance: "Continue", start: "Start topic", review: "Review" };

export default function TopicCard({ step, last, done, onToggle }) {
  const s = STATUS[step.status] ?? STATUS.new;
  const pct = Math.round(step.mastery * 100);
  return (
    <li className="relative flex gap-4">
      <div className="flex flex-col items-center">
        <span className={`mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-full border-2 text-sm font-semibold ${done ? "border-good bg-good text-white" : "border-ink bg-white"}`}>
          {done ? "✓" : step.rank}
        </span>
        {!last && <span className="w-0.5 grow bg-line" />}
      </div>
      <article className={`mb-6 w-full rounded-lg border border-line bg-white p-5 ${done ? "opacity-60" : ""}`}>
        <p className={`text-sm font-medium ${s.color}`}>{s.label}</p>
        <h3 className="mt-1 text-lg font-semibold">{step.name}</h3>
        <p className="mt-1 text-sm text-new">{step.reason}</p>
        <div className="mt-4" aria-label={`Mastery ${pct}%`}>
          <div className="h-2 rounded-full bg-line"><div className={`h-2 rounded-full ${s.bar}`} style={{ width: `${pct}%` }} /></div>
          <p className="mt-1 text-xs text-new">Mastery {pct}% · {step.attempts} attempts · {Math.round(step.accuracy * 100)}% correct</p>
        </div>
        <div className="mt-4 flex gap-3">
          <button className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:opacity-90">{ACTION[step.action] ?? "Practice"}</button>
          <button onClick={onToggle} className="rounded-md border border-line px-4 py-2 text-sm hover:bg-paper">
            {done ? "Mark as not done" : "Mark as done"}
          </button>
        </div>
      </article>
    </li>
  );
}
