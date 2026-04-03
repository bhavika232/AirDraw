import { useState } from "react";
import Join from "./components/Join";
import Game from "./components/Game";
import Results from "./components/Results";

// The app has exactly three screens
export default function App() {
  const [screen, setScreen] = useState("join");
  const [username, setUsername] = useState("");
  const [finalState, setFinalState] = useState(null);

  function handleJoined(name) {
    setUsername(name);
    setScreen("game");
  }

  function handleGameOver(state) {
    setFinalState(state);
    setScreen("results");
  }

  function handlePlayAgain() {
    setFinalState(null);
    setScreen("join"); //players re-enter their names
  }

  return (
    <div className="app-root">
      {screen === "join"    && <Join onJoined={handleJoined} />}
      {screen === "game"    && <Game username={username} onGameOver={handleGameOver} />}
      {screen === "results" && <Results state={finalState} username={username} onPlayAgain={handlePlayAgain} />}
    </div>
  );
}