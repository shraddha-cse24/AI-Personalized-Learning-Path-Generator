import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { getMastery } from "../services/api";
import { Card, Chip, ErrorBox, Skeleton, STATUS, Stat, pct } from "../components/ui";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { getMastery().then(setData).catch((e) => setError(e.message)); }, []);

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Skeleton />;

  const c = data.status_counts;
  const chart = Object.keys(STATUS).map((k) => ({ key: k, name: STATUS[k].label, count: c[k] ?? 0 }));
  const attempted = data.topics.filter((t) => t.attempts > 0).sort((a, b) => a.mastery - b.mastery);
  const unlocked = data.topics.filter((t) => t.unlocked).length;

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold">Your progress</h1>
          <p className="mt-1 text-sm text-new">Curriculum mastery, attempt tracking, and topic statuses.</p>
        </div>
        <Link to="/practice" className="rounded-md bg-brand px-5 py-2.5 text-sm font-medium text-white hover:opacity-90">
          Continue Practice →
        </Link>
      </div>
      <div className="mt-6 grid gap-4 grid-cols-2 lg:grid-cols-4">
        <Stat label="Exercises answered" value={data.answered} />
        <Stat label="Overall accuracy" value={data.accuracy == null ? "–" : `${pct(data.accuracy)}%`} />
        <Stat label="Topics unlocked" value={`${unlocked}/${data.topics.length}`} />
        <Stat label="Need revision" value={c.weak} tone={c.weak ? "text-weak" : ""} />
      </div>
      {data.answered === 0 ? (
        <Card className="mt-6 text-center py-8">
          <p className="text-lg font-semibold">No activity recorded yet</p>
          <p className="mt-1 text-sm text-new">Start answering exercises to see your mastery metrics and progress charts.</p>
          <Link to="/practice" className="mt-4 inline-block rounded-md bg-brand px-5 py-2.5 text-sm font-medium text-white hover:opacity-90">
            Answer your first exercise
          </Link>
        </Card>
      ) : (
        <>
          <Card className="mt-6">
            <h2 className="font-semibold">Topics by status</h2>
            <div className="mt-4 h-60">
              <ResponsiveContainer>
                <BarChart data={chart}><XAxis dataKey="name" tick={{ fontSize: 12 }} /><YAxis allowDecimals={false} /><Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>{chart.map((d) => <Cell key={d.key} fill={STATUS[d.key].hex} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card className="mt-6 overflow-x-auto">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">Topics you've practised</h2>
              <span className="text-xs text-new">{attempted.length} active topics</span>
            </div>
            <table className="mt-3 w-full min-w-[34rem] text-left text-sm">
              <thead className="text-new">
                <tr>
                  <th className="py-2 font-medium">Topic</th>
                  <th className="font-medium">Attempts</th>
                  <th className="font-medium">Accuracy</th>
                  <th className="font-medium">Mastery</th>
                  <th className="font-medium">Status</th>
                  <th className="font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody>{attempted.map((t) => (
                <tr key={t.concept_code} className="border-t border-line">
                  <td className="py-2.5 pr-3 font-medium text-ink">{t.name}</td>
                  <td>{t.attempts}</td>
                  <td>{pct(t.accuracy)}%</td>
                  <td>{pct(t.mastery)}%</td>
                  <td><Chip status={t.status} /></td>
                  <td className="text-right">
                    <Link to={`/practice?topic=${t.concept_code}`} className="rounded px-2.5 py-1 text-xs font-semibold text-brand hover:bg-brand/10">
                      Practise →
                    </Link>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </Card>
        </>
      )}
    </>
  );
}
