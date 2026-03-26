import axios from "axios";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api";
const api = axios.create({ baseURL: apiBaseUrl });

export const fetchGraph = () => api.get("/graph/").then((r) => r.data);

export const fetchNeighbors = (nodeId) =>
  api.get(`/graph/neighbors/${encodeURIComponent(nodeId)}`).then((r) => r.data);

export const sendChat = (message) =>
  api.post("/chat/", { message }).then((r) => r.data);
