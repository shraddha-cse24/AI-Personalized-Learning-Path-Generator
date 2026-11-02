// `id` must match a subject the backend accepts (SUPPORTED_SUBJECTS in backend/app/schemas/profile.py).
// Only subjects with a trained model + exercise data are `available`. See the project notes on adding CSE tracks.
export const SUBJECTS = [
  { id: "junyi-math", label: "Mathematics (Junyi Academy data)", available: true },
  { id: "cse-dsa", label: "Data Structures & Algorithms", available: false },
  { id: "cse-ml", label: "Machine Learning fundamentals", available: false },
];
export const AVAILABLE_SUBJECTS = SUBJECTS.filter((s) => s.available);
