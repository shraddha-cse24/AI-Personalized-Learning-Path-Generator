import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import TopicCard from "../components/TopicCard";
import { useAuth } from "../context/AuthContext";
import { getLearningPath } from "../services/api";

export default function LearningPath() {
  const [steps, setSteps] = useState(null);
  const [error, setError] = useState("");
  const [done, setDone] = useState({});
  const { user: student } = useAuth();

  useEffect(() => {
    getLearningPath(student.id).then((d) => setSteps(d.steps)).catch((e) => setError(e.message));
  }, []);

  if (error) return <p role="alert" className="text-weak">Couldn't load your path: {error}. Is the backend running?</p>;
  if (!steps) return <p className="text-new">Building your path…</p>;
  if (steps.length === 0) return <p>No path yet. <Link className="text-brand underline" to="/start">Take the quiz</Link> to get one.</p>;

  const completed = Object.values(done).filter(Boolean).length;
  return (
    <>
      <h1 className="text-3xl font-bold">{student.name ? `${student.name}'s learning path` : "Your learning path"}</h1>
      <p className="mt-1 text-new">{completed} of {steps.length} topics done. Start at the top.</p>
      <ol className="mt-8">
        {steps.map((s, idx) => (
          <TopicCard key={s.concept_code} step={s} last={idx === steps.length - 1}
            done={!!done[s.concept_code]} onToggle={() => setDone({ ...done, [s.concept_code]: !done[s.concept_code] })} />
        ))}
      </ol>
    </>
  );
}
