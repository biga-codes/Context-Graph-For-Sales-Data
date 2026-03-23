import { create } from "zustand";

export const useStore = create((set, get) => ({
  // ── Graph ───────────────────────────────────────────────────────────────
  nodes: [],
  edges: [],
  loading: false,
  selectedNode: null,

  setGraph: ({ nodes, edges }) => set({ nodes, edges }),
  setLoading: (v) => set({ loading: v }),
  setSelectedNode: (node) => set({ selectedNode: node }),

  mergeNeighbors: ({ nodes, edges }) => {
    const existing = get();
    const nodeMap = new Map(existing.nodes.map((n) => [n.id, n]));
    nodes.forEach((n) => nodeMap.set(n.id, n));
    const edgeMap = new Map(existing.edges.map((e) => [e.id, e]));
    edges.forEach((e) => edgeMap.set(e.id, e));
    set({ nodes: [...nodeMap.values()], edges: [...edgeMap.values()] });
  },

  // ── Chat ────────────────────────────────────────────────────────────────
  messages: [],
  chatLoading: false,

  addMessage: (msg) =>
    set((s) => ({ messages: [...s.messages, msg] })),

  setChatLoading: (v) => set({ chatLoading: v }),

  // ── Highlighted nodes from last query ──────────────────────────────────
  highlightedNodeIds: new Set(),
  setHighlightedNodeIds: (ids) => set({ highlightedNodeIds: new Set(ids) }),
}));
