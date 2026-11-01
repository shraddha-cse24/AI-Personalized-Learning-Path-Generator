import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { useAuth } from "../context/AuthContext";
import { getMastery } from "../services/api";

export default function Dashboard() {
  const { user } = useAuth();
  const [topics, setTopics] = useState([]);
  useEffect(() => { getMastery(user.id).then((d) => setTopics(d.topics)); }, []);

  const avg = topics.length ? Math.round((topics.reduce((a, t) => a + t.mastery, 0) / topics.length) * 100) : 0;
  const weak = topics.filter((t) => t.status === "weak");
  const data = topics.map((t) => ({ name: t.name.length > 18 ? t.name.slice(0, 18) + "…" : t.name, mastery: Math.round(t.mastery * 100) }));

  return (
    <>
      <h1 className="text-3xl font-bold">Your progress</h1>
      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-line bg-white p-5"><p className="text-sm text-new">Average mastery</p><p className="mt-1 text-3xl font-semibold">{avg}%</p></div>
        <div className="rounded-lg border border-line bg-white p-5"><p className="text-sm text-new">Topics tracked</p><p className="mt-1 text-3xl font-semibold">{topics.length}</p></div>
        <div className="rounded-lg border border-line bg-white p-5"><p className="text-sm text-new">Need revision</p><p className="mt-1 text-3xl font-semibold text-weak">{weak.length}</p></div>
      </div>
      <section className="mt-6 rounded-lg border border-line bg-white p-5">
        <h2 className="font-semibold">Mastery by topic</h2>
        <div className="mt-4 h-64">
          <ResponsiveContainer>
            <BarChart data={data}>
              <XAxis dataKey="name" tick={{ fontSize: 11 }} /><YAxis domain={[0, 100]} /><Tooltip />
              <Bar dataKey="mastery" fill="#2f4bd8" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </>
  );
}
