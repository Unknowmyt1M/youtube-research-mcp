import React, { useEffect, useRef } from 'react';
import { ExternalLink, Play } from 'lucide-react';

interface YouTubePlayerProps {
  videoId: string;
  startSeconds?: number;
  autoPlay?: boolean;
}

export const YouTubePlayer: React.FC<YouTubePlayerProps> = ({
  videoId,
  startSeconds = 0,
  autoPlay = false,
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    // When startSeconds changes, reload iframe with start parameter
    if (iframeRef.current && videoId) {
      const src = `https://www.youtube-nocookie.com/embed/${videoId}?start=${Math.floor(
        startSeconds
      )}&autoplay=${autoPlay ? 1 : 0}&enablejsapi=1&rel=0`;
      iframeRef.current.src = src;
    }
  }, [videoId, startSeconds, autoPlay]);

  if (!videoId) {
    return (
      <div className="aspect-video w-full rounded-2xl bg-surface-raised border border-border flex flex-col items-center justify-center p-6 text-center text-gray-500">
        <Play className="w-12 h-12 stroke-[1.5] mb-2 opacity-40 text-red-500" />
        <p className="text-sm font-medium">Select a video or timestamp quote</p>
        <p className="text-xs text-gray-600">The interactive player will load here</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col space-y-2">
      <div className="relative aspect-video w-full rounded-2xl overflow-hidden bg-black border border-border/80 shadow-2xl">
        <iframe
          ref={iframeRef}
          src={`https://www.youtube-nocookie.com/embed/${videoId}?start=${Math.floor(
            startSeconds
          )}&autoplay=${autoPlay ? 1 : 0}&enablejsapi=1&rel=0`}
          title="YouTube Video Player"
          className="w-full h-full border-0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
      <div className="flex items-center justify-between text-xs text-gray-400 px-1 font-mono">
        <span>Video ID: {videoId}</span>
        <a
          href={`https://www.youtube.com/watch?v=${videoId}&t=${Math.floor(startSeconds)}s`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center space-x-1 text-red-400 hover:text-red-300 transition"
        >
          <span>Open on YouTube ({Math.floor(startSeconds)}s)</span>
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
};
