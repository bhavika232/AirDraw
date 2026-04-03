import { useEffect, useState } from "react";
import { resetGame } from "../api";

// Simplified from original Results.jsx:
//   REMOVED — roomId parameter (no rooms)
//   KEPT    — podium, rest of players, chat replay, play again button
export default function Results({ state, username, onPlayAgain }) {
  const [board, setBoard] = useState([]);

  // Sort players highest score first
  useEffect(() => {
    if (state?.players) {
      setBoard(Object.entries(state.players).sort((a, b) => b[1].score - a[1].score));
    }
  }, [state]);

  async function handlePlayAgain() {
    await resetGame(); // tell Flask to wipe all state
    onPlayAgain();     // go back to the Join screen
  }

  const [first, second, third, ...rest] = board;

  return (
    <div className="results-root">
      <header className="game-header">
        <span className="game-logo">Pictionary Play</span>
        <span className="game-room">Game Over</span>
      </header>

      <div className="results-body">

        {/* Podium — top 3 players */}
        <section className="podium">
          <h1 className="results-title">🏁 Final Scores</h1>

          <div className="podium-row">
            {second && (
              <div className="podium-card place-2">
                <div className="podium-rank">2</div>
                <div className="podium-avatar">{second[0][0].toUpperCase()}</div>
                <div className="podium-name">
                  {second[0]}
                  {second[0] === username && <span className="you-tag">you</span>}
                </div>
                <div className="podium-score">{second[1].score} pts</div>
              </div>
            )}

            {first && (
              <div className="podium-card place-1">
                <div className="podium-trophy">🏆</div>
                <div className="podium-avatar podium-avatar-lg">{first[0][0].toUpperCase()}</div>
                <div className="podium-name podium-name-lg">
                  {first[0]}
                  {first[0] === username && <span className="you-tag">you</span>}
                </div>
                <div className="podium-score podium-score-lg">{first[1].score} pts</div>
              </div>
            )}

            {third && (
              <div className="podium-card place-3">
                <div className="podium-rank">3</div>
                <div className="podium-avatar">{third[0][0].toUpperCase()}</div>
                <div className="podium-name">
                  {third[0]}
                  {third[0] === username && <span className="you-tag">you</span>}
                </div>
                <div className="podium-score">{third[1].score} pts</div>
              </div>
            )}
          </div>

          {/* Anyone beyond the top 3 */}
          {rest.length > 0 && (
            <div className="results-rest">
              {rest.map(([name, info], i) => (
                <div key={name} className="rest-row">
                  <span className="rest-rank">{i + 4}</span>
                  <div className="rest-avatar">{name[0].toUpperCase()}</div>
                  <span className="rest-name">
                    {name}
                    {name === username && <span className="you-tag">you</span>}
                  </span>
                  <span className="rest-score">{info.score} pts</span>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Chat replay from the last round */}
        {state?.chat?.length > 0 && (
          <aside className="results-chat sidebar-card">
            <h3 className="sidebar-heading">Round Chat</h3>
            <div className="chat-log results-chat-log">
              {state.chat.map((msg, i) => {
                const isSystem = msg.startsWith("---") || msg.includes("🌟");
                return (
                  <div key={i} className={`chat-msg ${isSystem ? "chat-system" : ""}`}>
                    {msg}
                  </div>
                );
              })}
            </div>
          </aside>
        )}
      </div>

      <div className="results-actions">
        <button className="start-btn" onClick={handlePlayAgain}>
          🔄 Play Again
        </button>
      </div>
    </div>
  );
}