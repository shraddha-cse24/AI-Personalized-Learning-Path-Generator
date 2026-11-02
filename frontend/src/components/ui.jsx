export const STATUS = {
  weak:       { label: "Needs revision", chip: "bg-weak/10 text-weak",           bar: "bg-weak",      hex: "#c2410c" },
  learning:   { label: "In progress",    chip: "bg-learning/10 text-learning",   bar: "bg-learning",  hex: "#b7791f" },
  proficient: { label: "Proficient",     chip: "bg-good/10 text-good",           bar: "bg-good",      hex: "#15803d" },
  mastered:   { label: "Mastered",       chip: "bg-good/15 text-good",           bar: "bg-good",      hex: "#166534" },
  new:        { label: "Not started",    chip: "bg-new/10 text-new",             bar: "bg-new",       hex: "#64748b" },
};
export const pct = (x) => (x == null ? null : Math.round(x * 100));

export const Chip = ({ status }) => (
  <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${(STATUS[status] ?? STATUS.new).chip}`}>
    {(STATUS[status] ?? STATUS.new).label}
  </span>
);

export const Card = ({ className = "", children }) => (
  <div className={`rounded-xl border border-line bg-white p-5 shadow-[0_1px_2px_rgba(27,37,64,0.04)] ${className}`}>{children}</div>
);

export const Stat = ({ label, value, tone = "" }) => (
  <Card><p className="text-sm text-new">{label}</p><p className={`mt-1 text-3xl font-semibold ${tone}`}>{value}</p></Card>
);

export const ErrorBox = ({ message }) => (
  <div role="alert" className="rounded-lg border border-weak/30 bg-weak/5 p-4 text-sm text-weak">{message}</div>
);

export const Skeleton = ({ rows = 3 }) => (
  <div className="space-y-4" aria-busy="true" aria-label="Loading">
    {Array.from({ length: rows }).map((_, i) => <div key={i} className="h-28 animate-pulse rounded-xl bg-line/60" />)}
  </div>
);
