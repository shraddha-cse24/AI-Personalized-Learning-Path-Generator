import { Link } from "react-router-dom";
import { Card, Chip, STATUS, pct } from "./ui";

const ACTION = { revise: "Revise", practice: "Practice", advance: "Start next", review: "Review" };

export default function TopicCard({ step, last }) {
  const s = STATUS[step.status] ?? STATUS.new;
  const m = pct(step.mastery);
  return (
    <li className="flex gap-4">
      <div className="flex flex-col items-center">
        <span className="mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-ink text-sm font-semibold text-white">{step.rank}</span>
        {!last && <span className="w-0.5 grow bg-line" />}
      </div>
      <Card className="mb-5 w-full">
        <div className="flex flex-wrap items-center gap-2">
          <Chip status={step.status} />
          <span className="text-xs font-medium uppercase tracking-wide text-new">{ACTION[step.action] ?? step.action}</span>
        </div>
        <h3 className="mt-2 text-lg font-semibold">{step.name}</h3>
        <p className="text-xs text-new">{step.area_name}</p>
        <p className="mt-2 text-sm">{step.reason}</p>
        <div className="mt-4">
          <div className="flex justify-between text-xs text-new">
            <span>{m == null ? "Not started yet" : `Mastery ${m}%`}</span>
            <span>{step.attempts} attempt{step.attempts === 1 ? "" : "s"}{step.attempts > 0 && ` · ${pct(step.accuracy)}% correct`}</span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-line" role="progressbar" aria-valuenow={m ?? 0} aria-valuemin={0} aria-valuemax={100}>
            <div className={`h-2 rounded-full ${s.bar}`} style={{ width: `${m ?? 0}%` }} />
          </div>
        </div>
        <Link to={`/practice?topic=${step.concept_code}`} className="mt-4 inline-block text-sm font-medium text-brand underline">Practise this topic</Link>
        {step.exercises?.length > 0 && (
          <div className="mt-4 border-t border-line pt-3">
            <p className="text-xs font-medium text-new">Up next in this topic</p>
            <ul className="mt-2 space-y-1.5 text-sm">
              {step.exercises.map((e) => (
                <li key={e.ucid} className="flex justify-between gap-3">
                  <span>{e.label}</span>
                  <span className="shrink-0 text-new">{pct(e.predicted_p_correct)}% chance of success</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>
    </li>
  );
}
