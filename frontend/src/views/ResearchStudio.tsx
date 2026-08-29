import React, { useState } from 'react';
import {
  Sparkles,
  Search,
  Loader2,
  Copy,
  Check,
  Film,
  Layers,
  FileText,
  Sliders,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { api } from '../api/client';
import { MultiVideoResearchResult, ResearchDepth } from '../types';
import { EvidenceCard } from '../components/EvidenceCard';
import { ClusterView } from '../components/ClusterView';
import { YouTubePlayer } from '../components/YouTubePlayer';

export const ResearchStudio: React.FC = () => {
  const [query, setQuery] = useState('recent developments in quantum computing');
  const [depth, setDepth] = useState<ResearchDepth>('standard');
  const [maxPerChannel, setMaxPerChannel] = useState(2);
  const [language, setLanguage] = useState('en');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<MultiVideoResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'evidence' | 'clusters' | 'sources'>('evidence');
  const [activePlayer, setActivePlayer] = useState<{ videoId: string; seconds: number } | null>(null);
  const [copiedMd, setCopiedMd] = useState(false);
  const [copiedJson, setCopiedJson] = useState(false);
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    setError(null);
    try {
      const res = await api.researchTopic(
        query.trim(),
        depth,
        maxPerChannel,
        language,
        'en'
      );
      setResult(res);
      if (res.all_citations_ranked.length > 0) {
        setActivePlayer({
          videoId: res.all_citations_ranked[0].video_id,
          seconds: res.all_citations_ranked[0].start_seconds,
        });
      }
    } catch (err: any) {
      setError(err.message || 'Failed to perform multi-video research.');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePlayTimestamp = (videoId: string, seconds: number) => {
    setActivePlayer({ videoId, seconds });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const toggleSourceExpand = (id: string) => {
    setExpandedSources((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // Export as Markdown for Obsidian / Notes
  const copyObsidianMarkdown = () => {
    if (!result) return;
    let md = `# YouTube Research: ${result.topic}\n\n`;
    md += `> [!INFO] Research Overview\n`;
    md += `> - **Depth**: ${result.depth} (${result.total_videos_analyzed} videos analyzed)\n`;
    md += `> - **Transcripts Extracted**: ${result.videos_with_transcripts}\n`;
    md += `> - **Total Spoken Quotes**: ${result.total_evidence_chunks}\n\n`;

    if (result.evidence_clusters.length > 0) {
      md += `## 🧠 Key Consensus Clusters\n\n`;
      result.evidence_clusters.forEach((cl) => {
        md += `### ${cl.topic_headline}\n`;
        md += `*Consensus: ${Math.round(cl.consensus_score * 100)}% across ${cl.independent_sources_count} sources (${cl.channels.join(', ')})*\n\n`;
        cl.citations.forEach((c) => {
          md += `> [!QUOTE] **${c.channel}** - *${c.video_title}*\n`;
          md += `> "${c.quote}"\n`;
          md += `> 👉 [Watch at ${c.time_range}](${c.url_with_timestamp})\n\n`;
        });
      });
    }

    md += `## 📑 Key Timestamped Citations\n\n`;
    result.all_citations_ranked.forEach((c, idx) => {
      md += `${idx + 1}. **${c.video_title}** (${c.channel}) — [${c.time_range}](${c.url_with_timestamp})\n`;
      md += `   > "${c.quote}"\n\n`;
    });

    navigator.clipboard.writeText(md);
    setCopiedMd(true);
    setTimeout(() => setCopiedMd(false), 2500);
  };

  const copyJsonEvidence = () => {
    if (!result) return;
    navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2500);
  };

  return (
    <div className="space-y-6">
      {/* Search Header Banner */}
      <div className="rounded-3xl bg-gradient-to-b from-surface to-background border border-border/80 p-6 sm:p-8 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-red-600/10 rounded-full blur-3xl pointer-events-none" />

        <div className="max-w-3xl">
          <div className="flex items-center space-x-2 text-xs font-mono text-red-400 mb-2">
            <Sparkles className="w-4 h-4" />
            <span>AUTONOMOUS MULTI-VIDEO SYNTHESIS</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mb-3">
            Deep Research Studio
          </h2>
          <p className="text-sm text-gray-400 mb-6">
            Discovers candidate YouTube videos across diverse channels, pulls full spoken transcripts concurrently,
            and pinpoints corroborated evidence claims with clickable timecodes.
          </p>

          {/* Search Form */}
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="flex items-center rounded-2xl bg-surface-raised border border-border focus-within:border-red-500 shadow-xl overflow-hidden p-1.5 transition">
              <Search className="w-5 h-5 text-gray-400 ml-3 shrink-0" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter research topic, question, or technology..."
                className="w-full px-3 py-2 text-sm sm:text-base bg-transparent text-white focus:outline-none placeholder:text-gray-500"
              />
              <button
                type="submit"
                disabled={isLoading || !query.trim()}
                className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white font-medium text-sm transition shadow-md glow-red shrink-0"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Researching...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Run Deep Research</span>
                  </>
                )}
              </button>
            </div>

            {/* Config Controls */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-1 text-xs">
              {/* Depth Selector */}
              <div className="flex items-center space-x-2">
                <span className="text-gray-400 font-mono">Depth:</span>
                <div className="flex items-center space-x-1 p-1 rounded-xl bg-surface-raised border border-border font-mono">
                  {(['quick', 'standard', 'deep'] as ResearchDepth[]).map((d) => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => setDepth(d)}
                      className={`px-3 py-1 rounded-lg capitalize transition ${
                        depth === d
                          ? 'bg-red-600 text-white font-semibold shadow-sm'
                          : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      {d === 'quick' ? '⚡ Quick (2)' : d === 'standard' ? '🎯 Standard (3)' : '🔬 Deep (5)'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Channel Diversity Limit */}
              <div className="flex items-center space-x-2">
                <span className="text-gray-400 font-mono">Max / Channel:</span>
                <select
                  value={maxPerChannel}
                  onChange={(e) => setMaxPerChannel(Number(e.target.value))}
                  className="px-2.5 py-1 rounded-lg bg-surface-raised border border-border text-white text-xs font-mono focus:outline-none"
                >
                  <option value={1}>1 video (Max Diversity)</option>
                  <option value={2}>2 videos (Balanced)</option>
                  <option value={3}>3 videos</option>
                </select>
              </div>
            </div>
          </form>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="p-12 text-center space-y-4 rounded-3xl bg-surface border border-border animate-pulse">
          <Loader2 className="w-10 h-10 text-red-500 animate-spin mx-auto" />
          <h3 className="text-lg font-bold text-white">Analyzing YouTube Knowledge Graph...</h3>
          <p className="text-xs text-gray-400 max-w-md mx-auto">
            Searching candidate videos across creators, extracting timed dialogue tracks, computing hybrid RRF embeddings,
            and clustering corroborating claims.
          </p>
        </div>
      )}

      {/* Research Results Canvas */}
      {result && !isLoading && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Video Player & Source Details (5 Cols) */}
          <div className="lg:col-span-5 space-y-6 sticky top-20">
            {/* Embedded Player */}
            <div className="p-4 rounded-2xl bg-surface border border-border shadow-xl">
              <h3 className="text-xs font-mono font-semibold text-gray-400 uppercase tracking-wider mb-3">
                Live Evidence Video Player
              </h3>
              <YouTubePlayer
                videoId={activePlayer?.videoId || ''}
                startSeconds={activePlayer?.seconds || 0}
                autoPlay={true}
              />
            </div>

            {/* Sources Breakdown Accordion */}
            <div className="p-4 rounded-2xl bg-surface border border-border space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-mono font-semibold text-gray-400 uppercase tracking-wider flex items-center space-x-1.5">
                  <Film className="w-3.5 h-3.5 text-red-400" />
                  <span>Analyzed Sources ({result.sources.length})</span>
                </h3>
                <span className="text-[11px] font-mono text-emerald-400">
                  {result.videos_with_transcripts}/{result.total_videos_analyzed} Transcripts
                </span>
              </div>

              <div className="space-y-2">
                {result.sources.map((src) => (
                  <div
                    key={src.video_id}
                    className="rounded-xl bg-surface-raised border border-border p-3 text-xs space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <a
                          href={src.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-semibold text-gray-200 hover:text-red-400 line-clamp-1"
                        >
                          {src.title}
                        </a>
                        <p className="text-[11px] text-gray-400">{src.channel} • {src.duration || 'N/A'}</p>
                      </div>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-mono shrink-0 ${
                          src.caption_found
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
                        }`}
                      >
                        {src.caption_found ? 'Captioned' : 'No Captions'}
                      </span>
                    </div>

                    {src.key_citations.length > 0 && (
                      <div>
                        <button
                          onClick={() => toggleSourceExpand(src.video_id)}
                          className="flex items-center space-x-1 text-[11px] text-red-400 hover:text-red-300 font-mono"
                        >
                          <span>{src.key_citations.length} Citations</span>
                          {expandedSources[src.video_id] ? (
                            <ChevronUp className="w-3 h-3" />
                          ) : (
                            <ChevronDown className="w-3 h-3" />
                          )}
                        </button>

                        {expandedSources[src.video_id] && (
                          <div className="mt-2 space-y-1.5 pl-2 border-l border-border">
                            {src.key_citations.map((c, idx) => (
                              <button
                                key={idx}
                                onClick={() => handlePlayTimestamp(c.video_id, c.start_seconds)}
                                className="w-full text-left p-1.5 rounded bg-background hover:bg-red-500/10 text-gray-300 hover:text-white transition font-mono text-[10px] flex justify-between"
                              >
                                <span className="truncate pr-2">"{c.quote.slice(0, 50)}..."</span>
                                <span className="text-red-400 shrink-0">@{c.time_range}</span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Evidence, Clusters, and Export Controls (7 Cols) */}
          <div className="lg:col-span-7 space-y-4">
            {/* Action Bar & Tabs */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-2xl bg-surface border border-border">
              {/* Tab Navigation */}
              <div className="flex items-center space-x-1 p-1 rounded-xl bg-background border border-border text-xs font-medium">
                <button
                  onClick={() => setActiveTab('evidence')}
                  className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg transition ${
                    activeTab === 'evidence'
                      ? 'bg-surface-raised text-red-400 font-semibold shadow-sm'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>All Quotes ({result.all_citations_ranked.length})</span>
                </button>
                <button
                  onClick={() => setActiveTab('clusters')}
                  className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg transition ${
                    activeTab === 'clusters'
                      ? 'bg-surface-raised text-cyan-400 font-semibold shadow-sm'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  <Layers className="w-3.5 h-3.5" />
                  <span>Consensus Clusters ({result.evidence_clusters.length})</span>
                </button>
              </div>

              {/* Copy & Export Buttons */}
              <div className="flex items-center space-x-2">
                <button
                  onClick={copyObsidianMarkdown}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-surface-raised hover:bg-border text-xs font-mono text-gray-200 hover:text-white border border-border transition"
                  title="Copy formatted markdown with timestamp deep links for Obsidian/Notes"
                >
                  {copiedMd ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedMd ? 'Copied MD!' : 'Copy Markdown'}</span>
                </button>

                <button
                  onClick={copyJsonEvidence}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-surface-raised hover:bg-border text-xs font-mono text-gray-200 hover:text-white border border-border transition"
                  title="Copy raw JSON payload for AI agents"
                >
                  {copiedJson ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedJson ? 'Copied JSON!' : 'Copy JSON'}</span>
                </button>
              </div>
            </div>

            {/* Evidence Quotes List */}
            {activeTab === 'evidence' && (
              <div className="space-y-3">
                {result.all_citations_ranked.length === 0 ? (
                  <div className="p-8 rounded-2xl bg-surface border border-border text-center text-gray-500 text-sm">
                    No matching dialogue quotes found in video transcripts.
                  </div>
                ) : (
                  result.all_citations_ranked.map((cit, idx) => (
                    <EvidenceCard
                      key={idx}
                      citation={cit}
                      onPlayTimestamp={handlePlayTimestamp}
                    />
                  ))
                )}
              </div>
            )}

            {/* Consensus Clusters View */}
            {activeTab === 'clusters' && (
              <ClusterView
                clusters={result.evidence_clusters}
                onPlayTimestamp={handlePlayTimestamp}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};
