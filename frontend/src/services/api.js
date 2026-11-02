const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };
export const getToken = () => localStorage.getItem("token");

function messageFrom(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg.replace(/^Value error, /, "");
  return "Please check what you entered and try again.";
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(BASE + path, {
      ...options,
      headers: { "Content-Type": "application/json", ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}) },
    });
  } catch {
    throw new Error(`Can't reach the server at ${BASE}. Is the backend running?`);
  }
  if (res.status === 401 && getToken()) onUnauthorized();
  if (!res.ok) throw new Error(messageFrom((await res.json().catch(() => ({}))).detail));
  return res.json();
}
const send = (method, path, body) => request(path, { method, body: JSON.stringify(body) });

// Auth -> { id, name, email, access_token }
export const register = (name, email, password) => send("POST", "/auth/register", { name, email, password });
export const login = (email, password) => send("POST", "/auth/login", { email, password });
export const getMe = () => request("/auth/me");

// Student data
export const getProfile = () => request("/students/me/profile");
export const updateProfile = (selected_subject, learning_level) => send("PUT", "/students/me/profile", { selected_subject, learning_level });
export const getLearningPath = () => request("/students/me/path?n_steps=6&exercises_per_step=3");
export const getNextExercises = (k = 3, conceptCode) => request(`/students/me/next-exercises?k=${k}${conceptCode ? `&concept_code=${conceptCode}` : ""}`);
export const getMastery = () => request("/students/me/mastery");
export const submitAttempt = (ucid, is_correct) => send("POST", "/attempts", { ucid, is_correct });
