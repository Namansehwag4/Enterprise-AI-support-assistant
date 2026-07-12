"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { MessageSquare, Plus, Trash2, LogOut, ShieldAlert, ChevronLeft, LayoutDashboard, Sparkles, MessageCircle } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface SidebarProps {
  activeSessionId: string | null;
  onSelectSession: (id: string | null) => void;
  refreshTrigger: number;
}

export default function Sidebar({ activeSessionId, onSelectSession, refreshTrigger }: SidebarProps) {
  const { user, logout, apiFetch } = useAuth();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const fetchSessions = async () => {
    setIsLoading(true);
    try {
      const res = await apiFetch("/api/v1/chat/sessions");
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (err) {
      console.error("Failed to fetch chat sessions:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchSessions();
    }
  }, [user, refreshTrigger]);

  const handleCreateNewChat = () => {
    onSelectSession(null);
    if (pathname !== "/") {
      router.push("/");
    }
  };

  const handleDeleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation(); // Avoid selecting the thread
    if (!confirm("Are you sure you want to delete this chat session?")) return;

    try {
      const res = await apiFetch(`/api/v1/chat/sessions/${sessionId}`, {
        method: "DELETE",
      });

      if (res.ok) {
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
        if (activeSessionId === sessionId) {
          onSelectSession(null);
        }
      }
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  };

  return (
    <aside className="flex h-screen w-80 flex-col border-r border-zinc-800/80 bg-zinc-950/80 p-4 shadow-xl backdrop-blur-xl">
      {/* Brand Header */}
      <div className="flex items-center gap-3 px-2 py-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-teal-500 to-indigo-600 shadow-md shadow-teal-500/10">
          <Sparkles className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-bold bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
            Enterprise AI
          </h1>
          <p className="text-xs text-zinc-500">Support Assistant</p>
        </div>
      </div>

      {/* Action Button: New Chat */}
      <button
        onClick={handleCreateNewChat}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-zinc-800 bg-zinc-900/50 py-3 px-4 text-sm font-semibold text-zinc-200 shadow-sm transition-all duration-200 hover:border-teal-500/50 hover:bg-zinc-900 active:scale-[0.98]"
      >
        <Plus className="h-4 w-4 text-teal-400" />
        New Chat
      </button>

      {/* Navigation Switcher for Admin */}
      {user?.role === "ADMIN" && (
        <div className="mt-4 border-b border-zinc-800 pb-4">
          {pathname === "/admin" ? (
            <Link
              href="/"
              className="flex w-full items-center gap-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 py-2.5 px-4 text-sm font-medium text-indigo-400 hover:bg-indigo-500/20 transition-all duration-200"
            >
              <MessageCircle className="h-4 w-4" />
              Go to Workspace Chat
            </Link>
          ) : (
            <Link
              href="/admin"
              className="flex w-full items-center gap-3 rounded-xl bg-teal-500/10 border border-teal-500/20 py-2.5 px-4 text-sm font-medium text-teal-400 hover:bg-teal-500/20 transition-all duration-200"
            >
              <LayoutDashboard className="h-4 w-4" />
              Admin Portal (Docs)
            </Link>
          )}
        </div>
      )}

      {/* Chat Sessions History List */}
      <div className="mt-6 flex-1 overflow-y-auto space-y-1.5 scrollbar-thin">
        <p className="px-2 text-xs font-semibold uppercase tracking-wider text-zinc-600">
          Chat History
        </p>
        
        {isLoading && sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-zinc-600">
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-zinc-700 border-t-teal-400" />
          </div>
        ) : sessions.length === 0 ? (
          <p className="px-2 py-4 text-sm text-zinc-650 italic">No past conversations</p>
        ) : (
          sessions.map((session) => {
            const isActive = activeSessionId === session.id;
            return (
              <div
                key={session.id}
                onClick={() => {
                  onSelectSession(session.id);
                  if (pathname !== "/") router.push("/");
                }}
                className={`group relative flex cursor-pointer items-center justify-between rounded-xl py-3 px-4 text-sm transition-all duration-150 ${
                  isActive
                    ? "bg-zinc-850 text-white font-medium shadow-inner border-l-2 border-teal-500"
                    : "text-zinc-400 hover:bg-zinc-900/60 hover:text-zinc-200"
                }`}
              >
                <div className="flex items-center gap-3 min-w-0 pr-6">
                  <MessageSquare className={`h-4 w-4 flex-shrink-0 ${isActive ? "text-teal-400" : "text-zinc-600 group-hover:text-zinc-400"}`} />
                  <span className="truncate">{session.title}</span>
                </div>
                <button
                  onClick={(e) => handleDeleteSession(e, session.id)}
                  className="absolute right-3 opacity-0 group-hover:opacity-100 p-1 text-zinc-500 hover:text-red-400 hover:bg-zinc-800 rounded-md transition-all duration-150"
                  title="Delete Conversation"
                >
                  <Trash2 className="h-4.5 w-4.5" />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* User Footer Account Info & Actions */}
      <div className="mt-auto border-t border-zinc-850 pt-4">
        <div className="flex items-center justify-between rounded-xl bg-zinc-900/40 p-3 border border-zinc-900/80">
          <div className="min-w-0 pr-2">
            <p className="truncate text-sm font-semibold text-zinc-200">{user?.fullName}</p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className={`inline-block h-1.5 w-1.5 rounded-full ${user?.role === "ADMIN" ? "bg-indigo-400" : "bg-teal-400"}`} />
              <p className="text-xxs font-medium uppercase tracking-wider text-zinc-500">
                {user?.role}
              </p>
            </div>
          </div>
          <button
            onClick={logout}
            className="p-2 text-zinc-500 hover:text-red-400 hover:bg-zinc-850 rounded-xl transition-all"
            title="Sign Out"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </div>
    </aside>
  );
}
