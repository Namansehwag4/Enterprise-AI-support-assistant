"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";

interface User {
  id: string;
  email: string;
  fullName: string;
  role: "EMPLOYEE" | "ADMIN";
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string, role: string) => Promise<void>;
  logout: () => void;
  apiFetch: (endpoint: string, options?: RequestInit) => Promise<Response>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  // Load token and user from localStorage on mount
  useEffect(() => {
    async function initializeAuth() {
      const storedToken = localStorage.getItem("auth_token");
      if (storedToken) {
        try {
          // Fetch current user details to verify token
          const res = await fetch(`${API_URL}/api/v1/auth/me`, {
            headers: {
              Authorization: `Bearer ${storedToken}`,
            },
          });

          if (res.ok) {
            const userData = await res.json();
            setUser({
              id: userData.id,
              email: userData.email,
              fullName: userData.full_name,
              role: userData.role,
            });
            setToken(storedToken);
          } else {
            // Token is invalid/expired
            localStorage.removeItem("auth_token");
          }
        } catch (err) {
          console.error("Auth initialization failed:", err);
        }
      }
      setLoading(false);
    }
    initializeAuth();
  }, []);

  // Enforce route protection
  useEffect(() => {
    if (loading) return;

    const publicPages = ["/login", "/register"];
    const isPublicPage = publicPages.includes(pathname);

    if (!token && !isPublicPage) {
      router.push("/login");
    } else if (token && isPublicPage) {
      // Redirect authenticated users away from login/register
      if (user?.role === "ADMIN") {
        router.push("/admin");
      } else {
        router.push("/");
      }
    } else if (token && pathname === "/admin" && user?.role !== "ADMIN") {
      // Protect admin routes
      router.push("/");
    }
  }, [token, pathname, loading, user, router]);

  const login = async (email: string, password: string) => {
    // FastAPI OAuth2PasswordRequestForm expects application/x-www-form-urlencoded
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const response = await fetch(`${API_URL}/api/v1/auth/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || "Authentication failed. Please check credentials.");
    }

    const data = await response.json();
    const accessToken = data.access_token;
    const refreshToken = data.refresh_token;
    localStorage.setItem("auth_token", accessToken);
    if (refreshToken) {
      localStorage.setItem("refresh_token", refreshToken);
    }
    setToken(accessToken);

    // Fetch user details
    const userRes = await fetch(`${API_URL}/api/v1/auth/me`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!userRes.ok) {
      logout();
      throw new Error("Failed to load user profile after login.");
    }

    const userData = await userRes.json();
    const activeUser: User = {
      id: userData.id,
      email: userData.email,
      fullName: userData.full_name,
      role: userData.role,
    };

    setUser(activeUser);

    if (activeUser.role === "ADMIN") {
      router.push("/admin");
    } else {
      router.push("/");
    }
  };

  const register = async (email: string, password: string, fullName: string, role: string) => {
    const response = await fetch(`${API_URL}/api/v1/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        password,
        full_name: fullName,
        role,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || "Registration failed. Email might already exist.");
    }

    // After registration, automatically log in
    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("refresh_token");
    setToken(null);
    setUser(null);
    router.push("/login");
  };

  // Helper fetch function that automatically injects JWT and handles 401 auto-refreshes
  const apiFetch = async (endpoint: string, options: RequestInit = {}) => {
    let storedToken = localStorage.getItem("auth_token") || token;
    const headers = new Headers(options.headers || {});
    
    if (storedToken) {
      headers.set("Authorization", `Bearer ${storedToken}`);
    }

    const url = endpoint.startsWith("http") ? endpoint : `${API_URL}${endpoint}`;
    let res = await fetch(url, {
      ...options,
      headers,
    });

    if (res.status === 401) {
      const storedRefreshToken = localStorage.getItem("refresh_token");
      if (storedRefreshToken) {
        try {
          const refreshRes = await fetch(`${API_URL}/api/v1/auth/refresh`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ refresh_token: storedRefreshToken }),
          });

          if (refreshRes.ok) {
            const data = await refreshRes.json();
            const newAccessToken = data.access_token;
            const newRefreshToken = data.refresh_token;

            localStorage.setItem("auth_token", newAccessToken);
            if (newRefreshToken) {
              localStorage.setItem("refresh_token", newRefreshToken);
            }
            setToken(newAccessToken);

            // Retry original request with new access token
            headers.set("Authorization", `Bearer ${newAccessToken}`);
            res = await fetch(url, {
              ...options,
              headers,
            });
            return res;
          }
        } catch (err) {
          console.error("Token auto-refresh failed:", err);
        }
      }
      logout();
    }

    return res;
  };

  const isAuthenticated = !!token;

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated,
        loading,
        login,
        register,
        logout,
        apiFetch,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
