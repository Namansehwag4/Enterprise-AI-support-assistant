"use client";

import React, { useEffect, useState, useRef } from "react";
import { useAuth } from "./context/AuthContext";
import Sidebar from "./components/Sidebar";
import CitationViewer from "./components/CitationViewer";
import { Send, Sparkles, Loader2, MessageSquare, AlertCircle, FileText, ArrowRight } from "lucide-react";

interface Citation {
  id: string;
  document_id: string;
  filename: string;
  snippet: string;
  page_number?: number | null;
}

interface Message {
  id: string;
  sender: "USER" | "ASSISTANT";
  content: string;
  created_at: string;
  citations?: Citation[];
}

const SUGGESTIONS = [
  {
    title: "Meal Allowance limits",
    prompt: "What is the daily meal allowance limit for travel?",
  },
  {
    title: "Claim travel reimbursement",
    prompt: "How do I file a claim for travel expense reimbursement?",
  },
  {
    title: "Flight bookings policy",
    prompt: "What class of flight is allowed for business travel?",
  },
];

export default function Home() {
  const { user, apiFetch, token, loading: authLoading } = useAuth();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [sidebarRefresh, setSidebarRefresh] = useState(0);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Scroll to bottom whenever messages list grows or is currently streaming
  useEffect(() => {
    scrollToBottom();
  }, [messages, isGenerating]);

  // Load chat session history when selected
  useEffect(() => {
    async function loadHistory() {
      if (!activeSessionId) {
        setMessages([]);
        return;
      }

      setMessagesLoading(true);
      try {
        const res = await apiFetch(`/api/v1/chat/sessions/${activeSessionId}`);
        if (res.ok) {
          const data = await res.json();
          // Message format returned: list of messages, each with sender, content, citations
          setMessages(
            data.messages.map((m: any) => ({
              id: m.id,
              sender: m.sender,
              content: m.content,
              created_at: m.created_at,
              citations: m.citations || [],
            }))
          );
        }
      } catch (err) {
        console.error("Failed to load chat history:", err);
      } finally {
        setMessagesLoading(false);
      }
    }
    loadHistory();
  }, [activeSessionId]);

  const handleSendMessage = async (textToSend?: string) => {
    const content = (textToSend || inputMessage).trim();
    if (!content || isGenerating) return;

    setInputMessage("");
    setIsGenerating(true);

    let currentSessionId = activeSessionId;

    // Create session first if none is active
    if (!currentSessionId) {
      try {
        // Create title from first query snippet
        const title = content.length > 25 ? `${content.substring(0, 25)}...` : content;
        const res = await apiFetch("/api/v1/chat/sessions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ title }),
        });

        if (!res.ok) {
          throw new Error("Failed to create chat session.");
        }

        const newSession = await res.json();
        currentSessionId = newSession.id;
        setActiveSessionId(currentSessionId);
        setSidebarRefresh((prev) => prev + 1);
      } catch (err) {
        console.error("Session creation failed:", err);
        setIsGenerating(false);
        alert("Failed to initialize conversation session.");
        return;
      }
    }

    // Append user message immediately
    const userMessageId = Math.random().toString(); // Temporary local ID
    const userMsg: Message = {
      id: userMessageId,
      sender: "USER",
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    // Append empty assistant message placeholder to stream into
    const assistantMessageId = Math.random().toString();
    const assistantMsgPlaceholder: Message = {
      id: assistantMessageId,
      sender: "ASSISTANT",
      content: "",
      created_at: new Date().toISOString(),
      citations: [],
    };
    setMessages((prev) => [...prev, assistantMsgPlaceholder]);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${API_URL}/api/v1/chat/sessions/${currentSessionId}/messages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("auth_token") || token}`,
        },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        throw new Error("Failed to post message to RAG stream.");
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("Response body is not readable.");

      let buffer = "";
      let accumulatedText = "";
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep partial line in buffer

        for (const line of lines) {
          const cleanLine = line.trim();
          if (!cleanLine) continue;

          if (cleanLine.startsWith("data: ")) {
            const dataVal = cleanLine.slice(6);
            
            if (dataVal.startsWith("[METADATA]")) {
              try {
                const metadata = JSON.parse(dataVal.slice(10));
                
                // Update placeholder with actual DB ID and citations payload
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? {
                          ...msg,
                          id: metadata.message_id,
                          citations: metadata.citations || [],
                        }
                      : msg
                  )
                );
              } catch (e) {
                console.error("Failed to parse RAG metadata:", e);
              }
            } else {
              // Append streamed text chunk
              accumulatedText += dataVal;
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, content: accumulatedText }
                    : msg
                )
              );
            }
          }
        }
      }
    } catch (err) {
      console.error("Streaming failed:", err);
      // Update placeholder with error notice
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                content: "⚠️ An error occurred while retrieving policy answers. Please try again.",
              }
            : msg
        )
      );
    } finally {
      setIsGenerating(false);
    }
  };

  // Convert raw citations brackets [1], [2] to clickable nodes or format citations
  const renderMessageContent = (msg: Message) => {
    if (msg.sender === "USER") {
      return <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>;
    }

    const citations = msg.citations || [];
    if (citations.length === 0) {
      return <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>;
    }

    // Convert text citations like [DocID:page_number] or general numbers [1] to pill links
    // For simplicity, we can render the main body, then show a list of clickable citations at the bottom of the card
    return (
      <div className="space-y-4">
        <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
        
        {/* Citations list footer */}
        <div className="border-t border-zinc-800/80 pt-3 mt-2">
          <p className="text-xxs font-semibold uppercase tracking-wider text-zinc-500 mb-2">
            Verified Sources
          </p>
          <div className="flex flex-wrap gap-2">
            {citations.map((cit, idx) => (
              <button
                key={cit.id || idx}
                onClick={() => setActiveCitation(cit)}
                className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-950/40 py-1 px-2.5 text-xs text-zinc-350 transition-all hover:border-teal-500/50 hover:bg-zinc-900 active:scale-[0.98]"
              >
                <FileText className="h-3 w-3 text-teal-400" />
                <span className="max-w-[120px] truncate">{cit.filename}</span>
                {cit.page_number && (
                  <span className="text-xxs text-zinc-550 border-l border-zinc-800 pl-1.5">
                    p. {cit.page_number}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  };

  if (authLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-950">
        <Loader2 className="h-8 w-8 animate-spin text-teal-400" />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100 overflow-hidden">
      {/* Sidebar navigation */}
      <Sidebar
        activeSessionId={activeSessionId}
        onSelectSession={setActiveSessionId}
        refreshTrigger={sidebarRefresh}
      />

      {/* Main chat Workspace panel */}
      <main className="flex-1 flex flex-col min-w-0 bg-zinc-950/40 relative">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-850 bg-zinc-950/40 py-4.5 px-8 shadow-sm">
          <div>
            <h2 className="text-md font-bold text-white">
              {activeSessionId ? "Policy Q&A Session" : "New Support Chat"}
            </h2>
            <p className="text-xxs text-zinc-500 font-medium uppercase tracking-wider mt-0.5">
              Secure Retrieval-Augmented Generation
            </p>
          </div>
        </div>

        {/* Conversation Box */}
        <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6 scrollbar-thin">
          {messagesLoading ? (
            <div className="flex flex-col items-center justify-center h-full">
              <Loader2 className="h-8 w-8 animate-spin text-teal-400 mb-2" />
              <p className="text-xs text-zinc-500">Retrieving thread history...</p>
            </div>
          ) : messages.length === 0 ? (
            /* Empty State */
            <div className="flex flex-col items-center justify-center h-full max-w-2xl mx-auto text-center space-y-8 animate-fade-in">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-tr from-teal-500/10 to-indigo-500/10 border border-teal-500/20 shadow-md">
                <Sparkles className="h-8 w-8 text-teal-400" />
              </div>
              <div className="space-y-3">
                <h3 className="text-xl font-bold text-white">How can I help you today?</h3>
                <p className="text-sm text-zinc-400">
                  Ask questions about corporate rules, flight guidelines, meal allowance limits, or claim procedures. I will answer based on indexed document contexts.
                </p>
              </div>

              {/* Suggestions Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full pt-4">
                {SUGGESTIONS.map((s, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleSendMessage(s.prompt)}
                    className="flex flex-col text-left rounded-xl border border-zinc-850 bg-zinc-900/30 p-4 cursor-pointer hover:border-teal-500/40 hover:bg-zinc-900/60 group transition-all duration-200"
                  >
                    <h4 className="text-xs font-bold text-zinc-200 group-hover:text-teal-400 transition-colors">
                      {s.title}
                    </h4>
                    <p className="mt-1 text-xs text-zinc-500 leading-normal flex-1">
                      {s.prompt}
                    </p>
                    <ArrowRight className="h-4 w-4 text-zinc-650 self-end mt-3 group-hover:text-teal-400 group-hover:translate-x-1 transition-all duration-200" />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* Messages Feed */
            <div className="max-w-4xl mx-auto space-y-6">
              {messages.map((msg) => {
                const isUser = msg.sender === "USER";
                return (
                  <div
                    key={msg.id}
                    className={`flex gap-4 ${isUser ? "justify-end" : "justify-start animate-fade-in"}`}
                  >
                    {/* User profile bubble vs Assistant icon */}
                    {!isUser && (
                      <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400">
                        <Sparkles className="h-4.5 w-4.5" />
                      </div>
                    )}

                    {/* Chat Bubble card container */}
                    <div
                      className={`max-w-2xl rounded-2xl p-5 text-sm shadow-md border ${
                        isUser
                          ? "bg-teal-500/15 border-teal-500/20 text-zinc-100"
                          : "bg-zinc-900/60 border-zinc-850/80 text-zinc-300 backdrop-blur-md"
                      }`}
                    >
                      {renderMessageContent(msg)}
                    </div>
                  </div>
                );
              })}

              {/* Streaming loading indicator inside feed */}
              {isGenerating && messages[messages.length - 1]?.content === "" && (
                <div className="flex gap-4 justify-start">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400">
                    <Loader2 className="h-4.5 w-4.5 animate-spin" />
                  </div>
                  <div className="rounded-2xl p-5 text-sm bg-zinc-900/60 border border-zinc-850/80 text-zinc-500 italic">
                    Retrieving matching contexts and compiling answer...
                  </div>
                </div>
              )}

              {/* Scrolling target reference */}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="border-t border-zinc-850 bg-zinc-950/40 p-6">
          <div className="max-w-4xl mx-auto">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="relative flex items-center"
            >
              <input
                type="text"
                disabled={isGenerating}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Ask support assistant verified by policy guidelines..."
                className="w-full rounded-xl border border-zinc-850 bg-zinc-950/80 py-4.5 pl-5 pr-14 text-sm text-zinc-200 placeholder-zinc-500 shadow-inner outline-none transition-all duration-200 focus:border-teal-500/80 focus:ring-1 focus:ring-teal-500/20 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!inputMessage.trim() || isGenerating}
                className="absolute right-3.5 rounded-lg bg-teal-500/10 border border-teal-500/20 p-2 text-teal-400 hover:bg-teal-500 hover:text-white transition-all active:scale-[0.98] disabled:opacity-30 disabled:hover:bg-teal-500/10 disabled:hover:text-teal-400"
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
            <p className="mt-2 text-center text-xxs text-zinc-600">
              Verified by Retrieval-Augmented Generation context indexes.
            </p>
          </div>
        </div>
      </main>

      {/* Citation Overlay details modal */}
      <CitationViewer citation={activeCitation} onClose={() => setActiveCitation(null)} />
    </div>
  );
}
