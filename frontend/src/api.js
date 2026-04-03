// All requests go to the local Flask server
const BASE = "http://localhost:5000";

// Join the single shared game room with a username
export async function joinGame(username) {
  const res = await fetch(`${BASE}/join`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username }),
  });
  return res.json(); 
}

// Start the game 
export async function startGame() {
  const res = await fetch(`${BASE}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  return res.json();
}

// Poll this every ~600ms to keep all screens in sync
export async function getState(username) {
  const res = await fetch(`${BASE}/state?username=${encodeURIComponent(username)}`);
  return res.json();
}

// Submit a guess
export async function sendGuess(username, guess) {
  const res = await fetch(`${BASE}/guess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, guess }),
  });
  return res.json(); // { correct: true/false }
}

// Reset everything for a new game
export async function resetGame() {
  const res = await fetch(`${BASE}/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  return res.json();
}

// The live camera stream URL — used directly in the VideoFeed component
export function videoFeedUrl() {
  return `${BASE}/video_feed`;
}