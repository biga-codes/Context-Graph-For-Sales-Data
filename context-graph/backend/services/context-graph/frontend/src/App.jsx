import React from "react";
import Navbar from "./components/Navbar";
import GraphCanvas from "./components/GraphCanvas";
import ChatPanel from "./components/ChatPanel";

export default function App() {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <Navbar />
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <GraphCanvas />
        <ChatPanel />
      </div>
    </div>
  );
}
