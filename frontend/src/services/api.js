import { mockLearningPath } from "../data/mockData";

const USE_MOCK = true; // set to false when the backend is ready
const API_BASE_URL = "http://localhost:8000"; // confirm with your backend teammate

async function request(path, options) {
  const res = await fetch(`${API_BASE_URL}${path}`, options);
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

export async function submitAttempt(studentId, ucid, isCorrect) {
  if (USE_MOCK) return { ok: true };
  return request("/attempts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ student_id: studentId, ucid, is_correct: isCorrect }),
  });
}

export async function getLearningPath(studentId) {
  if (USE_MOCK) return { steps: mockLearningPath };
  return request(`/students/${studentId}/path`);
}

export async function getMastery(studentId) {
  if (USE_MOCK) return { topics: mockLearningPath };
  return request(`/students/${studentId}/mastery`);
}

// ---- Auth. Confirm endpoint names and response shape with the backend teammate ----
export async function register(name, email, password) {
  if (USE_MOCK) {
    const users = JSON.parse(localStorage.getItem("mockUsers") || "[]");
    if (users.some((u) => u.email === email)) throw new Error("An account with this email already exists. Log in instead.");
    const u = { id: "stu" + (users.length + 1), name, email, password };
    localStorage.setItem("mockUsers", JSON.stringify([...users, u]));
    return { id: u.id, name, email };
  }
  return request("/auth/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, email, password }) });
}

export async function login(email, password) {
  if (USE_MOCK) {
    const users = JSON.parse(localStorage.getItem("mockUsers") || "[]");
    const u = users.find((x) => x.email === email && x.password === password);
    if (!u) throw new Error("Email or password is incorrect.");
    return { id: u.id, name: u.name, email };
  }
  return request("/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
}
