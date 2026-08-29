import React, { useState } from 'react';
import { Compass, Search, Loader2, Play, Sparkles, ExternalLink, Clock, Tag } from 'lucide-react';
import { api } from '../api/client';
import { TranscriptSearchMatch } from '../types';
import { YouTubePlayer } from '../components/YouTubePlayer';

export const PinpointPlayer: React.FC = () => {
  const [videoUrl, setVideoUrl] = useState('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
  const [conceptQuery, setConceptQuery] = useState('never gonna give you up');
  const [maxResults, setMaxResults] = useState(5);
  const [isLoading, setIsLoading] = useState(false);
  const [matches, setMatches] = useState<TranscriptSearchMatch[]>([]);
  const [activeVideoId, setActiveVideoId] = useState('dQw4w9WgXcQ');
  const [currentSeconds, setCurrentSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const extractCleanId = (input: string): string => {
    const clean = input.trim();
    if (clean.length === 11 && !clean.includes('/')) return clean;
    const match = clean.match(/(?:v=|\/embed\/|\/live\/|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
    return match ? match[1] : clean;
  };

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const vid = extractCleanId(videoUrl);
    if (!vid || !conceptQuery.trim()) return;

    setActiveVideoId(vid);
    setIsLoading(true);
    setError(null);

    try {
      const res = await api.findInVideo(vid, conceptQuery.trim(), maxResults);
      setMatches(res.matches || []);
      if (res.matches && res.matches.length > 0) {
        setCurrentSeconds(res.matches[0].start_seconds);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to pinpoint concept in video.');
      setMatches([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleJump = (seconds: number) => {
    setCurrentSeconds(seconds);
  };

  return (
    <div className="space-y-6">
      {/* Header Form Banner */}
      <div className="rounded-3xl bg-gradient-to-b from-surface to-background border border-border/80 p-6 sm:p-8 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="max-w-3xl">
          <div className="flex items-center space-x-2 text-xs font-mono text-cyan-400 mb-2">
            <Compass className="w-4 h-4" />
            <span>HYBRID RRF IN-VIDEO RETRIEVAL</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mb-2">
            Pinpoint Concept Navigator
          </h2>
          <p className="text-sm text-gray-400 mb-6">
            Paste any long lecture or podcast URL and query. Uses in-process FastEmbed + BM25s RRF retrieval to jump straight to the spoken timestamp.
          </p>

          <form onSubmit={handleSearch} className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-2">
              <div className="md:col-span-6 flex items-center rounded-xl bg-surface-raised border border-border px-3 py-2">
                <input
                  type="text"
                  value={videoUrl}
                  onChange={(e) => setVideoUrl(e.target.value)}
                  placeholder="YouTube Video URL or 11-char ID..."
                  className="w-full text-xs sm:text-sm bg-transparent text-white focus:outline-none placeholder:text-gray-500 font-mono"
                />
              </div>

              <div className="md:col-span-4 flex items-center rounded-xl bg-surface-raised border border-border px-3 py-2">
                <input
                  type="text"
                  value={conceptQuery}
                  onChange={(e) => setConceptQuery(e.target.value)}
                  placeholder="Concept or question to pinpoint..."
                  className="w-full text-xs sm:text-sm bg-transparent text-white focus:outline-none placeholder:text-gray-500"
                />
              </div>

              <div className="md:col-span-2">
                <button
                  type="submit"
                  disabled={isLoading || !videoUrl || !conceptQuery}
                  className="w-full h-full min-h-[40px] flex items-center justify-center space-x-1.5 px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-xs font-semibold transition glow-cyan"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Search className="w-4 h-4" />
                      <span>Find</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Main Dual-Column Player + Timestamp Heatmap */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Embedded Player (7 Cols) */}
        <div className="lg:col-span-7 space-y-4 sticky top-20">
          <div className="p-4 rounded-2xl bg-surface border border-border shadow-xl">
            <YouTubePlayer
              videoId={activeVideoId}
              startSeconds={currentSeconds}
              autoPlay={true}
            />
          </div>
        </div>

        {/* Right Column: Ranked Semantic Matches (5 Cols) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between px-1">
            <h3 className="text-xs font-mono font-semibold text-gray-400 uppercase tracking-wider flex items-center space-x-1.5">
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              <span>Matching Spoken Sections ({matches.length})</span>
            </h3>
          </div>

          {isLoading ? (
            <div className="p-8 text-center space-y-2 rounded-2xl bg-surface border border-border animate-pulse">
              <Loader2 className="w-6 h-6 text-cyan-400 animate-spin mx-auto" />
              <p className="text-xs text-gray-400">Embedding chunks and ranking with BM25s RRF...</p>
            </div>
          ) : matches.length === 0 ? (
            <div className="p-8 text-center rounded-2xl bg-surface border border-border text-gray-500 text-xs">
              Enter video URL and search for any topic or question.
            </div>
          ) : (
            <div className="space-y-2.5">
              {matches.map((m, idx) => {
                const matchPct = Math.round(m.relevance_score * 100);
                const isActive = Math.abs(currentSeconds - m.start_seconds) < 2;

                return (
                  <div
                    key={idx}
                    onClick={() => handleJump(m.start_seconds)}
                    className={`cursor-pointer rounded-xl p-4 transition-all duration-200 border ${
                      isActive
                        ? 'bg-cyan-950/40 border-cyan-500/80 shadow-lg glow-cyan'
                        : 'bg-surface-raised/70 hover:bg-surface-raised border-border/80 hover:border-cyan-500/40'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <button className="flex items-center space-x-1.5 px-2.5 py-0.5 rounded-md bg-cyan-500/20 text-cyan-300 font-mono text-xs font-semibold">
                        <Play className="w-3 h-3 fill-current" />
                        <span>{m.time_range}</span>
                      </button>

                      <span
                        className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded-md ${
                          matchPct >= 80
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                        }`}
                      >
                        {matchPct}% Match
                      </span>
                    </div>

                    {m.chapter_title && (
                      <div className="flex items-center space-x-1 text-[11px] text-gray-400 mb-2 font-medium">
                        <Tag className="w-3 h-3 text-cyan-400" />
                        <span>Chapter: {m.chapter_title}</span>
                      </div>
                    )}

                    <p className="text-xs text-gray-300 line-clamp-3 leading-relaxed italic">
                      "{m.text}"
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
