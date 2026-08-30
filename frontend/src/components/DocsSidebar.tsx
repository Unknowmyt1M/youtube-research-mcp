import { useState } from 'react';
import { 
  Compass, 
  Zap, 
  Wrench, 
  Layers,
  Code2, 
  Server, 
  Cpu,
  HelpCircle, 
  ChevronDown, 
  ChevronRight, 
  ExternalLink,
  Search,
  X
} from 'lucide-react';
import { DOCS_CATEGORIES } from '../docs/docsRegistry';

interface DocsSidebarProps {
  activePageId: string;
  onSelectPage: (pageId: string) => void;
  onOpenSearch: () => void;
  isOpenMobile?: boolean;
  onCloseMobile?: () => void;
}

export function DocsSidebar({ 
  activePageId, 
  onSelectPage, 
  onOpenSearch, 
  isOpenMobile = false,
  onCloseMobile 
}: DocsSidebarProps) {
  // All categories open by default
  const [openCategories, setOpenCategories] = useState<Record<string, boolean>>({
    introduction: true,
    'getting-started': true,
    'mcp-tools': true,
    integrations: true,
    'rest-api': true,
    'self-hosting': true,
    architecture: true,
    resources: true,
  });

  const toggleCategory = (catId: string) => {
    setOpenCategories((prev) => ({
      ...prev,
      [catId]: !(prev[catId] ?? true),
    }));
  };

  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'Compass':
        return <Compass className="w-4 h-4 text-primary-400" />;
      case 'Zap':
        return <Zap className="w-4 h-4 text-yellow-400" />;
      case 'Wrench':
        return <Wrench className="w-4 h-4 text-cyan-400" />;
      case 'Layers':
        return <Layers className="w-4 h-4 text-purple-400" />;
      case 'Code2':
        return <Code2 className="w-4 h-4 text-emerald-400" />;
      case 'Server':
        return <Server className="w-4 h-4 text-indigo-400" />;
      case 'Cpu':
        return <Cpu className="w-4 h-4 text-cyan-400" />;
      case 'HelpCircle':
        return <HelpCircle className="w-4 h-4 text-rose-400" />;
      default:
        return <Compass className="w-4 h-4 text-gray-400" />;
    }
  };

  const content = (
    <div className="flex flex-col h-full bg-surface border-r border-border">
      {/* Mobile Drawer Top Bar with Icon Mark */}
      <div className="lg:hidden p-4 border-b border-border/80 flex items-center justify-between bg-surface-raised">
        <div className="flex items-center space-x-2">
          <div className="w-7 h-7 rounded-lg bg-surface border border-border flex items-center justify-center p-0.5 shadow-glow-primary">
            <img
              src="/nexora-icon-mark.png"
              alt="Nexora Icon Mark"
              className="w-full h-full object-contain"
            />
          </div>
          <div>
            <div className="font-bold text-sm text-white font-sans">NEXORA</div>
            <div className="text-[10px] text-gray-400 font-mono">Documentation</div>
          </div>
        </div>
        <button
          onClick={onCloseMobile}
          className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-surface transition-colors active:scale-95 cursor-pointer"
          title="Close Navigation"
          aria-label="Close navigation drawer"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Quick Search trigger in sidebar */}
      <div className="p-3.5 sm:p-4 border-b border-border/80">
        <button
          onClick={onOpenSearch}
          className="w-full flex items-center justify-between px-3 py-2 rounded-xl bg-surface-raised hover:bg-surface-hover border border-border text-gray-400 hover:text-gray-200 transition-all text-xs font-sans group cursor-pointer"
        >
          <div className="flex items-center space-x-2">
            <Search className="w-3.5 h-3.5 text-gray-500 group-hover:text-primary-400 transition-colors" />
            <span>Search documentation...</span>
          </div>
          <kbd className="px-1.5 py-0.5 rounded bg-surface border border-border text-[10px] text-gray-400 font-mono">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Categories tree */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-5 overscroll-contain">
        {DOCS_CATEGORIES.map((cat) => {
          const isOpen = openCategories[cat.id] ?? true;
          return (
            <div key={cat.id} className="space-y-1">
              <button
                onClick={() => toggleCategory(cat.id)}
                className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider text-gray-400 hover:text-gray-200 hover:bg-surface-raised transition-colors group cursor-pointer"
              >
                <div className="flex items-center space-x-2">
                  {getIcon(cat.icon)}
                  <span>{cat.title}</span>
                </div>
                {isOpen ? (
                  <ChevronDown className="w-3.5 h-3.5 text-gray-500 group-hover:text-gray-300" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5 text-gray-500 group-hover:text-gray-300" />
                )}
              </button>

              {isOpen && (
                <div className="mt-1 pl-2 space-y-0.5 border-l border-border/60 ml-3">
                  {cat.pages.map((page) => {
                    const isActive = page.id === activePageId;
                    return (
                      <button
                        key={page.id}
                        onClick={() => {
                          onSelectPage(page.id);
                          onCloseMobile?.();
                        }}
                        className={`w-full text-left flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                          isActive
                            ? 'bg-primary-600/15 border border-primary-500/30 text-primary-300 font-semibold shadow-sm'
                            : 'text-gray-400 hover:text-gray-100 hover:bg-surface-raised/70 border border-transparent'
                        }`}
                      >
                        <span className="truncate">{page.title}</span>
                        {page.badge && (
                          <span
                            className={`text-[9px] font-mono uppercase px-1.5 py-0.2 rounded font-semibold shrink-0 ml-1.5 ${
                              page.badge === 'Core'
                                ? 'bg-primary-500/20 text-primary-300 border border-primary-500/30'
                                : page.badge === 'Popular'
                                ? 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30'
                                : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                            }`}
                          >
                            {page.badge}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}

        {/* Resources & Links */}
        <div className="pt-4 border-t border-border/60 space-y-1">
          <div className="px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-gray-500">
            External Resources
          </div>
          <a
            href="https://github.com/Unknowmyt1M/youtube-research-mcp"
            target="_blank"
            rel="noreferrer"
            className="flex items-center justify-between px-3 py-2 rounded-lg text-xs text-gray-400 hover:text-white hover:bg-surface-raised transition-colors"
          >
            <span>GitHub Repository</span>
            <ExternalLink className="w-3.5 h-3.5 text-gray-500" />
          </a>
          <a
            href="https://youtube-research-mcp-production.up.railway.app/openapi.json"
            target="_blank"
            rel="noreferrer"
            className="flex items-center justify-between px-3 py-2 rounded-lg text-xs text-gray-400 hover:text-white hover:bg-surface-raised transition-colors"
          >
            <span>Live OpenAPI Spec</span>
            <ExternalLink className="w-3.5 h-3.5 text-gray-500" />
          </a>
        </div>
      </nav>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar (Permanent) */}
      <aside className="hidden lg:block w-72 h-[calc(100vh-4rem)] sticky top-16 shrink-0 z-30">
        {content}
      </aside>

      {/* Mobile Drawer (Collapsible with smooth overlay) */}
      {isOpenMobile && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div
            className="fixed inset-0 bg-black/75 backdrop-blur-sm transition-opacity"
            onClick={onCloseMobile}
          />
          <div className="relative w-80 max-w-[85vw] h-full shadow-2xl z-10 animate-in slide-in-from-left duration-200">
            {content}
          </div>
        </div>
      )}
    </>
  );
}
