import React from "react";
import { Handle, Position } from "reactflow";

const styles = {
  node: (color, selected, highlighted) => ({
    background: selected || highlighted ? color + "22" : "#151820",
    border: `1.5px solid ${selected || highlighted ? color : "#2a2f3e"}`,
    borderRadius: 8,
    padding: "8px 14px",
    minWidth: 160,
    cursor: "pointer",
    boxShadow: selected ? `0 0 0 2px ${color}55` : "none",
    transition: "all 0.15s ease",
  }),
  badge: (color) => ({
    display: "inline-block",
    fontSize: 9,
    fontFamily: "IBM Plex Mono, monospace",
    fontWeight: 600,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    color,
    background: color + "18",
    border: `1px solid ${color}44`,
    borderRadius: 4,
    padding: "1px 6px",
    marginBottom: 4,
  }),
  label: {
    fontSize: 13,
    fontWeight: 500,
    color: "#e2e8f0",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
    maxWidth: 150,
  },
};

export default function EntityNode({ data, selected }) {
  const { label, entityType, color, highlighted } = data;

  return (
    <div style={styles.node(color, selected, highlighted)}>
      <Handle type="target" position={Position.Left} style={{ background: color, border: "none" }} />
      <div style={styles.badge(color)}>{entityType}</div>
      <div style={styles.label}>{label}</div>
      <Handle type="source" position={Position.Right} style={{ background: color, border: "none" }} />
    </div>
  );
}
