import { Search, Menu, Sparkles } from 'lucide-react';

interface NavbarProps {
  currentView: 'docs' | 'explorer';
  setCurrentView: (view: 'docs' | 'explorer') => void;
  onOpenSearch: () => void;
  onToggleMobileSidebar: () => void;
  onNavigatePage: (pageId: string) => void;
}

export function Navbar({
  currentView,
  setCurrentView,
  onOpenSearch,
  onToggleMobileSidebar,
  onNavigatePage,
}: NavbarProps) {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-border/80 bg-background/85 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-2">
        {/* Left: Mobile hamburger + Brand logo */}
        <div className="flex items-center space-x-2 sm:space-x-3 shrink-0">
          <button
            onClick={onToggleMobileSidebar}
            className="lg:hidden p-2 -ml-1.5 rounded-xl text-gray-400 hover:text-white hover:bg-surface transition-colors active:scale-95 cursor-pointer"
            title="Toggle Menu"
            aria-label="Toggle navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div
            onClick={() => {
              setCurrentView('docs');
              onNavigatePage('what-is-nexora');
            }}
            className="flex items-center space-x-2.5 cursor-pointer group select-none"
          >
            {/* Mobile Icon Mark (Colorful Gradient origami N as requested) */}
            <div className="sm:hidden w-8 h-8 rounded-xl bg-surface border border-border/80 flex items-center justify-center p-1 shadow-glow-primary group-hover:border-primary-500/50 transition-all">
              <img
                src="/nexora-icon-mark.png"
                alt="Nexora Icon Mark"
                className="w-full h-full object-contain"
              />
            </div>

            {/* Desktop Monochrome Icon Mark */}
            <div className="hidden sm:flex w-8 h-8 rounded-xl bg-surface border border-border/80 items-center justify-center p-1 shadow-sm group-hover:border-primary-500/50 transition-all">
              <img
                src="/nexora-monochrome.png"
                alt="Nexora Monochrome Logo"
                className="w-full h-full object-contain filter brightness-100"
              />
            </div>

            <div className="flex flex-col">
              <div className="flex items-center space-x-1.5">
                <span className="font-bold text-base sm:text-lg text-white font-sans tracking-tight group-hover:text-primary-300 transition-colors">
                  NEXORA
                </span>
                <span className="hidden sm:inline-block text-[10px] font-mono font-semibold px-1.5 py-0.2 rounded bg-primary-500/20 text-primary-300 border border-primary-500/30 uppercase">
                  MCP v2.0
                </span>
              </div>
              <span className="text-[10px] text-gray-400 font-mono hidden md:block">
                Understand Everything. Instantly.
              </span>
            </div>
          </div>
        </div>

        {/* Center: Search trigger & Nav items */}
        <div className="flex items-center space-x-2 sm:space-x-4">
          <button
            onClick={onOpenSearch}
            className="flex items-center space-x-2 sm:space-x-3 px-2.5 sm:px-3.5 py-1.5 rounded-xl bg-surface hover:bg-surface-raised border border-border text-gray-400 hover:text-gray-200 transition-all text-xs font-sans group cursor-pointer"
            aria-label="Search documentation"
          >
            <Search className="w-3.5 h-3.5 text-gray-500 group-hover:text-primary-400 transition-colors" />
            <span className="hidden md:inline">Search docs, tools, API...</span>
            <span className="md:hidden text-xs">Search...</span>
            <kbd className="hidden sm:inline-block px-1.5 py-0.5 rounded bg-surface-raised border border-border text-[10px] text-gray-400 font-mono">
              ⌘K
            </kbd>
          </button>

          <nav className="hidden md:flex items-center space-x-1 text-xs font-medium">
            <button
              onClick={() => {
                setCurrentView('docs');
                onNavigatePage('what-is-nexora');
              }}
              className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer ${
                currentView === 'docs'
                  ? 'text-white bg-surface border border-border'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-surface/50'
              }`}
            >
              Docs
            </button>

            <button
              onClick={() => {
                setCurrentView('docs');
                onNavigatePage('tool-youtube-find-in-video');
              }}
              className="px-3 py-1.5 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-surface/50 transition-colors cursor-pointer"
            >
              MCP Tools
            </button>

            <button
              onClick={() => {
                setCurrentView('docs');
                onNavigatePage('api-overview');
              }}
              className="px-3 py-1.5 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-surface/50 transition-colors cursor-pointer"
            >
              REST API
            </button>

            <button
              onClick={() => setCurrentView('explorer')}
              className={`px-3 py-1.5 rounded-lg transition-colors flex items-center space-x-1.5 cursor-pointer ${
                currentView === 'explorer'
                  ? 'text-cyan-300 bg-cyan-950/30 border border-cyan-500/40 shadow-glow-cyan'
                  : 'text-cyan-400 hover:text-cyan-300 hover:bg-surface/50'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Live Explorer</span>
            </button>
          </nav>
        </div>

        {/* Right: Mobile Explorer button + Horizontal Lockup + Live Status + GitHub */}
        <div className="flex items-center space-x-2 sm:space-x-3 shrink-0">
          {/* Mobile Explorer quick toggle */}
          <button
            onClick={() => setCurrentView(currentView === 'explorer' ? 'docs' : 'explorer')}
            className={`md:hidden p-2 rounded-xl border transition-colors cursor-pointer ${
              currentView === 'explorer'
                ? 'bg-cyan-950/40 border-cyan-500/40 text-cyan-300'
                : 'bg-surface border-border text-gray-400 hover:text-white'
            }`}
            title="Toggle Live Explorer"
            aria-label="Toggle Live Explorer"
          >
            <Sparkles className="w-4 h-4 text-cyan-400" />
          </button>

          {/* Horizontal Lockup Logo (Desktop only) */}
          <div className="hidden xl:flex items-center px-2.5 py-1 rounded-xl bg-surface border border-border/80 hover:border-primary-500/40 transition-colors shadow-sm">
            <img
              src="/nexora-horizontal-lockup.png"
              alt="Nexora Horizontal Lockup"
              className="h-4 w-auto object-contain opacity-90 hover:opacity-100 transition-opacity"
            />
          </div>

          {/* Live Cloud Status (Tablet & Desktop) */}
          <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-emerald-950/40 border border-emerald-500/30 text-[11px] font-mono text-emerald-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="hidden md:inline">Live on Railway</span>
            <span className="md:hidden">Live</span>
          </div>

          {/* GitHub Repository */}
          <a
            href="https://github.com/Unknowmyt1M/youtube-research-mcp"
            target="_blank"
            rel="noreferrer"
            className="p-2 rounded-xl bg-surface hover:bg-surface-raised border border-border text-gray-300 hover:text-white transition-colors"
            title="GitHub Repository"
            aria-label="GitHub Repository"
          >
            <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
              <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
            </svg>
          </a>
        </div>
      </div>
    </header>
  );
}
