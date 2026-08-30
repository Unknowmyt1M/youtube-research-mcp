import { Sparkles, ExternalLink } from 'lucide-react';

interface FooterProps {
  onNavigatePage: (pageId: string) => void;
}

export function Footer({ onNavigatePage }: FooterProps) {
  return (
    <footer className="border-t border-border bg-surface text-gray-400 text-xs mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 sm:gap-8 mb-10">
          {/* Brand Col */}
          <div className="space-y-3 md:col-span-1">
            <div className="flex items-center space-x-2">
              <div className="w-6 h-6 rounded-lg bg-surface border border-border flex items-center justify-center p-0.5">
                <img
                  src="/nexora-monochrome.png"
                  alt="Nexora Monochrome Logo"
                  className="w-full h-full object-contain"
                />
              </div>
              <span className="font-bold text-white tracking-tight font-sans text-sm">
                NEXORA
              </span>
            </div>
            <p className="text-gray-400 text-xs leading-relaxed">
              AI-powered video intelligence platform for AI agents, reasoning models, and developers.
            </p>
            <div className="text-[11px] font-mono text-primary-400">
              Understand Everything. Instantly.
            </div>
          </div>

          {/* Docs Col */}
          <div>
            <h4 className="font-semibold text-gray-200 font-mono text-[11px] uppercase tracking-wider mb-3">
              Documentation
            </h4>
            <ul className="space-y-2">
              <li>
                <button
                  onClick={() => onNavigatePage('what-is-nexora')}
                  className="hover:text-white transition-colors"
                >
                  What is Nexora?
                </button>
              </li>
              <li>
                <button
                  onClick={() => onNavigatePage('quickstart')}
                  className="hover:text-white transition-colors"
                >
                  Quick Start Guide
                </button>
              </li>
              <li>
                <button
                  onClick={() => onNavigatePage('core-concepts')}
                  className="hover:text-white transition-colors"
                >
                  Core Concepts & RRF
                </button>
              </li>
              <li>
                <button
                  onClick={() => onNavigatePage('architecture-overview')}
                  className="hover:text-white transition-colors"
                >
                  Architecture Overview
                </button>
              </li>
            </ul>
          </div>

          {/* MCP Tools Col */}
          <div>
            <h4 className="font-semibold text-gray-200 font-mono text-[11px] uppercase tracking-wider mb-3">
              MCP Tools
            </h4>
            <ul className="space-y-2 font-mono text-[11px]">
              <li>
                <button
                  onClick={() => onNavigatePage('tool-youtube-search')}
                  className="hover:text-cyan-400 transition-colors"
                >
                  youtube_search
                </button>
              </li>
              <li>
                <button
                  onClick={() => onNavigatePage('tool-youtube-video')}
                  className="hover:text-cyan-400 transition-colors"
                >
                  youtube_video
                </button>
              </li>
              <li>
                <button
                  onClick={() => onNavigatePage('tool-youtube-transcript')}
                  className="hover:text-cyan-400 transition-colors"
                >
                  youtube_transcript
                </button>
              </li>
              <li>
                <button
                  onClick={() => onNavigatePage('tool-youtube-find-in-video')}
                  className="hover:text-cyan-400 transition-colors"
                >
                  youtube_find_in_video
                </button>
              </li>
              <li>
                <button
                  onClick={() => onNavigatePage('tool-youtube-research')}
                  className="hover:text-cyan-400 transition-colors"
                >
                  youtube_research
                </button>
              </li>
            </ul>
          </div>

          {/* Protocols & Deploy */}
          <div>
            <h4 className="font-semibold text-gray-200 font-mono text-[11px] uppercase tracking-wider mb-3">
              Deployment & Specs
            </h4>
            <ul className="space-y-2">
              <li>
                <button
                  onClick={() => onNavigatePage('api-overview')}
                  className="hover:text-white transition-colors"
                >
                  REST & OpenAPI 3.1.0
                </button>
              </li>
              <li>
                <button
                  onClick={() => onNavigatePage('hosting-docker')}
                  className="hover:text-white transition-colors"
                >
                  Docker Deployment
                </button>
              </li>
              <li>
                <button
                  onClick={() => onNavigatePage('hosting-railway')}
                  className="hover:text-white transition-colors"
                >
                  Railway Production Deploy
                </button>
              </li>
              <li>
                <a
                  href="https://github.com/Unknowmyt1M/youtube-research-mcp"
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center space-x-1 hover:text-white transition-colors"
                >
                  <span>GitHub Repository</span>
                  <ExternalLink className="w-3 h-3 text-gray-500" />
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="pt-8 border-t border-border/80 flex flex-col sm:flex-row items-center justify-between gap-4 font-mono text-[11px] text-gray-500">
          <div>
            © 2026 Nexora Platform • Built with FastMCP 2.0 & BM25s Hybrid Retrieval.
          </div>
          <div className="flex items-center space-x-4">
            <span className="flex items-center space-x-1 text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>MCP Protocol 2024-11-05</span>
            </span>
            <span>MIT License</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
