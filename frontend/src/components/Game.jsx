import { useState, useEffect, useRef } from "react";
import { getState, sendGuess, startGame, videoFeedUrl } from "../api";

const POLL_MS = 600; // how often (ms) we ask Flask for the latest game state

// Simplified from the original Game.jsx:
//   REMOVED — roomId (no rooms anymore)
//   KEPT    — polling, video feed, guess input, player list, chat, countdown
export default function Game({ username, onGameOver }) {
  const [state, setState] = useState(null);  // latest snapshot from /state
  const [guess, setGuess] = useState("");
  const [flash, setFlash] = useState(null);  // brief "✓ Correct!" message
  const chatEndRef = useRef(null);

  // Poll /state every 600ms — this is how all players stay in sync
  useEffect(() => {
    let alive = true;

    async function poll() {
      try {
        const data = await getState(username);
        if (!alive) return;
        setState(data);
        if (data.game_over) onGameOver(data); // hand off to Results screen
      } catch (_) {}
    }

    const id = setInterval(poll, POLL_MS);
    poll(); // run once immediately so the screen isn't blank on load
    return () => { alive = false; clearInterval(id); };
  }, [username, onGameOver]);

  // Auto-scroll the chat log to the newest message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state?.chat]);

  // Clear the flash message when the round changes
  const prevRoundRef = useRef(null);
  useEffect(() => {
    if (prevRoundRef.current !== null && state?.round !== prevRoundRef.current) {
      setFlash(null);
    }
    prevRoundRef.current = state?.round;
  }, [state?.round]);

  async function handleStart() {
    const result = await startGame();
    if (result.error) alert(result.error);
  }

  async function handleGuess(e) {
    e.preventDefault();
    if (!guess.trim()) return;
    const result = await sendGuess(username, guess.trim());
    setGuess("");
    if (result.correct) {
      setFlash("✓ Correct!");
      setTimeout(() => setFlash(null), 2500);
    }
  }

  // Derived values — computed from state so the JSX stays readable
  const isDrawer   = state?.drawer === username;
  const hasGuessed = state?.guessed_correctly?.includes(username);
  const gameActive = state?.game_started;
  const countdown  = state?.countdown ?? 0;
  const playerList = state ? Object.entries(state.players) : [];

  return (
    <div className="game-root">

      {/* Header */}
      <header className="game-header">
        <span className="game-logo">Pictionary Play</span>
        <div className="game-meta">
          {gameActive && (
            <span className="game-round">
              Round {Math.min(state.round, state.max_rounds)} / {state.max_rounds}
            </span>
          )}
        </div>
        {gameActive && countdown === 0 && (
          <div className="game-timer-pill">
            <span className="timer-label">Time</span>
            <span className={`timer-val ${state?.time_left <= 10 ? "timer-urgent" : ""}`}>
              {state?.time_left ?? "–"}
            </span>
          </div>
        )}
      </header>

      {/* Full-screen 3-2-1 countdown overlay */}
      {countdown > 0 && (
        <div className="countdown-overlay">
          <div className="countdown-number">{countdown}</div>
          <div className="countdown-label">Get ready!</div>
        </div>
      )}

      <div className="game-body">

        {/* Left column: video feed + word hint + gesture tips */}
        <section className="game-canvas-col">

          {/* Shows the secret word to the drawer; blanks to guessers */}
          <div className="word-hint-bar">
            {countdown > 0 ? (
              <span className="hint-label hint-waiting">Round starting…</span>
            ) : gameActive ? (
              isDrawer ? (
                <>
                  <span className="hint-label">Your word:</span>
                  <span className="hint-word">{state.word}</span>
                </>
              ) : hasGuessed ? (
                <span className="hint-word" style={{ color: "var(--tertiary)" }}>
                  🎉 Guessed it! Waiting for others…
                </span>
              ) : (
                <>
                  <span className="hint-label">Guess:</span>
                  <span className="hint-word hint-masked">{state.word}</span>
                </>
              )
            ) : (
              <span className="hint-label hint-waiting">Waiting to start…</span>
            )}
          </div>

          {/* Live camera stream from Flask /video_feed */}
          <div className="canvas-frame">
            <VideoFeed />
            {flash && <div className="flash-overlay">{flash}</div>}
            {isDrawer && gameActive && countdown === 0 && (
              <div className="drawer-badge">✏️ You are drawing!</div>
            )}
          </div>

          {/* Remind the drawer which gestures do what */}
          <div className="gesture-hints">
            <span>☝️ Draw</span>
            <span>✌️ Pause</span>
            <span>🤟 Erase</span>
            <span>🎨 Hover color box to switch</span>
            <span>🗑️ Hover CLR to clear</span>
          </div>
        </section>

        {/* Right column: players, chat, controls */}
        <aside className="game-sidebar">

          {/* Sorted scoreboard */}
          <div className="sidebar-card players-card">
            <h3 className="sidebar-heading">Players</h3>
            <ul className="player-list">
              {playerList
                .sort((a, b) => b[1].score - a[1].score)
                .map(([name, info]) => {
                  const isCurrentDrawer = name === state?.drawer;
                  const didGuess = state?.guessed_correctly?.includes(name);
                  return (
                    <li
                      key={name}
                      className={`player-row ${isCurrentDrawer ? "is-drawer" : ""} ${didGuess ? "did-guess" : ""}`}
                    >
                      <div className="player-avatar">{name[0].toUpperCase()}</div>
                      <span className="player-name">
                        {name}
                        {isCurrentDrawer && <span className="drawer-tag">✏️</span>}
                        {didGuess && !isCurrentDrawer && <span className="guessed-tag">✓</span>}
                        {name === username && <span className="you-tag">you</span>}
                      </span>
                      <span className="player-score">{info.score} pts</span>
                    </li>
                  );
                })}
            </ul>
          </div>

          {/* Chat log + guess input */}
          <div className="sidebar-card chat-card">
            <h3 className="sidebar-heading">Chat</h3>
            <div className="chat-log">
              {(state?.chat ?? []).map((msg, i) => {
                const isSystem = msg.startsWith("---") || msg.includes("🌟");
                return (
                  <div key={i} className={`chat-msg ${isSystem ? "chat-system" : ""}`}>
                    {msg}
                  </div>
                );
              })}
              <div ref={chatEndRef} />
            </div>

            {/* Only show input to active guessers */}
            {gameActive && !isDrawer && !hasGuessed && countdown === 0 ? (
              <form className="chat-form" onSubmit={handleGuess}>
                <input
                  className="chat-input"
                  value={guess}
                  onChange={(e) => setGuess(e.target.value)}
                  placeholder="Type your guess…"
                  autoComplete="off"
                  autoFocus
                />
                <button className="chat-send" type="submit">→</button>
              </form>
            ) : (
              <div className="chat-disabled">
                {isDrawer       ? "You're drawing — no guessing!"
                : hasGuessed    ? "You guessed it! 🎉"
                : countdown > 0 ? "Round starting…"
                :                 "Press Start to begin"}
              </div>
            )}
          </div>

          {/* Start button — visible before the game begins */}
          {!gameActive && !state?.game_over && (
            <button className="start-btn" onClick={handleStart}>
              Start Game
            </button>
          )}

          {gameActive && countdown === 0 && (
            <div className="waiting-pill">
              Round {Math.min(state?.round, state?.max_rounds)} of {state?.max_rounds} in progress…
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

// Receives base64 JPEG frames from Flask via Server-Sent Events and paints
// them onto a <canvas> element — this is how the live drawing stream works.
function VideoFeed() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const es = new EventSource(videoFeedUrl());

    es.onmessage = (e) => {
      const img = new Image();
      img.onload = () => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        canvas.width  = img.width;
        canvas.height = img.height;
        canvas.getContext("2d").drawImage(img, 0, 0);
      };
      img.src = "data:image/jpeg;base64," + e.data;
    };

    es.onerror = () => es.close();
    return () => es.close();
  }, []);

  return <canvas ref={canvasRef} className="video-canvas" />;
}