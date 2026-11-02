import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getNextExercises, submitAttempt } from "../services/api";
import { Card, ErrorBox, Skeleton, pct } from "../components/ui";

export default function Practice() {
  const topic = useSearchParams()[0].get("topic");
  const [queue, setQueue] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [count, setCount] = useState(0);
  const [flash, setFlash] = useState("");

  const load = useCallback(async () => {
    try { setQueue(await getNextExercises(3, topic)); setError(""); } catch (e) { setError(e.message); }
  }, [topic]);
  useEffect(() => { load(); }, [load]);

  async function answer(ex, correct) {
    setBusy(true); setError("");
    try {
      await submitAttempt(ex.ucid, correct);
      setCount((c) => c + 1);
      setFlash(correct 
        ? { text: "✓ Nice! Your answer was recorded and your path has been updated.", type: "good" }
        : { text: "✓ Noted. This topic was marked for revision in your path.", type: "weak" }
      );
      await load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  if (!queue && !error) return <Skeleton rows={2} />;
  const ex = queue?.[0];

  return (
    <div className="mx-auto max-w-xl">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h1 className="text-3xl font-bold">{topic ? "Topic Practice" : "Adaptive Practice"}</h1>
          {topic && (
            <div className="mt-2 flex items-center gap-2">
              <span className="inline-flex items-center rounded-full bg-brand/10 px-3 py-0.5 text-xs font-medium text-brand">
                Topic ID: {topic}
              </span>
              <Link to="/practice" className="text-xs text-new hover:text-ink underline">
                Clear filter (practice all)
              </Link>
            </div>
          )}
        </div>
        <p className="text-sm font-medium text-new">{count} answered this session</p>
      </div>
      {flash && (
        <div role="status" className={`mt-3 flex items-center justify-between rounded-lg p-3 text-sm ${flash.type === 'good' ? 'bg-good/10 text-good border border-good/20' : 'bg-weak/10 text-weak border border-weak/20'}`}>
          <span>{flash.text}</span>
          <button onClick={() => setFlash("")} className="text-xs opacity-60 hover:opacity-100 ml-2" aria-label="Dismiss">✕</button>
        </div>
      )}
      {error && <div className="mt-4"><ErrorBox message={error} /></div>}
      {ex ? (
        <Card className="mt-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-brand">{ex.topic}</span>
            <span className="text-xs text-new">Queue: {queue.length} available</span>
          </div>
          <h2 className="mt-2 text-xl font-semibold">{ex.label}</h2>
          <p className="mt-2 text-sm text-ink/80">{ex.reason}</p>
          <div className="mt-3 flex items-center gap-2 text-sm">
            <span className="text-new">Predicted chance of success:</span>
            <strong className="rounded bg-paper px-2 py-0.5 text-ink font-semibold">{pct(ex.predicted_p_correct)}%</strong>
          </div>
          <div className="mt-5 rounded-lg border border-line/60 bg-paper p-4 text-sm text-ink/80">
            <p className="font-medium text-ink">Instructions:</p>
            <p className="mt-1">Work this exercise out on your own. Then self-report your result below — our recommendation model uses your accuracy to immediately rebalance your path.</p>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-3">
            <button
              disabled={busy}
              onClick={() => answer(ex, true)}
              className="flex items-center justify-center gap-1.5 rounded-lg bg-good py-3 font-medium text-white transition hover:opacity-90 disabled:opacity-50"
            >
              <span>✓</span> I got it right
            </button>
            <button
              disabled={busy}
              onClick={() => answer(ex, false)}
              className="flex items-center justify-center gap-1.5 rounded-lg border border-line bg-white py-3 font-medium text-ink transition hover:bg-paper disabled:opacity-50"
            >
              <span>✕</span> I got it wrong
            </button>
          </div>
        </Card>
      ) : !error && (
        <Card className="mt-6 text-center py-8">
          <p className="text-lg font-semibold">No more exercises available right now</p>
          <p className="mt-1 text-sm text-new">You've covered the available exercises in this topic. Check your learning path to see newly unlocked topics!</p>
          <Link to="/path" className="mt-4 inline-block rounded-md bg-brand px-5 py-2.5 text-sm font-medium text-white hover:opacity-90">
            View Learning Path
          </Link>
        </Card>
      )}
      <div className="mt-6 flex items-center justify-between text-sm">
        <Link to="/path" className="text-brand underline">← Back to learning path</Link>
        <Link to="/dashboard" className="text-new hover:text-ink">View progress & analytics →</Link>
      </div>
    </div>
  );
}
