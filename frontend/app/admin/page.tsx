"use client";

import React, { useEffect, useState, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import Sidebar from "../components/Sidebar";
import { UploadCloud, FileText, Trash2, CheckCircle2, AlertCircle, Loader2, RefreshCw } from "lucide-react";

interface DocumentItem {
  id: string;
  filename: string;
  storage_path: string;
  content_type: string;
  file_size: number;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  error_message: string | null;
  uploaded_by: string;
  created_at: string;
}

export default function AdminDashboard() {
  const { user, apiFetch, loading: authLoading } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const fetchDocuments = async (silent = false) => {
    if (!silent) setListLoading(true);
    try {
      const res = await apiFetch("/api/v1/documents/");
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error("Failed to fetch documents:", err);
    } finally {
      if (!silent) setListLoading(false);
    }
  };

  // Poll for status updates if any document is in PENDING or PROCESSING state
  useEffect(() => {
    const hasActiveTasks = documents.some(
      (doc) => doc.status === "PENDING" || doc.status === "PROCESSING"
    );

    if (hasActiveTasks) {
      if (!pollingRef.current) {
        pollingRef.current = setInterval(() => {
          fetchDocuments(true);
        }, 3000);
      }
    } else {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [documents]);

  useEffect(() => {
    if (user && user.role === "ADMIN") {
      fetchDocuments();
    }
  }, [user]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploadError(null);
    setUploadSuccess(null);
    setUploadLoading(true);

    const file = files[0];
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await apiFetch("/api/v1/documents/", {
        method: "POST",
        body: formData, // Automatically sets multipart/form-data boundary
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to upload document.");
      }

      setUploadSuccess(`Document "${file.name}" uploaded successfully! Ingestion processing started.`);
      fetchDocuments();
    } catch (err: any) {
      setUploadError(err.message || "An error occurred during file upload.");
    } finally {
      setUploadLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDeleteDocument = async (docId: string, filename: string) => {
    if (!confirm(`Are you sure you want to delete and de-index document "${filename}"?`)) return;

    try {
      const res = await apiFetch(`/api/v1/documents/${docId}`, {
        method: "DELETE",
      });

      if (res.ok) {
        setDocuments((prev) => prev.filter((d) => d.id !== docId));
      } else {
        const errorData = await res.json().catch(() => ({}));
        alert(errorData.detail || "Failed to delete document.");
      }
    } catch (err) {
      console.error("Delete failed:", err);
      alert("An error occurred during deletion.");
    }
  };

  const formatBytes = (bytes: number, decimals = 2) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
  };

  if (authLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-950">
        <Loader2 className="h-8 w-8 animate-spin text-teal-400" />
      </div>
    );
  }

  if (user.role !== "ADMIN") {
    return null; // AuthContext handles redirect
  }

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100 overflow-hidden">
      {/* Sidebar navigation */}
      <Sidebar activeSessionId={null} onSelectSession={() => {}} refreshTrigger={0} />

      {/* Main Content Pane */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto bg-zinc-950/40 p-8">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-850 pb-5">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-white">Document Management</h2>
            <p className="text-sm text-zinc-400">Upload, parse, and index corporate policy documents into vector storage.</p>
          </div>
          <button
            onClick={() => fetchDocuments()}
            className="flex items-center gap-2 rounded-xl bg-zinc-900 px-4 py-2 text-xs font-semibold text-zinc-300 hover:bg-zinc-800 active:scale-[0.98] border border-zinc-800/80 transition-all"
            disabled={listLoading}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${listLoading ? "animate-spin text-teal-400" : ""}`} />
            Refresh
          </button>
        </div>

        {/* Dashboard Grid */}
        <div className="mt-8 grid grid-cols-3 gap-8">
          {/* Upload Zone (Left Column) */}
          <div className="col-span-1 space-y-6">
            <div className="rounded-2xl border border-zinc-800/80 bg-zinc-900/40 p-6 backdrop-blur-xl">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400 mb-4">
                Upload New Document
              </h3>

              {/* Upload Dropzone container */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-zinc-800 p-8 text-center cursor-pointer transition-all duration-200 hover:border-teal-500/50 hover:bg-zinc-900/30 ${
                  uploadLoading ? "opacity-50 pointer-events-none" : ""
                }`}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept=".txt,.pdf,.doc,.docx"
                  className="hidden"
                />
                
                {uploadLoading ? (
                  <Loader2 className="h-10 w-10 animate-spin text-teal-400 mb-4" />
                ) : (
                  <UploadCloud className="h-10 w-10 text-zinc-500 mb-4 group-hover:text-teal-400" />
                )}
                
                <p className="text-sm font-semibold text-zinc-200">
                  {uploadLoading ? "Uploading & Processing..." : "Select File to Upload"}
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  PDF, TXT, DOC, DOCX up to 10MB
                </p>
              </div>

              {/* Status alerts */}
              {uploadSuccess && (
                <div className="mt-4 flex gap-2.5 rounded-lg border border-teal-500/30 bg-teal-500/10 p-3 text-xs text-teal-400 leading-normal animate-fade-in">
                  <CheckCircle2 className="h-4.5 w-4.5 flex-shrink-0" />
                  <p>{uploadSuccess}</p>
                </div>
              )}
              {uploadError && (
                <div className="mt-4 flex gap-2.5 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400 leading-normal animate-fade-in">
                  <AlertCircle className="h-4.5 w-4.5 flex-shrink-0" />
                  <p>{uploadError}</p>
                </div>
              )}
            </div>
          </div>

          {/* Documents Table (Right Columns) */}
          <div className="col-span-2 rounded-2xl border border-zinc-800/80 bg-zinc-900/40 p-6 backdrop-blur-xl">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400 mb-4">
              Indexed Documents Registry
            </h3>

            {listLoading && documents.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-teal-400 mb-4" />
                <p className="text-sm text-zinc-500">Loading document registry...</p>
              </div>
            ) : documents.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <FileText className="h-12 w-12 text-zinc-700 mb-4" />
                <p className="text-sm font-semibold text-zinc-400">No documents indexed</p>
                <p className="mt-1 text-xs text-zinc-650">Upload policy docs to establish context for RAG.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-850 text-xxs font-semibold uppercase tracking-wider text-zinc-500">
                      <th className="py-3 px-4">Filename</th>
                      <th className="py-3 px-4">Size</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Indexed On</th>
                      <th className="py-3 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-850/50">
                    {documents.map((doc) => (
                      <tr key={doc.id} className="hover:bg-zinc-900/20 group">
                        <td className="py-3.5 px-4 font-medium text-zinc-200">
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-zinc-500 flex-shrink-0" />
                            <span className="truncate max-w-[200px]" title={doc.filename}>
                              {doc.filename}
                            </span>
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-zinc-400">
                          {formatBytes(doc.file_size)}
                        </td>
                        <td className="py-3.5 px-4">
                          {doc.status === "COMPLETED" && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-teal-500/10 px-2.5 py-0.5 text-xs font-semibold text-teal-400">
                              <span className="h-1.5 w-1.5 rounded-full bg-teal-400" />
                              Ready
                            </span>
                          )}
                          {doc.status === "PENDING" && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-zinc-500/10 px-2.5 py-0.5 text-xs font-semibold text-zinc-450">
                              <span className="h-1.5 w-1.5 rounded-full bg-zinc-500" />
                              Queued
                            </span>
                          )}
                          {doc.status === "PROCESSING" && (
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-500/10 px-2.5 py-0.5 text-xs font-semibold text-indigo-400">
                              <Loader2 className="h-3 w-3 animate-spin text-indigo-400" />
                              Parsing
                            </span>
                          )}
                          {doc.status === "FAILED" && (
                            <span 
                              className="inline-flex items-center gap-1 rounded-full bg-red-500/10 px-2.5 py-0.5 text-xs font-semibold text-red-400 cursor-help"
                              title={doc.error_message || "Ingestion task failed"}
                            >
                              <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                              Error
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-zinc-500 text-xs">
                          {new Date(doc.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <button
                            onClick={() => handleDeleteDocument(doc.id, doc.filename)}
                            className="p-1.5 text-zinc-500 hover:text-red-400 hover:bg-zinc-800 rounded-lg transition-all"
                            title="De-index Document"
                          >
                            <Trash2 className="h-4.5 w-4.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
