import React, { useEffect, useCallback, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  Panel,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
} from "reactflow";
import { useStore } from "../store/useStore";
import { fetchGraph } from "../services/api";
import { applyDagreLayout } from "../services/layout";
import EntityNode from "./EntityNode";
import NodeDetailPanel from "./NodeDetailPanel";

const nodeTypes = { entityNode: EntityNode };

export default function GraphCanvas() {
  const {
    setGraph,
    setLoading,
    setSelectedNode,
    highlightedNodeIds,
    setHighlightedNodeIds,
  } = useStore();

  const storeNodes = useStore((s) => s.nodes);
  const storeEdges = useStore((s) => s.edges);
  const loading = useStore((s) => s.loading);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [rfInstance, setRfInstance] = useState(null);
  const [initialViewApplied, setInitialViewApplied] = useState(false);

  const topHubs = useMemo(() => {
    const degree = new Map();
    storeEdges.forEach((e) => {
      degree.set(e.source, (degree.get(e.source) || 0) + 1);
      degree.set(e.target, (degree.get(e.target) || 0) + 1);
    });

    const nodeById = new Map(storeNodes.map((n) => [n.id, n]));
    return [...degree.entries()]
      .map(([id, count]) => ({ id, count, node: nodeById.get(id) }))
      .filter((x) => x.node)
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
  }, [storeNodes, storeEdges]);

  // Sync store → local RF state with highlight injection
  useEffect(() => {
    const enriched = storeNodes.map((n) => ({
      ...n,
      data: {
        ...n.data,
        highlighted: highlightedNodeIds.has(n.id),
      },
    }));
    setNodes(enriched);
  }, [storeNodes, highlightedNodeIds]);

  useEffect(() => {
    setEdges(storeEdges);
  }, [storeEdges]);

  // Initial viewport: focus the top part of the graph for a cleaner first impression.
  useEffect(() => {
    if (!rfInstance || initialViewApplied || nodes.length === 0) return;

    const topCount = Math.max(12, Math.floor(nodes.length * 0.25));
    const topNodes = [...nodes]
      .sort((a, b) => (a.position?.y ?? 0) - (b.position?.y ?? 0))
      .slice(0, topCount)
      .map((n) => ({ id: n.id }));

    requestAnimationFrame(() => {
      rfInstance.fitView({
        nodes: topNodes,
        padding: 0.12,
        minZoom: 0.8,
        maxZoom: 1.9,
        duration: 420,
      });
    });

    setInitialViewApplied(true);
  }, [rfInstance, nodes, initialViewApplied]);

  // Load full graph on mount
  useEffect(() => {
    setLoading(true);
    fetchGraph()
      .then((data) => {
        const laid = applyDagreLayout(data.nodes, data.edges);
        setGraph({ nodes: laid, edges: data.edges });
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const onNodeClick = useCallback(
    (_, node) => setSelectedNode(node),
    [setSelectedNode]
  );

  const onHubClick = useCallback(
    (hubNode) => {
      setSelectedNode(hubNode);

      // Keep hub interaction snappy: center + zoom in, no graph mutation.
      if (rfInstance && hubNode?.position) {
        rfInstance.setCenter(hubNode.position.x, hubNode.position.y, {
          zoom: 1.2,
          duration: 260,
        });
      }

      // Highlight first + second-degree neighbors around the selected hub.
      const adjacency = new Map();
      storeEdges.forEach((e) => {
        if (!adjacency.has(e.source)) adjacency.set(e.source, new Set());
        if (!adjacency.has(e.target)) adjacency.set(e.target, new Set());
        adjacency.get(e.source).add(e.target);
        adjacency.get(e.target).add(e.source);
      });

      const center = hubNode.id;
      const first = adjacency.get(center) || new Set();
      const second = new Set();
      first.forEach((n1) => {
        (adjacency.get(n1) || new Set()).forEach((n2) => second.add(n2));
      });

      setHighlightedNodeIds([center, ...first, ...second]);
    },
    [rfInstance, setSelectedNode, setHighlightedNodeIds, storeEdges]
  );

  if (loading) {
    return (
      <div style={loadingStyle}>
        <span style={{ fontFamily: "IBM Plex Mono, monospace", color: "#3b82f6", fontSize: 13 }}>
          Building graph…
        </span>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, position: "relative" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onInit={setRfInstance}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={{
          type: "smoothstep",
          pathOptions: { offset: 36, borderRadius: 16 },
          style: { strokeWidth: 1.2 },
        }}
        minZoom={0.1}
        maxZoom={2}
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#1e2230" />
        <Controls
          position="bottom-right"
          showZoom
          showFitView
          showInteractive
          style={{ background: "#151820", border: "1px solid #2a2f3e", zIndex: 12 }}
        />
        <Panel position="bottom-left">
          <div style={hubStyles.card}>
            <div style={hubStyles.header}>Top 5 Hubs</div>
            <div style={hubStyles.sub}>Click to center + highlight context</div>
            <div style={hubStyles.list}>
              {topHubs.length === 0 && <div style={hubStyles.empty}>No hubs available</div>}
              {topHubs.map((h) => (
                <button
                  key={h.id}
                  style={hubStyles.item}
                  onClick={() => onHubClick(h.node)}
                  title={h.id}
                >
                  <span style={hubStyles.label}>{h.node.data?.label || h.id}</span>
                  <span style={hubStyles.degree}>{h.count}</span>
                </button>
              ))}
            </div>
          </div>
        </Panel>
      </ReactFlow>
      <NodeDetailPanel />
    </div>
  );
}

const loadingStyle = {
  flex: 1,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "#0d0f14",
};

const hubStyles = {
  card: {
    width: 260,
    background: "#121826",
    border: "1px solid #2a2f3e",
    borderRadius: 10,
    padding: 10,
    boxShadow: "0 6px 20px #00000055",
    fontFamily: "IBM Plex Sans, sans-serif",
  },
  header: {
    color: "#e2e8f0",
    fontSize: 13,
    fontWeight: 700,
    marginBottom: 2,
  },
  sub: {
    color: "#64748b",
    fontSize: 11,
    marginBottom: 8,
  },
  list: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  empty: {
    color: "#64748b",
    fontSize: 12,
    padding: "4px 0",
  },
  item: {
    width: "100%",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    background: "#1e2230",
    border: "1px solid #2a2f3e",
    borderRadius: 6,
    color: "#cbd5e1",
    fontSize: 12,
    padding: "7px 8px",
    cursor: "pointer",
    textAlign: "left",
  },
  label: {
    maxWidth: 190,
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  degree: {
    fontFamily: "IBM Plex Mono, monospace",
    color: "#60a5fa",
    fontWeight: 700,
  },
};
