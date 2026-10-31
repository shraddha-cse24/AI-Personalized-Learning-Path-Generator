import { Link } from "react-router-dom";

export default function Home() {
  return (
    <section className="py-10">
      <h1 className="max-w-2xl text-4xl font-bold leading-tight">Learn what you actually need next.</h1>
      <p className="mt-4 max-w-xl text-lg text-new">
        Answer a few questions. We find the topics you're ready for and the ones that need another look, then put them in the right order.
      </p>
      <Link to="/start" className="mt-8 inline-block rounded-md bg-brand px-6 py-3 font-medium text-white hover:opacity-90">Build my learning path</Link>
      <ol className="mt-14 grid gap-4 sm:grid-cols-3">
        {[["Tell us your goal", "Pick what you want to learn."], ["Take a short quiz", "We measure what you already know."], ["Follow your path", "Topics are ordered by what helps you most, and update as you improve."]].map(([t, d], i) => (
          <li key={t} className="rounded-lg border border-line bg-white p-5">
            <p className="font-semibold">{i + 1}. {t}</p><p className="mt-1 text-sm text-new">{d}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
