"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAuth } from "../context/AuthContext";
import { Lock, Mail, Loader2, Sparkles } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.message || "Invalid username or password");
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-radial from-zinc-900 to-zinc-950 px-4 py-12 sm:px-6 lg:px-8">
      {/* Dynamic background highlights */}
      <div className="absolute top-1/4 left-1/4 -z-10 h-72 w-72 rounded-full bg-teal-500/10 blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 -z-10 h-72 w-72 rounded-full bg-indigo-500/10 blur-3xl" />

      <div className="w-full max-w-md space-y-8 rounded-2xl border border-zinc-800/80 bg-zinc-900/60 p-8 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-col items-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-tr from-teal-500 to-indigo-600 shadow-lg shadow-teal-500/20">
            <Sparkles className="h-6 w-6 text-white animate-pulse" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-white">
            Sign in to Assistant
          </h2>
          <p className="mt-2 text-center text-sm text-zinc-400">
            Enter your enterprise credentials
          </p>
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">
            <p className="font-medium">Authentication Error</p>
            <p className="mt-1">{error}</p>
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4 rounded-md shadow-sm">
            <div>
              <label htmlFor="email-address" className="sr-only">
                Email address
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                  <Mail className="h-5 w-5 text-zinc-500" />
                </div>
                <input
                  id="email-address"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full rounded-lg border border-zinc-850 bg-zinc-950/80 py-3 pl-10 pr-3 text-sm text-zinc-100 placeholder-zinc-500 shadow-inner outline-none transition-colors duration-200 focus:border-teal-500/80 focus:ring-1 focus:ring-teal-500/30"
                  placeholder="name@company.com"
                />
              </div>
            </div>
            <div>
              <label htmlFor="password" className="sr-only">
                Password
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                  <Lock className="h-5 w-5 text-zinc-500" />
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full rounded-lg border border-zinc-850 bg-zinc-950/80 py-3 pl-10 pr-3 text-sm text-zinc-100 placeholder-zinc-500 shadow-inner outline-none transition-colors duration-200 focus:border-teal-500/80 focus:ring-1 focus:ring-teal-500/30"
                  placeholder="••••••••"
                />
              </div>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="group relative flex w-full justify-center rounded-lg bg-gradient-to-r from-teal-500 to-teal-600 py-3 px-4 text-sm font-semibold text-white shadow-md transition-all duration-200 hover:from-teal-400 hover:to-teal-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-500 focus-visible:outline-offset-2 active:scale-[0.99] disabled:opacity-75 disabled:hover:from-teal-500 disabled:hover:to-teal-600"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </div>
        </form>

        <div className="text-center">
          <p className="text-sm text-zinc-500">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="font-semibold text-teal-400 hover:text-teal-300 transition-colors">
              Register here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
