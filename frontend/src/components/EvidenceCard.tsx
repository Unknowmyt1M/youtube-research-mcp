import React from 'react';
import { Play, ExternalLink, Quote, Award } from 'lucide-react';
import { SourceCitation } from '../types';

interface EvidenceCardProps {
  citation: SourceCitation;
  onPlayTimestamp?: (videoId: string, seconds: number) => void;
  isCompact?: boolean;
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({
  citation,
  onPlayTimestamp,
  isCompact = false,
}) => {
  const matchPct = Math.round(citation.relevance * 100);

  return (
    <div className="group relative rounded-xl bg-surface-raised/70 hover:bg-surface-raised border border-border/80 hover:border-red-500/40 p-4 transition-all duration-200 shadow-sm hover:shadow-md">
      {/* Top Header: Video Info & Timecode */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center space-x-2 min-w-0">
          <span className="text-xs font-semibold text-gray-200 truncate group-hover:text-red-300 transition">
            {citation.video_title}
          </span>
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-border text-gray-400 font-medium shrink-0">
            {citation.channel}
          </span>
        </div>

        {/* Relevance Score Pill */}
        <div className="flex items-center space-x-1 shrink-0">
          <span
            className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded-md ${
              matchPct >= 80
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : matchPct >= 50
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                : 'bg-gray-800 text-gray-400 border border-gray-700'
            }`}
          >
            {matchPct}% Match
          </span>
        </div>
      </div>

      {/* Quote Body */}
      <div className="relative pl-3 border-l-2 border-red-500/40 mb-3 text-xs sm:text-sm text-gray-300 italic leading-relaxed">
        <Quote className="w-3 h-3 text-red-500/40 absolute -left-1.5 -top-1 fill-red-500/20" />
        "{citation.quote}"
      </div>

      {/* Footer Controls: Jump to timestamp & URL */}
      <div className="flex items-center justify-between pt-2 border-t border-border/40 text-xs">
        <button
          onClick={() =>
            onPlayTimestamp?.(citation.video_id, citation.start_seconds)
          }
          className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-red-600/10 hover:bg-red-600 text-red-400 hover:text-white font-mono font-medium transition"
        >
          <Play className="w-3 h-3 fill-current" />
          <span>Play @ {citation.time_range}</span>
        </button>

        <a
          href={citation.url_with_timestamp}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center space-x-1 text-gray-400 hover:text-gray-200 transition"
        >
          <span className="text-[11px]">YouTube Deep Link</span>
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
};
