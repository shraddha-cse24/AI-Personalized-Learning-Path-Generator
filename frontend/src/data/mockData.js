export const mockLearningPath = [
  { rank: 1, concept_code: 2, name: "One-to-one correspondence counting", action: "revise", status: "weak", mastery: 0.4, attempts: 5, accuracy: 0.2, reason: "Your accuracy in this topic is 20% over 5 attempts." },
  { rank: 2, concept_code: 7, name: "Comparing numbers", action: "practice", status: "learning", mastery: 0.58, attempts: 8, accuracy: 0.5, reason: "You're improving here. A few more exercises will lock it in." },
  { rank: 3, concept_code: 11, name: "Addition within 20", action: "advance", status: "proficient", mastery: 0.82, attempts: 12, accuracy: 0.83, reason: "You're ready for harder problems in this topic." },
  { rank: 4, concept_code: 15, name: "Place value", action: "start", status: "new", mastery: 0, attempts: 0, accuracy: 0, reason: "New topic that builds on the ones above." },
];

export const mockQuestions = [
  { id: "q1", ucid: "ex_101", text: "How many apples are in a group of 3 apples plus 2 apples?", options: ["4", "5", "6", "7"], answer: "5" },
  { id: "q2", ucid: "ex_102", text: "Which number is greater?", options: ["12", "9", "7", "3"], answer: "12" },
  { id: "q3", ucid: "ex_103", text: "What is 8 + 7?", options: ["13", "14", "15", "16"], answer: "15" },
];
