"use client";

import React from "react";
import { X, FileText, Bookmark, Quote, Info } from "lucide-react";

interface Citation {
  id: string;
  document_id: string;
  filename: string;
  snippet: string;
  page_number?: number | null;
}

interface CitationViewerProps {
  citation: Citation | null;
  onClose: () => void;
}

export default function CitationViewer({ citation, onClose }: CitationViewerProps) {
  if (!citation) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div 
        className="relative w-full max-w-lg overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-900 shadow-2xl transition-all scale-100 animate-scale-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-850 bg-zinc-900/50 py-4 px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-500/10 text-teal-400">
              <FileText className="h-4.5 w-4.5" />
            </div>
            <div>
              <h3 className="font-semibold text-zinc-150">Citation Source</h3>
              <p className="text-xs text-zinc-500">Document Reference Detail</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-white transition-all"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content body */}
        <div className="p-6 space-y-5">
          {/* Metadata Cards */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-zinc-850 bg-zinc-950/40 p-3.5">
              <div className="flex items-center gap-2 text-zinc-500 text-xs font-medium uppercase tracking-wider mb-1">
                <FileText className="h-3.5 w-3.5" />
                Document Name
              </div>
              <p className="text-sm font-semibold text-zinc-200 truncate" title={citation.filename}>
                {citation.filename}
              </p>
            </div>

            <div className="rounded-xl border border-zinc-850 bg-zinc-950/40 p-3.5">
              <div className="flex items-center gap-2 text-zinc-500 text-xs font-medium uppercase tracking-wider mb-1">
                <Bookmark className="h-3.5 w-3.5" />
                Page Reference
              </div>
              <p className="text-sm font-semibold text-zinc-200">
                {citation.page_number !== undefined && citation.page_number !== null
                  ? `Page ${citation.page_number}`
                  : "N/A (Single-page document)"}
              </p>
            </div>
          </div>

          {/* Snippet quote box */}
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-zinc-500 text-xs font-medium uppercase tracking-wider">
              <Quote className="h-3.5 w-3.5" />
              Retrieved Context Snippet
            </div>
            <div className="relative rounded-xl border border-zinc-850 bg-zinc-950/80 p-5 font-mono text-xs leading-relaxed text-zinc-350 shadow-inner">
              <div className="absolute top-3 right-3 text-zinc-800 pointer-events-none select-none text-2xl font-serif">
                &ldquo;
              </div>
              <p className="whitespace-pre-wrap">{citation.snippet}</p>
            </div>
          </div>

          {/* Helper info */}
          <div className="flex gap-2 rounded-lg bg-zinc-950/30 border border-zinc-850/50 p-3 text-xxs text-zinc-500 leading-normal">
            <Info className="h-4 w-4 text-teal-500/80 flex-shrink-0" />
            <p>
              This snippet represents the exact segment retrieved from the vector storage. It was re-ranked and supplied to the AI engine to generate the response above.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-zinc-850 bg-zinc-900/50 py-3.5 px-6 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-lg bg-zinc-800 py-2 px-4 text-xs font-semibold text-zinc-300 hover:bg-zinc-750 hover:text-white transition-all active:scale-[0.98]"
          >
            Close Viewer
          </button>
        </div>
      </div>
    </div>
  );
}
