import { useState } from "react";
import { joinGame } from "../api";

// Simplified from Lobby.jsx:
//   REMOVED — Create Room / Join Room tabs (no room IDs needed anymore)
//   KEPT    — Username input and the join button
export default function Join({ onJoined }) {
  const [username, setUsername] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleJoin() {
    if (!username.trim()) return setError("Please enter a username");
    setLoading(true);
    setError(null);
    try {
      const data = await joinGame(username.trim());
      if (data.error) throw new Error(data.error);
      onJoined(username.trim());
    } catch (e) {
      setError(e.message || "Could not join. Try a different username.");
    } finally {
      setLoading(false);
    }
  }

  // Allow pressing Enter to join
  function handleKey(e) {
    if (e.key === "Enter") handleJoin();
  }

  return (
    <div className="lobby-wrap">
      <div className="lobby-card">
        <div className="lobby-logo">Pictionary Play</div>
        <p className="lobby-sub">Draw with your hands. No mouse needed.</p>

        <input
          className="lobby-input"
          placeholder="Your username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          onKeyDown={handleKey}
          autoFocus
        />

        {error && <p className="lobby-error">{error}</p>}

        <button className="lobby-btn" onClick={handleJoin} disabled={loading}>
          {loading ? "Joining…" : "Join Game"}
        </button>
      </div>
    </div>
  );
}