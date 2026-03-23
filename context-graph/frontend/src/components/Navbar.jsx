import React from "react";
import { useStore } from "../store/useStore";

export default function Navbar() {
  const nodeCount = useStore((s) => s.nodes.length);
  const edgeCount = useStore((s) => s.edges.length);

  return (
    <header style={s.nav}>
      <div style={s.brand}>
        <span style={s.dot} />
        <span style={s.title}>Context Graph</span>
        <span style={s.tag}>Explorer</span>
      </div>
      <div style={s.stats}>
        <Stat label="nodes" value={nodeCount} />
        <Stat label="edges" value={edgeCount} />
      </div>
    </header>
  );
}

function Stat({ label, value }) {
  return (
    <span style={s.stat}>
      <span style={s.statVal}>{value}</span>
      <span style={s.statLabel}>{label}</span>
    </span>
  );
}

const s = {
  nav: {
    height: 48,
    background: "#151820",
    borderBottom: "1px solid #2a2f3e",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 20px",
    flexShrink: 0,
  },
  brand: { display: "flex", alignItems: "center", gap: 10 },
  dot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: "#3b82f6",
    boxShadow: "0 0 8px #3b82f6",
  },
  title: {
    fontFamily: "IBM Plex Mono, monospace",
    fontSize: 14,
    fontWeight: 600,
    color: "#e2e8f0",
  },
  tag: {
    fontFamily: "IBM Plex Mono, monospace",
    fontSize: 10,
    color: "#64748b",
    background: "#1e2230",
    border: "1px solid #2a2f3e",
    borderRadius: 4,
    padding: "2px 7px",
    letterSpacing: "0.05em",
  },
  stats: { display: "flex", gap: 16 },
  stat: {
    display: "flex",
    gap: 5,
    alignItems: "baseline",
  },
  statVal: {
    fontFamily: "IBM Plex Mono, monospace",
    fontSize: 13,
    fontWeight: 600,
    color: "#3b82f6",
  },
  statLabel: {
    fontSize: 11,
    color: "#64748b",
    fontFamily: "IBM Plex Mono, monospace",
  },
};
