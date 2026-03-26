import React, { useState, useRef, useEffect } from "react";
import { useStore } from "../store/useStore";
import { sendChat } from "../services/api";

const SUGGESTIONS = [
  "Which product has the highest number of deliveries?",
  "Which products have the highest billed net amount, and how many billing documents does each have?",
  "For sales order 740506, what are the payment details and delivery status?",
  "Show orders that were delivered and billed",
];

export default function ChatPanel() {
  const [input, setInput] = useState("");
  const { messages, addMessage, chatLoading, setChatLoading, setHighlightedNodeIds } = useStore();
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chatLoading]);

  const submit = async (text) => {
    const q = (text || input).trim();
    if (!q) return;
    setInput("");
    addMessage({ role: "user", content: q });
    setChatLoading(true);

    try {
      const res = await sendChat(q);
      addMessage({
        role: "assistant",
        content: res.answer,
        sql: res.sql,
        rows: res.rows,
        relevant: res.relevant,
      });

      // Highlight nodes that appear in the result rows
      if (res.rows?.length) {
        const ids = extractNodeIds(res.rows);
        setHighlightedNodeIds(ids);
      } else {
        setHighlightedNodeIds([]);
      }
    } catch (e) {
      addMessage({ role: "assistant", content: "Error contacting the server.", relevant: false });
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div style={s.panel}>
      <div style={s.header}>
        <span style={s.title}>Query Interface</span>
        <span style={s.subtitle}>Ask questions about the dataset</span>
      </div>

      <div style={s.messages}>
        {messages.length === 0 && (
          <div style={s.empty}>
            <p style={s.emptyTitle}>Suggestions</p>
            {SUGGESTIONS.map((q) => (
              <button key={q} style={s.suggestion} onClick={() => submit(q)}>
                {q}
              </button>
            ))}
          </div>
        )}

        {messages.map((m, i) => (
          <MessageBubble key={i} msg={m} />
        ))}

        {chatLoading && (
          <div style={{ ...s.bubble, ...s.assistant }}>
            <span style={s.thinking}>Thinking…</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div style={s.inputRow}>
        <input
          style={s.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && submit()}
          placeholder="Ask about orders, deliveries, invoices…"
          disabled={chatLoading}
        />
        <button style={s.sendBtn} onClick={() => submit()} disabled={chatLoading || !input.trim()}>
          ↑
        </button>
      </div>
    </div>
  );
}

function MessageBubble({ msg }) {
  const [showSql, setShowSql] = useState(false);

  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ ...s.bubble, ...(msg.role === "user" ? s.user : s.assistant) }}>
        {msg.content}
      </div>

      {msg.role === "assistant" && msg.sql && (
        <div style={s.sqlContainer}>
          <button style={s.sqlToggle} onClick={() => setShowSql((v) => !v)}>
            {showSql ? "▾ Hide SQL" : "▸ Show SQL"}
          </button>
          {showSql && <pre style={s.sqlBlock}>{msg.sql}</pre>}
          {msg.rows?.length > 0 && (
            <span style={s.rowCount}>{msg.rows.length} row{msg.rows.length !== 1 ? "s" : ""}</span>
          )}
        </div>
      )}
    </div>
  );
}

// Extract node ids from query result rows by looking for known FK columns
function extractNodeIds(rows) {
  const idFields = {
    customer_id: "c_",
    order_id: "o_",
    order_item_id: "oi_",
    product_id: "p_",
    delivery_id: "d_",
    invoice_id: "inv_",
    payment_id: "pay_",
    address_id: "a_",
  };
  const ids = new Set();
  rows.forEach((row) => {
    Object.entries(idFields).forEach(([col, prefix]) => {
      if (row[col]) ids.add(`${prefix}${row[col]}`);
    });
  });
  return ids;
}

// ── Styles ────────────────────────────────────────────────────────────────────
const s = {
  panel: {
    width: 360,
    display: "flex",
    flexDirection: "column",
    background: "#151820",
    borderLeft: "1px solid #2a2f3e",
    height: "100%",
    fontFamily: "IBM Plex Sans, sans-serif",
  },
  header: {
    padding: "14px 16px 12px",
    borderBottom: "1px solid #2a2f3e",
  },
  title: {
    display: "block",
    fontSize: 14,
    fontWeight: 600,
    color: "#e2e8f0",
  },
  subtitle: {
    display: "block",
    fontSize: 11,
    color: "#64748b",
    marginTop: 2,
  },
  messages: {
    flex: 1,
    overflowY: "auto",
    padding: 14,
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  empty: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  emptyTitle: {
    fontSize: 11,
    color: "#64748b",
    marginBottom: 4,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    fontFamily: "IBM Plex Mono, monospace",
  },
  suggestion: {
    background: "#1e2230",
    border: "1px solid #2a2f3e",
    borderRadius: 6,
    color: "#94a3b8",
    fontSize: 12,
    padding: "8px 10px",
    textAlign: "left",
    cursor: "pointer",
    lineHeight: 1.4,
    fontFamily: "IBM Plex Sans, sans-serif",
  },
  bubble: {
    padding: "9px 12px",
    borderRadius: 8,
    fontSize: 13,
    lineHeight: 1.55,
    maxWidth: "100%",
  },
  user: {
    background: "#1d4ed822",
    border: "1px solid #1d4ed844",
    color: "#93c5fd",
    alignSelf: "flex-end",
    marginLeft: 24,
  },
  assistant: {
    background: "#1e2230",
    border: "1px solid #2a2f3e",
    color: "#e2e8f0",
    marginRight: 24,
  },
  thinking: {
    color: "#64748b",
    fontStyle: "italic",
    fontSize: 12,
  },
  sqlContainer: {
    marginTop: 4,
    marginLeft: 0,
  },
  sqlToggle: {
    background: "none",
    border: "none",
    color: "#3b82f6",
    fontSize: 11,
    cursor: "pointer",
    fontFamily: "IBM Plex Mono, monospace",
    padding: "2px 0",
  },
  sqlBlock: {
    background: "#0d0f14",
    border: "1px solid #2a2f3e",
    borderRadius: 6,
    padding: "8px 10px",
    fontSize: 11,
    color: "#94a3b8",
    overflowX: "auto",
    marginTop: 4,
    fontFamily: "IBM Plex Mono, monospace",
    lineHeight: 1.5,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  rowCount: {
    fontSize: 10,
    color: "#64748b",
    marginLeft: 8,
    fontFamily: "IBM Plex Mono, monospace",
  },
  inputRow: {
    display: "flex",
    gap: 8,
    padding: "12px 14px",
    borderTop: "1px solid #2a2f3e",
  },
  input: {
    flex: 1,
    background: "#1e2230",
    border: "1px solid #2a2f3e",
    borderRadius: 6,
    color: "#e2e8f0",
    fontSize: 13,
    padding: "8px 10px",
    fontFamily: "IBM Plex Sans, sans-serif",
    outline: "none",
  },
  sendBtn: {
    background: "#3b82f6",
    border: "none",
    borderRadius: 6,
    color: "#fff",
    width: 36,
    fontSize: 18,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 700,
  },
};
