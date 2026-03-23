import React, { useEffect, useCallback, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
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
  } = useStore();

  const storeNodes = useStore((s) => s.nodes);
  const storeEdges = useStore((s) => s.edges);
  const loading = useStore((s) => s.loading);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

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
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.1}
        maxZoom={2}
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#1e2230" />
        <Controls style={{ background: "#151820", border: "1px solid #2a2f3e" }} />
        <MiniMap
          nodeColor={(n) => n.data?.color || "#3b82f6"}
          style={{ background: "#151820", border: "1px solid #2a2f3e" }}
          maskColor="#0d0f1488"
        />
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
