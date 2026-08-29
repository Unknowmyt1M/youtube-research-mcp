import React, { useState } from 'react';
import { Search, Loader2, Eye, Clock, Calendar, Film, FileText, ChevronRight, Play } from 'lucide-react';
import { api } from '../api/client';
import { SearchResponse, TranscriptResult, VideoOverview, VideoSearchResult } from '../types';
import { YouTubePlayer } from '../components/YouTubePlayer';

export const SearchExplorer: React.FC = () => {
  const [query, setQuery] = useState('quantum computing error correction');
  const [maxResults, setMaxResults] = useState(8);
  const [publishedAfter, setPublishedAfter] = useState('');
  const [publishedBefore, setPublishedBefore] = useState('');
  const [language, setLanguage] = useState('en');
  const [isLoading, setIsLoading] = useState(false);
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [selectedVideo, setSelectedVideo] = useState<VideoOverview | null>(null);
  const [selectedTranscript, setSelectedTranscript] = useState<TranscriptResult | null>(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [activePlayer, setActivePlayer] = useState<{ videoId: string; seconds: number } | null>(null);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    try {
      const res = await api.searchVideos(
        query.trim(),
        maxResults,
        language,
        publishedAfter || undefined,
        publishedBefore || undefined
      );
      setSearchResponse(res);
      if (res.results.length > 0) {
        handleInspectVideo(res.results[0].video_id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleInspectVideo = async (videoId: string) => {
    setIsLoadingDetails(true);
    setActivePlayer({ videoId, seconds: 0 });
    try {
      const [overview, transcript] = await Promise.allSettled([
        api.getVideo(videoId),
        api.getTranscript(videoId, 'en', 'en', true),
      ]);

      if (overview.status === 'fulfilled') {
        setSelectedVideo(overview.value);
      }
      if (transcript.status === 'fulfilled') {
        setSelectedTranscript(transcript.value);
      } else {
        setSelectedTranscript(null);
      }
    } finally {
      setIsLoadingDetails(false);
    }
  };

  const handleSeek = (seconds: number) => {
    if (activePlayer) {
      setActivePlayer({ ...activePlayer, seconds });
    }
  };

  return (
    <div className="space-y-6">
      {/* Search Bar & Filters */}
      <div className="p-6 rounded-3xl bg-surface border border-border space-y-4">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3.5" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search YouTube videos without API keys..."
              className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-surface-raised border border-border text-white text-sm focus:outline-none focus:border-red-500 font-medium"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-sm font-semibold transition shrink-0 glow-red"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            <span>Search</span>
          </button>
        </form>

        {/* Date Post-Filters */}
        <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-gray-400 pt-1">
          <div className="flex items-center space-x-2">
            <span>Published After:</span>
            <input
              type="date"
              value={publishedAfter}
              onChange={(e) => setPublishedAfter(e.target.value)}
              className="px-2 py-1 rounded-lg bg-surface-raised border border-border text-white text-xs focus:outline-none"
            />
          </div>
          <div className="flex items-center space-x-2">
            <span>Published Before:</span>
            <input
              type="date"
              value={publishedBefore}
              onChange={(e) => setPublishedBefore(e.target.value)}
              className="px-2 py-1 rounded-lg bg-surface-raised border border-border text-white text-xs focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Main Grid: Results & Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Search Results List (5 Cols) */}
        <div className="lg:col-span-5 space-y-3">
          <h3 className="text-xs font-mono font-semibold text-gray-400 uppercase tracking-wider px-1">
            Search Results ({searchResponse?.results.length || 0})
          </h3>

          {isLoading ? (
            <div className="p-8 text-center space-y-2 rounded-2xl bg-surface border border-border animate-pulse">
              <Loader2 className="w-6 h-6 text-red-500 animate-spin mx-auto" />
              <p className="text-xs text-gray-400">Searching YouTube InnerTube & yt-dlp...</p>
            </div>
          ) : !searchResponse || searchResponse.results.length === 0 ? (
            <div className="p-8 text-center rounded-2xl bg-surface border border-border text-gray-500 text-xs">
              Search for videos to inspect chapters and transcripts.
            </div>
          ) : (
            <div className="space-y-2">
              {searchResponse.results.map((r) => {
                const isSelected = activePlayer?.videoId === r.video_id;
                return (
                  <div
                    key={r.video_id}
                    onClick={() => handleInspectVideo(r.video_id)}
                    className={`cursor-pointer rounded-xl p-3 border transition-all ${
                      isSelected
                        ? 'bg-surface-raised border-red-500 shadow-md'
                        : 'bg-surface hover:bg-surface-raised border-border/80'
                    }`}
                  >
                    <div className="flex gap-3">
                      {r.thumbnail && (
                        <img
                          src={r.thumbnail}
                          alt={r.title}
                          className="w-24 h-14 object-cover rounded-lg shrink-0 bg-background"
                        />
                      )}
                      <div className="min-w-0 flex-1">
                        <h4 className="text-xs font-semibold text-white line-clamp-1 hover:text-red-400">
                          {r.title}
                        </h4>
                        <p className="text-[11px] text-gray-400 line-clamp-1">{r.channel}</p>
                        <div className="flex items-center space-x-2 text-[10px] font-mono text-gray-500 mt-1">
                          <span>{r.duration || 'N/A'}</span>
                          {r.published_time && <span>• {r.published_time}</span>}
                          {r.view_count && <span>• {r.view_count}</span>}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Selected Video Inspector (7 Cols) */}
        <div className="lg:col-span-7 space-y-4 sticky top-20">
          <div className="p-4 rounded-2xl bg-surface border border-border shadow-xl space-y-4">
            <YouTubePlayer
              videoId={activePlayer?.videoId || ''}
              startSeconds={activePlayer?.seconds || 0}
              autoPlay={false}
            />

            {isLoadingDetails ? (
              <div className="p-6 text-center text-xs text-gray-400">
                <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-red-400" />
                Loading chapters and transcripts...
              </div>
            ) : selectedVideo ? (
              <div className="space-y-4">
                <div>
                  <h3 className="text-base font-bold text-white mb-1">{selectedVideo.title}</h3>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-gray-400 font-mono">
                    <span className="px-2 py-0.5 rounded bg-border text-gray-300">{selectedVideo.channel}</span>
                    <span>Duration: {selectedVideo.duration_formatted}</span>
                    {selectedVideo.view_count && <span>• {selectedVideo.view_count.toLocaleString()} Views</span>}
                    <span
                      className={`px-2 py-0.5 rounded-full ${
                        selectedVideo.caption_available
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
                      }`}
                    >
                      {selectedVideo.caption_available ? 'Captions Available' : 'No Captions'}
                    </span>
                  </div>
                </div>

                {/* Chapter Markers */}
                {selectedVideo.chapters.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-border">
                    <h4 className="text-xs font-mono font-semibold text-gray-400 uppercase">
                      Chapters ({selectedVideo.chapters.length})
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 max-h-48 overflow-y-auto pr-1">
                      {selectedVideo.chapters.map((ch, i) => (
                        <button
                          key={i}
                          onClick={() => handleSeek(ch.start_seconds)}
                          className="flex items-center justify-between p-2 rounded-lg bg-surface-raised hover:bg-red-500/10 text-left text-xs text-gray-300 hover:text-white transition font-mono"
                        >
                          <span className="truncate pr-2">{ch.title}</span>
                          <span className="text-red-400 shrink-0">{ch.timestamp_formatted}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Transcript Preview */}
                {selectedTranscript && (
                  <div className="space-y-2 pt-2 border-t border-border">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-mono font-semibold text-gray-400 uppercase">
                        Full Transcript Preview ({selectedTranscript.total_words} words)
                      </h4>
                      <span className="text-[11px] font-mono text-gray-400">
                        Language: {selectedTranscript.actual_language}
                      </span>
                    </div>
                    <div className="p-3 rounded-xl bg-background border border-border text-xs text-gray-300 max-h-56 overflow-y-auto leading-relaxed space-y-2 font-mono">
                      {selectedTranscript.segments.slice(0, 15).map((seg, i) => (
                        <div
                          key={i}
                          onClick={() => handleSeek(seg.start)}
                          className="cursor-pointer hover:text-red-300 transition flex gap-2"
                        >
                          <span className="text-red-400 shrink-0">[{seg.timestamp_formatted}]</span>
                          <span>{seg.text}</span>
                        </div>
                      ))}
                      {selectedTranscript.segments.length > 15 && (
                        <p className="text-gray-500 italic pt-2">
                          ... and {selectedTranscript.segments.length - 15} more dialogue segments.
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
};
