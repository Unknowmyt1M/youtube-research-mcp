import React, { useEffect, useState } from 'react';
import {
  ShieldAlert,
  Database,
  Sliders,
  Terminal,
  Activity,
  Trash2,
  RefreshCw,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Play,
  Loader2,
  Code,
} from 'lucide-react';
import { adminApi, AdminConfig, CacheEntry, ProviderHealthReport, AdminMetrics } from '../api/adminClient';

export const AdminDashboard: React.FC = () => {
  const [adminTab, setAdminTab] = useState<'config' | 'cache' | 'circuits' | 'repl' | 'metrics'>('config');
  const [config, setConfig] = useState<AdminConfig | null>(null);
  const [cacheEntries, setCacheEntries] = useState<CacheEntry[]>([]);
  const [reports, setReports] = useState<ProviderHealthReport[]>([]);
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Tool REPL state
  const [selectedTool, setSelectedTool] = useState<string>('youtube_search');
  const [toolPayload, setToolPayload] = useState<string>(
    JSON.stringify({ query: 'quantum computing breakthroughs 2026', max_results: 3 }, null, 2)
  );
  const [replResult, setReplResult] = useState<string | null>(null);
  const [isExecutingRepl, setIsExecutingRepl] = useState(false);
  const [replExecutionTime, setReplExecutionTime] = useState<number | null>(null);

  const fetchAllAdminData = async () => {
    setIsLoading(true);
    try {
      const [cfgRes, cacheRes, circRes, metRes] = await Promise.allSettled([
        adminApi.getConfig(),
        adminApi.getCacheKeys(),
        adminApi.getCircuits(),
        adminApi.getMetrics(),
      ]);

      if (cfgRes.status === 'fulfilled') setConfig(cfgRes.value.config);
      if (cacheRes.status === 'fulfilled') setCacheEntries(cacheRes.value.entries);
      if (circRes.status === 'fulfilled') setReports(circRes.value.reports);
      if (metRes.status === 'fulfilled') setMetrics(metRes.value.metrics);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAllAdminData();
  }, []);

  const handlePurgeCache = async () => {
    try {
      const res = await adminApi.purgeCache();
      setActionMessage(`Purged ${res.purged_count} expired cache entries.`);
      fetchAllAdminData();
      setTimeout(() => setActionMessage(null), 3000);
    } catch (e: any) {
      setActionMessage(`Error: ${e.message}`);
    }
  };

  const handleClearCache = async () => {
    if (!window.confirm('Are you sure you want to flush and wipe ALL cached search, metadata, and transcript entries?')) return;
    try {
      await adminApi.clearCache();
      setActionMessage('Successfully cleared the entire cache database.');
      fetchAllAdminData();
      setTimeout(() => setActionMessage(null), 3000);
    } catch (e: any) {
      setActionMessage(`Error: ${e.message}`);
    }
  };

  const handleResetCircuits = async () => {
    try {
      await adminApi.resetCircuits();
      setActionMessage('All Circuit Breakers have been manually reset to CLOSED (Healthy).');
      fetchAllAdminData();
      setTimeout(() => setActionMessage(null), 3000);
    } catch (e: any) {
      setActionMessage(`Error: ${e.message}`);
    }
  };

  const handleToolSelect = (tool: string) => {
    setSelectedTool(tool);
    if (tool === 'youtube_search') {
      setToolPayload(JSON.stringify({ query: 'quantum computing breakthroughs', max_results: 3 }, null, 2));
    } else if (tool === 'youtube_video') {
      setToolPayload(JSON.stringify({ video_id: 'dQw4w9WgXcQ' }, null, 2));
    } else if (tool === 'youtube_transcript') {
      setToolPayload(JSON.stringify({ video_id: 'dQw4w9WgXcQ', language: 'en' }, null, 2));
    } else if (tool === 'youtube_find_in_video') {
      setToolPayload(JSON.stringify({ video_id: 'dQw4w9WgXcQ', query: 'never gonna give you up', max_results: 3 }, null, 2));
    } else if (tool === 'youtube_research') {
      setToolPayload(JSON.stringify({ query: 'AI agents and tool use', depth: 'quick' }, null, 2));
    }
  };

  const handleExecuteRepl = async () => {
    setIsExecutingRepl(true);
    setReplResult(null);
    const start = performance.now();
    try {
      const parsed = JSON.parse(toolPayload);
      let endpoint = '/api/search';
      if (selectedTool === 'youtube_video') endpoint = '/api/video';
      if (selectedTool === 'youtube_transcript') endpoint = '/api/transcript';
      if (selectedTool === 'youtube_find_in_video') endpoint = '/api/find_in_video';
      if (selectedTool === 'youtube_research') endpoint = '/api/research';

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed),
      });
      const data = await res.json();
      setReplExecutionTime(Math.round(performance.now() - start));
      setReplResult(JSON.stringify(data, null, 2));
    } catch (e: any) {
      setReplExecutionTime(Math.round(performance.now() - start));
      setReplResult(`Execution Error:\n${e.message}`);
    } finally {
      setIsExecutingRepl(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Admin Header Banner */}
      <div className="rounded-3xl bg-gradient-to-r from-red-950/40 via-surface to-background border border-red-500/40 p-6 sm:p-8 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-red-600/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-xs font-mono text-red-400 mb-1">
              <ShieldAlert className="w-4 h-4" />
              <span>FULL CODE & SYSTEM CONTROL CENTER</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              YouTube Research MCP Admin
            </h2>
            <p className="text-xs sm:text-sm text-gray-400 mt-1 font-mono">
              Inspect runtime configurations, cache storage, circuit breaker states, and execute raw tool queries.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={fetchAllAdminData}
              disabled={isLoading}
              className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-surface-raised hover:bg-border text-xs font-mono text-gray-300 hover:text-white border border-border transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh All</span>
            </button>
          </div>
        </div>

        {/* Action Message Banner */}
        {actionMessage && (
          <div className="mt-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-mono flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{actionMessage}</span>
          </div>
        )}
      </div>

      {/* Admin Tab Bar */}
      <div className="flex overflow-x-auto space-x-1 p-1 rounded-2xl bg-surface border border-border text-xs font-mono">
        <button
          onClick={() => setAdminTab('config')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl transition ${
            adminTab === 'config' ? 'bg-red-600 text-white font-bold shadow-md' : 'text-gray-400 hover:text-white'
          }`}
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>Config & Environment</span>
        </button>

        <button
          onClick={() => setAdminTab('cache')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl transition ${
            adminTab === 'cache' ? 'bg-red-600 text-white font-bold shadow-md' : 'text-gray-400 hover:text-white'
          }`}
        >
          <Database className="w-3.5 h-3.5" />
          <span>Cache DB Explorer ({cacheEntries.length})</span>
        </button>

        <button
          onClick={() => setAdminTab('circuits')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl transition ${
            adminTab === 'circuits' ? 'bg-red-600 text-white font-bold shadow-md' : 'text-gray-400 hover:text-white'
          }`}
        >
          <Zap className="w-3.5 h-3.5" />
          <span>Circuit Breakers</span>
        </button>

        <button
          onClick={() => setAdminTab('repl')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl transition ${
            adminTab === 'repl' ? 'bg-red-600 text-white font-bold shadow-md' : 'text-gray-400 hover:text-white'
          }`}
        >
          <Terminal className="w-3.5 h-3.5" />
          <span>Tool REPL / Raw Code</span>
        </button>

        <button
          onClick={() => setAdminTab('metrics')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl transition ${
            adminTab === 'metrics' ? 'bg-red-600 text-white font-bold shadow-md' : 'text-gray-400 hover:text-white'
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Live Metrics</span>
        </button>
      </div>

      {/* 1. Config & Environment Inspector */}
      {adminTab === 'config' && (
        <div className="p-6 rounded-3xl bg-surface border border-border space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-mono font-bold text-white uppercase tracking-wider flex items-center space-x-2">
              <Code className="w-4 h-4 text-red-400" />
              <span>Active Runtime Settings & Parameters</span>
            </h3>
            <span className="text-xs font-mono text-gray-400">Pydantic BaseSettings Model</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {config ? (
              Object.entries(config).map(([key, val]) => (
                <div key={key} className="p-3.5 rounded-xl bg-surface-raised border border-border/80 font-mono space-y-1">
                  <span className="text-[11px] text-gray-400 block truncate" title={key}>
                    {key}
                  </span>
                  <span className="text-xs font-bold text-red-300 block truncate" title={String(val)}>
                    {String(val)}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-gray-500 font-mono">Loading config...</p>
            )}
          </div>
        </div>
      )}

      {/* 2. Cache Database Explorer */}
      {adminTab === 'cache' && (
        <div className="p-6 rounded-3xl bg-surface border border-border space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
                SQLite WAL Cache Store
              </h3>
              <p className="text-xs text-gray-400 font-mono">
                Inspect live stored cache rows, negative tags, remaining TTL, and byte sizes.
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={handlePurgeCache}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-surface-raised hover:bg-border text-xs font-mono text-yellow-400 hover:text-yellow-300 border border-yellow-500/30 transition"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Purge Expired</span>
              </button>

              <button
                onClick={handleClearCache}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-red-600/20 hover:bg-red-600 text-xs font-mono text-red-300 hover:text-white border border-red-500/40 transition"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Flush Entire Cache</span>
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-border text-gray-400">
                  <th className="pb-3 font-semibold">Cache Key</th>
                  <th className="pb-3 font-semibold">Type</th>
                  <th className="pb-3 font-semibold">Remaining TTL</th>
                  <th className="pb-3 font-semibold">Size</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50 text-gray-300">
                {cacheEntries.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-6 text-center text-gray-500">
                      Cache database is currently empty.
                    </td>
                  </tr>
                ) : (
                  cacheEntries.map((entry, idx) => (
                    <tr key={idx} className="hover:bg-surface-raised/40 transition">
                      <td className="py-2.5 max-w-xs sm:max-w-md truncate text-gray-200" title={entry.key}>
                        {entry.key}
                      </td>
                      <td>
                        {entry.is_negative ? (
                          <span className="px-2 py-0.5 rounded-full bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 text-[10px]">
                            Negative (No Captions)
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">
                            Valid Data
                          </span>
                        )}
                      </td>
                      <td>{entry.expires_in_seconds}s</td>
                      <td className="text-gray-400">{(entry.size_bytes / 1024).toFixed(1)} KB</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 3. Circuit Breakers Control Station */}
      {adminTab === 'circuits' && (
        <div className="p-6 rounded-3xl bg-surface border border-border space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
                Capability Circuit Breaker State Machine
              </h3>
              <p className="text-xs text-gray-400 font-mono">
                Individual capabilities break and recover independently to ensure maximum uptime.
              </p>
            </div>

            <button
              onClick={handleResetCircuits}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-emerald-600/20 hover:bg-emerald-600 text-xs font-mono text-emerald-300 hover:text-white border border-emerald-500/40 transition"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Reset All to CLOSED</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {reports.map((r, i) => (
              <div key={i} className="p-5 rounded-2xl bg-surface-raised border border-border space-y-3 font-mono">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-white">{r.provider_name}</h4>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      r.is_healthy
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-red-500/10 text-red-400 border border-red-500/20'
                    }`}
                  >
                    {r.is_healthy ? 'HEALTHY' : 'DEGRADED'}
                  </span>
                </div>

                <div className="space-y-1.5 text-xs text-gray-300">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Total Requests:</span>
                    <span>{r.total_requests}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Success Rate:</span>
                    <span>{(r.success_rate * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Avg Latency:</span>
                    <span>{r.avg_latency_ms.toFixed(1)} ms</span>
                  </div>
                </div>

                {/* Capabilities Breakdown */}
                <div className="pt-2 border-t border-border/80 space-y-1.5">
                  <span className="text-[11px] text-gray-400 uppercase font-semibold block">
                    Capabilities:
                  </span>
                  {Object.entries(r.capabilities).map(([capName, capData]: any) => (
                    <div
                      key={capName}
                      className="flex items-center justify-between text-xs p-1.5 rounded-lg bg-background"
                    >
                      <span className="capitalize text-gray-300">{capName}</span>
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                          capData.state === 'CLOSED'
                            ? 'text-emerald-400 bg-emerald-500/10'
                            : 'text-red-400 bg-red-500/10'
                        }`}
                      >
                        {capData.state}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Tool REPL / Raw Code Executor */}
      {adminTab === 'repl' && (
        <div className="p-6 rounded-3xl bg-surface border border-border space-y-4">
          <div>
            <h3 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
              Interactive Tool REPL & Raw Code Executor
            </h3>
            <p className="text-xs text-gray-400 font-mono">
              Directly invoke MCP tools with arbitrary JSON parameters and benchmark latency.
            </p>
          </div>

          {/* Tool Selector Tabs */}
          <div className="flex flex-wrap gap-1.5 text-xs font-mono">
            {['youtube_search', 'youtube_video', 'youtube_transcript', 'youtube_find_in_video', 'youtube_research'].map(
              (tool) => (
                <button
                  key={tool}
                  onClick={() => handleToolSelect(tool)}
                  className={`px-3 py-1.5 rounded-xl border transition ${
                    selectedTool === tool
                      ? 'bg-red-600 border-red-500 text-white font-bold'
                      : 'bg-surface-raised border-border text-gray-400 hover:text-white'
                  }`}
                >
                  {tool}
                </button>
              )
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Input JSON Box */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-mono text-gray-400">
                <span>Input JSON Payload:</span>
                <button
                  onClick={handleExecuteRepl}
                  disabled={isExecutingRepl}
                  className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-red-600 hover:bg-red-500 text-white font-semibold shadow-md transition"
                >
                  {isExecutingRepl ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                  <span>Execute Tool</span>
                </button>
              </div>
              <textarea
                value={toolPayload}
                onChange={(e) => setToolPayload(e.target.value)}
                rows={12}
                className="w-full p-3.5 rounded-2xl bg-background border border-border text-white text-xs font-mono focus:outline-none focus:border-red-500 leading-relaxed"
              />
            </div>

            {/* Output Result Box */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-mono text-gray-400">
                <span>Execution Result:</span>
                {replExecutionTime !== null && (
                  <span className="text-emerald-400 font-bold">{replExecutionTime} ms</span>
                )}
              </div>
              <pre className="w-full p-3.5 rounded-2xl bg-background border border-border text-xs text-red-200 font-mono overflow-auto h-[290px] leading-relaxed">
                {isExecutingRepl ? (
                  <div className="flex items-center justify-center h-full text-gray-500">
                    <Loader2 className="w-6 h-6 animate-spin mr-2" />
                    Executing {selectedTool}...
                  </div>
                ) : (
                  replResult || '// Execute tool to see raw JSON output...'
                )}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* 5. Live Metrics */}
      {adminTab === 'metrics' && (
        <div className="p-6 rounded-3xl bg-surface border border-border space-y-6">
          <h3 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
            Live Telemetry & Stampede Defense
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Cache Stats */}
            <div className="p-5 rounded-2xl bg-surface-raised border border-border space-y-2 font-mono">
              <span className="text-xs text-gray-400 block">Cache Hit Rate</span>
              <div className="text-3xl font-extrabold text-white">
                {metrics?.cache.hit_rate_pct || 0}%
              </div>
              <div className="text-xs text-gray-400 space-y-1 pt-2 border-t border-border">
                <div className="flex justify-between">
                  <span>Hits:</span>
                  <span className="text-emerald-400">{metrics?.cache.hits || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Misses:</span>
                  <span className="text-red-400">{metrics?.cache.misses || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Negative Hits:</span>
                  <span className="text-yellow-400">{metrics?.cache.negative_hits || 0}</span>
                </div>
              </div>
            </div>

            {/* Single Flight Savings */}
            <div className="p-5 rounded-2xl bg-surface-raised border border-border space-y-2 font-mono">
              <span className="text-xs text-gray-400 block">Single-Flight Stampede Savings</span>
              <div className="text-3xl font-extrabold text-cyan-400">
                {metrics?.single_flight_coalesced_savings || 0}
              </div>
              <p className="text-xs text-gray-400 pt-2 border-t border-border">
                Duplicate concurrent requests coalesced into 1 upstream execution.
              </p>
            </div>

            {/* Tool Request Counts */}
            <div className="p-5 rounded-2xl bg-surface-raised border border-border space-y-2 font-mono">
              <span className="text-xs text-gray-400 block">Tool Request Invocations</span>
              <div className="space-y-1 text-xs pt-1">
                {metrics?.requests &&
                  Object.entries(metrics.requests).map(([tool, count]) => (
                    <div key={tool} className="flex justify-between">
                      <span className="text-gray-400">{tool}:</span>
                      <span className="font-bold text-white">{count}</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
