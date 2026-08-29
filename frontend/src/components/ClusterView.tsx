import React from 'react';
import { Layers, Users, Sparkles } from 'lucide-react';
import { ClaimEvidenceCluster } from '../types';
import { EvidenceCard } from './EvidenceCard';

interface ClusterViewProps {
  clusters: ClaimEvidenceCluster[];
  onPlayTimestamp?: (videoId: string, seconds: number) => void;
}

export const ClusterView: React.FC<ClusterViewProps> = ({
  clusters,
  onPlayTimestamp,
}) => {
  if (!clusters || clusters.length === 0) {
    return (
      <div className="p-6 rounded-2xl bg-surface-raised border border-border text-center text-gray-500">
        <Layers className="w-8 h-8 mx-auto mb-2 opacity-40 text-cyan-400" />
        <p className="text-sm font-medium">No cross-video consensus clusters found yet</p>
        <p className="text-xs text-gray-600">
          When multiple independent creators discuss the same findings, they will be clustered here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {clusters.map((cluster) => (
        <div
          key={cluster.cluster_id}
          className="rounded-2xl bg-surface border border-cyan-500/30 p-5 shadow-lg relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/5 rounded-full blur-2xl pointer-events-none" />

          {/* Cluster Header */}
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <div className="flex items-center space-x-2">
              <span className="flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-xs font-mono font-semibold">
                <Sparkles className="w-3 h-3" />
                <span>Consensus Cluster</span>
              </span>
              <span className="flex items-center space-x-1 px-2 py-0.5 rounded-md bg-border text-gray-300 text-xs font-mono">
                <Users className="w-3 h-3 text-gray-400" />
                <span>{cluster.independent_sources_count} Independent Sources</span>
              </span>
            </div>

            <div className="text-xs font-mono text-cyan-300">
              Avg Consensus: <span className="font-bold">{Math.round(cluster.consensus_score * 100)}%</span>
            </div>
          </div>

          {/* Topic Headline */}
          <h4 className="text-sm sm:text-base font-semibold text-white mb-2">
            {cluster.topic_headline}
          </h4>

          {/* Contributing Channels */}
          <div className="flex flex-wrap gap-1.5 mb-4">
            <span className="text-xs text-gray-500 self-center">Corroborated by:</span>
            {cluster.channels.map((ch, idx) => (
              <span
                key={idx}
                className="text-[11px] px-2 py-0.5 rounded-md bg-surface-raised border border-border text-gray-300 font-medium"
              >
                {ch}
              </span>
            ))}
          </div>

          {/* Citations List inside Cluster */}
          <div className="space-y-2.5 pt-2 border-t border-border/60">
            {cluster.citations.map((c, i) => (
              <EvidenceCard
                key={i}
                citation={c}
                onPlayTimestamp={onPlayTimestamp}
                isCompact
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};
