import React from "react";
import { useStore } from "../store/useStore";
import { fetchNeighbors } from "../services/api";
import { applyDagreLayout } from "../services/layout";

const s = {
  panel: {
    position: "absolute",
    top: 16,
    right: 16,
    width: 280,
    background: "#151820",
    border: "1px solid #2a2f3e",
    borderRadius: 10,
    padding: 16,
    zIndex: 10,
    fontFamily: "IBM Plex Sans, sans-serif",
    boxShadow: "0 8px 32px #00000088",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  title: { fontSize: 13, fontWeight: 600, color: "#e2e8f0" },
  close: {
    background: "none",
    border: "none",
    color: "#64748b",
    cursor: "pointer",
    fontSize: 16,
    lineHeight: 1,
  },
  badge: (color) => ({
    display: "inline-block",
    fontSize: 10,
    fontFamily: "IBM Plex Mono, monospace",
    fontWeight: 600,
    textTransform: "uppercase",
    color,
    background: color + "18",
    border: `1px solid ${color}44`,
    borderRadius: 4,
    padding: "2px 7px",
    marginBottom: 10,
  }),
  row: {
    display: "flex",
    justifyContent: "space-between",
    padding: "4px 0",
    borderBottom: "1px solid #1e2230",
    fontSize: 12,
  },
  key: { color: "#64748b", fontFamily: "IBM Plex Mono, monospace" },
  val: { color: "#e2e8f0", maxWidth: 160, textAlign: "right", wordBreak: "break-all" },
  expandBtn: {
    marginTop: 12,
    width: "100%",
    padding: "7px 0",
    background: "#1e2230",
    border: "1px solid #3b82f6",
    borderRadius: 6,
    color: "#3b82f6",
    fontSize: 12,
    fontWeight: 600,
    cursor: "pointer",
    fontFamily: "IBM Plex Sans, sans-serif",
  },
};

export default function NodeDetailPanel() {
  const { selectedNode, setSelectedNode, mergeNeighbors, nodes, edges, setGraph } = useStore();

  if (!selectedNode) return null;

  const { label, entityType, color, properties } = selectedNode.data;

  const handleExpand = async () => {
    try {
      const data = await fetchNeighbors(selectedNode.id);
      mergeNeighbors(data);
      // Re-layout after merge
      const { nodes: allNodes, edges: allEdges } = useStore.getState();
      const laid = applyDagreLayout(allNodes, allEdges);
      setGraph({ nodes: laid, edges: allEdges });
    } catch (e) {
      console.error("Expand failed", e);
    }
  };

  return (
    <div style={s.panel}>
      <div style={s.header}>
        <span style={s.title}>{label}</span>
        <button style={s.close} onClick={() => setSelectedNode(null)}>×</button>
      </div>

      <span style={s.badge(color)}>{entityType}</span>

      <div>
        {Object.entries(properties || {})
          .filter(([k]) => k !== "label" && k !== "entityType" && k !== "color")
          .map(([k, v]) => (
            <div style={s.row} key={k}>
              <span style={s.key}>{k}</span>
              <span style={s.val}>{v == null ? "—" : String(v)}</span>
            </div>
          ))}
      </div>

      <button style={s.expandBtn} onClick={handleExpand}>
        ⊕ Expand Neighbors
      </button>
    </div>
  );
}
