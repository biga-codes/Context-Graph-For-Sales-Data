import axios from "axios";

const api = axios.create({ baseURL: "/api" });

export const fetchGraph = () => api.get("/graph/").then((r) => r.data);

export const fetchNeighbors = (nodeId) =>
  api.get(`/graph/neighbors/${encodeURIComponent(nodeId)}`).then((r) => r.data);

export const sendChat = (message) =>
  api.post("/chat/", { message }).then((r) => r.data);
