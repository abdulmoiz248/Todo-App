"use client";
import { useEffect, useRef, useState } from "react";
import { Send, Loader2 } from "lucide-react";
import { motion } from "framer-motion";

export default function ToDoGPT() {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const [hasStarted, setHasStarted] = useState(false);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage() {
    if (!input.trim() || isLoading) return;
    const userMsg = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setHasStarted(true);
    setIsLoading(true);
    setInput("");

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMsg.content }),
      });
      const data = await res.json();

      setMessages((prev) => [...prev, { role: "assistant", content: data.response }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "⚠️ Failed to get response. Try again." },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen bg-[#343541] text-gray-200 px-6 py-4">
      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto px-2 py-4 space-y-3 scrollbar-hide">
        {messages.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="h-full flex flex-col items-center justify-center text-gray-400"
          >
            <h1 className="text-3xl font-bold mb-3">👋 Hi Abdul</h1>
            <p className="text-base">
              Welcome to <span className="text-[#10a37f]">ToDoGPT</span>. What’s on your mind
              today?
            </p>
          </motion.div>
        ) : (
          messages.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
              className={`flex w-full ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[75%] px-4 py-3 rounded-xl whitespace-pre-wrap leading-relaxed shadow-sm ${
                  m.role === "user"
                    ? "bg-[#10a37f] text-white rounded-br-none"
                    : "bg-[#444654] text-gray-100 rounded-bl-none"
                }`}
              >
                {m.content}
              </div>
            </motion.div>
          ))
        )}

        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex w-full justify-start"
          >
            <div className="max-w-[75%] px-4 py-3 rounded-xl bg-[#444654] text-gray-300 flex items-center gap-2">
              <Loader2 className="animate-spin" size={18} />
              Thinking...
            </div>
          </motion.div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input Area */}
      <div
        className={`${
          hasStarted ? "sticky bottom-0" : "absolute inset-x-0 bottom-10"
        } px-2`}
      >
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="max-w-3xl mx-auto w-full bg-[#40414f] flex items-center gap-3 px-4 py-3 rounded-xl border border-gray-600 shadow-md"
        >
          <input
            className="flex-1 bg-transparent text-gray-100 placeholder-gray-400 focus:outline-none text-base"
            placeholder="Message ToDoGPT..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={isLoading}
            className={`text-gray-300 hover:text-white transition ${
              isLoading ? "opacity-50 cursor-not-allowed" : ""
            }`}
          >
            {isLoading ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
          </button>
        </motion.div>
        {!hasStarted && (
          <p className="text-xs text-center text-gray-400 mt-3">
            ToDoGPT can make mistakes. Check important info.
          </p>
        )}
      </div>
    </div>
  );
}
