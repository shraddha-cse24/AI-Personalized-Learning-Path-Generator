import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Auth({ mode }) {
  const isRegister = mode === "register";
  const { login, register } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      if (isRegister) await register(form.name, form.email, form.password);
      else await login(form.email, form.password);
      nav("/start");
    } catch (err) {
      setError(err.message);
    } finally { setBusy(false); }
  }

  const input = "mt-1 w-full rounded-md border border-line px-3 py-2";
  return (
    <form onSubmit={submit} className="mx-auto max-w-sm space-y-4 rounded-lg border border-line bg-white p-6">
      <h1 className="text-2xl font-bold">{isRegister ? "Create your account" : "Welcome back"}</h1>
      {isRegister && <label className="block text-sm font-medium">Name<input required value={form.name} onChange={set("name")} className={input} /></label>}
      <label className="block text-sm font-medium">Email<input required type="email" value={form.email} onChange={set("email")} className={input} /></label>
      <label className="block text-sm font-medium">Password<input required type="password" minLength={6} value={form.password} onChange={set("password")} className={input} /></label>
      {error && <p role="alert" className="text-sm text-weak">{error}</p>}
      <button disabled={busy} className="w-full rounded-md bg-brand py-2.5 font-medium text-white disabled:opacity-50">
        {busy ? "Please wait…" : isRegister ? "Create account" : "Log in"}
      </button>
      <p className="text-sm text-new">
        {isRegister ? "Already have an account? " : "New here? "}
        <Link className="text-brand underline" to={isRegister ? "/login" : "/register"}>{isRegister ? "Log in" : "Create an account"}</Link>
      </p>
    </form>
  );
}
