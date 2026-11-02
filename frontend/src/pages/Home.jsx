import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Card } from "../components/ui";

const steps = [
  ["Choose your starting level", "Beginner or intermediate, so you don't repeat what you already know."],
  ["Practise exercises picked for you", "Each one is chosen so it's challenging but within reach, using a model trained on real student data."],
  ["Watch your path adapt", "Weak topics come back for revision, strong topics move on, and new topics unlock as you master the basics."],
];

export default function Home() {
  const { user, profile } = useAuth();
  return (
    <>
      <section className="py-8 sm:py-14">
        <p className="text-sm font-medium text-brand">Adaptive mathematics learning</p>
        <h1 className="mt-3 max-w-2xl text-4xl font-bold leading-tight sm:text-5xl">Practise what you actually need next.</h1>
        <p className="mt-5 max-w-xl text-lg text-new">
          Every answer you give updates your learning path. Topics you struggle with get revisited, and topics you've mastered get left behind. Covers school mathematics for Grades 1–9 (about ages 6–15), using real student data from Junyi Academy.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link to={user ? (profile?.onboarding_completed ? "/practice" : "/start") : "/register"} className="rounded-md bg-brand px-6 py-3 font-medium text-white hover:opacity-90">
            {user ? "Continue learning" : "Create a free account"}
          </Link>
          {!user && <Link to="/login" className="rounded-md border border-line bg-white px-6 py-3 font-medium hover:bg-paper">Log in</Link>}
        </div>
      </section>
      <ol className="grid gap-4 sm:grid-cols-3">
        {steps.map(([t, d], i) => (
          <li key={t}><Card className="h-full"><p className="text-sm font-semibold text-brand">Step {i + 1}</p><p className="mt-1 font-semibold">{t}</p><p className="mt-1 text-sm text-new">{d}</p></Card></li>
        ))}
      </ol>
    </>
  );
}
