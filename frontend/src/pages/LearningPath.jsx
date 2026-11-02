import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import TopicCard from "../components/TopicCard";
import { getLearningPath } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { ErrorBox, Skeleton } from "../components/ui";

export default function LearningPath() {
  const { user } = useAuth();
  const [path, setPath] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { getLearningPath().then(setPath).catch((e) => setError(e.message)); }, []);

  if (error) return <ErrorBox message={error} />;
  if (!path) return <Skeleton />;

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold">{user.name}'s learning path</h1>
          <p className="mt-1 text-new">
            {path.answered === 0 ? "A starting path based on your level. It adapts after every answer." : `Based on your ${path.answered} answers so far. Start at the top.`}
          </p>
        </div>
        <Link to="/practice" className="rounded-md bg-brand px-5 py-2.5 text-sm font-medium text-white hover:opacity-90">Practise now</Link>
      </div>
      {path.notes?.length > 0 && (
        <ul className="mt-5 space-y-1 rounded-lg bg-paper p-4 text-sm text-new">{path.notes.map((n) => <li key={n}>{n}</li>)}</ul>
      )}
      <ol className="mt-8">
        {path.steps.map((s, i) => <TopicCard key={s.concept_code} step={s} last={i === path.steps.length - 1} />)}
      </ol>
      <p className="text-sm text-new">{path.locked_topics} more topics are locked until you master the earlier ones.</p>
    </>
  );
}
