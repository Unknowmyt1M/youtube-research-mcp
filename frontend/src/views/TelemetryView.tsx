import React, { useEffect, useState } from 'react';
import { Activity, ShieldCheck, Zap, Database, Server, RefreshCw, Cpu } from 'lucide-react';
import { api } from '../api/client';

export const TelemetryView: React.FC = () => {
  const [serverInfo, setServerInfo] = useState<{ status: string; version: string; name: string } | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
  const [isLoading, setIsLoading] = useState(false);

  const fetchHealth = async () => {
    setIsLoading(true);
    try {
      const res = await api.checkHealth();
      setServerInfo(res);
      setLastRefreshed(new Date());
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-6 rounded-3xl bg-surface border border-border">
        <div>
          <div className="flex items-center space-x-2 text-xs font-mono text-emerald-400 mb-1">
            <Activity className="w-4 h-4" />
            <span>REAL-TIME MCP OBSERVABILITY</span>
          </div>
          <h2 className="text-2xl font-bold text-white">System Telemetry & Health</h2>
          <p className="text-xs text-gray-400 font-mono mt-1">
            Last checked: {lastRefreshed.toLocaleTimeString()}
          </p>
        </div>

        <button
          onClick={fetchHealth}
          disabled={isLoading}
          className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-surface-raised hover:bg-border text-xs font-mono text-gray-300 hover:text-white border border-border transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Metrics</span>
        </button>
      </div>

      {/* Top Stat Gauges */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Server State */}
        <div className="p-5 rounded-2xl bg-surface border border-border space-y-2">
          <div className="flex items-center justify-between text-gray-400 text-xs font-mono">
            <span>FastMCP Server</span>
            <Server className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-white flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>{serverInfo?.status ? 'Online' : 'Offline'}</span>
          </div>
          <p className="text-[11px] text-gray-500 font-mono">Streamable HTTP @ Port 8000</p>
        </div>

        {/* Cache Engine */}
        <div className="p-5 rounded-2xl bg-surface border border-border space-y-2">
          <div className="flex items-center justify-between text-gray-400 text-xs font-mono">
            <span>Cache Engine</span>
            <Database className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-xl font-bold text-white font-mono">SQLite WAL v2</div>
          <p className="text-[11px] text-gray-500 font-mono">Negative Caching + Auto-Purge</p>
        </div>

        {/* Single-Flight Coalescer */}
        <div className="p-5 rounded-2xl bg-surface border border-border space-y-2">
          <div className="flex items-center justify-between text-gray-400 text-xs font-mono">
            <span>Stampede Protection</span>
            <Zap className="w-4 h-4 text-yellow-400" />
          </div>
          <div className="text-xl font-bold text-white font-mono">Single-Flight</div>
          <p className="text-[11px] text-gray-500 font-mono">Keyed Async Request Deduplication</p>
        </div>

        {/* Circuit Breaker Machine */}
        <div className="p-5 rounded-2xl bg-surface border border-border space-y-2">
          <div className="flex items-center justify-between text-gray-400 text-xs font-mono">
            <span>Resilience</span>
            <ShieldCheck className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-xl font-bold text-white font-mono">3-Tier Failover</div>
          <p className="text-[11px] text-gray-500 font-mono">Capability-Aware State Machine</p>
        </div>
      </div>

      {/* Provider Capabilities Table */}
      <div className="p-6 rounded-3xl bg-surface border border-border space-y-4">
        <h3 className="text-sm font-mono font-semibold text-white uppercase tracking-wider">
          Provider Capability Architecture & Circuit Breakers
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-border text-gray-400">
                <th className="pb-3 font-semibold">Provider Tier</th>
                <th className="pb-3 font-semibold">Capabilities</th>
                <th className="pb-3 font-semibold">Circuit State</th>
                <th className="pb-3 font-semibold">Anti-Bot Defense</th>
                <th className="pb-3 font-semibold">Connection Pool</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 text-gray-300">
              <tr>
                <td className="py-3.5 font-bold text-white">Tier 1: In-Process yt-dlp</td>
                <td>Transcript, Metadata, Search</td>
                <td><span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">CLOSED (Healthy)</span></td>
                <td>Android / iOS / TV Rotation</td>
                <td>Long-lived Pool (50 conn)</td>
              </tr>
              <tr>
                <td className="py-3.5 font-bold text-white">Tier 2: Direct InnerTube</td>
                <td>Search, Metadata, Timedtext</td>
                <td><span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">CLOSED (Healthy)</span></td>
                <td>Direct Protobuf/JSON Endpoints</td>
                <td>HTTP/2 Shared Client</td>
              </tr>
              <tr>
                <td className="py-3.5 font-bold text-white">Tier 3: Commercial Fallbacks</td>
                <td>Supadata, SearchAPI, YT Data API</td>
                <td><span className="px-2 py-0.5 rounded-full bg-border text-gray-400 font-bold">STANDBY (Isolated)</span></td>
                <td>API Key Quotas</td>
                <td>On-Demand Fallback</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
