import { useEffect, useRef, useState } from "react";
import { resetSession, sendMessage, type ToolCall } from "./api";

interface ChatMessage {
  role: "user" | "agent";
  text: string;
  tools?: ToolCall[];
}

const EXAMPLES = [
  "Plan 3 days in Rome, budget 500 EUR, I like food and history",
  "2 days in Budapest, budget 300 EUR, I like history",
  "Weekend in Berlin, budget 400 EUR, I like museums",
];

function formatTool(tool: ToolCall): string {
  const args = Object.entries(tool.args)
    .map(([key, value]) => `${key}=${String(value)}`)
    .join(", ");
  return `${tool.name}(${args})`;
}

export default function App() {
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll to the newest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setError(null);
    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setInput("");
    setLoading(true);

    try {
      const data = await sendMessage(sessionId, trimmed);
      setMessages((prev) => [
        ...prev,
        { role: "agent", text: data.reply, tools: data.tools },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function newChat() {
    await resetSession(sessionId);
    setSessionId(crypto.randomUUID());
    setMessages([]);
    setError(null);
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Travel Planning Agent</h1>
        <button className="ghost" onClick={newChat} disabled={loading}>
          New chat
        </button>
      </header>

      <main className="chat">
        {messages.length === 0 && (
          <div className="empty">
            <p>Tell me where you want to go, for how long, and your budget.</p>
            <div className="examples">
              {EXAMPLES.map((example) => (
                <button key={example} className="chip" onClick={() => send(example)}>
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            <div className="text">{m.text}</div>
            {m.tools && m.tools.length > 0 && (
              <div className="tools">
                {m.tools.map((tool, j) => (
                  <span key={j} className="tool">
                    {formatTool(tool)}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="bubble agent">
            <div className="text muted">Thinking... the first answer can take a while.</div>
          </div>
        )}
        {error && <div className="error">{error}</div>}
        <div ref={bottomRef} />
      </main>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. 3 days in Rome, budget 500 EUR"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
