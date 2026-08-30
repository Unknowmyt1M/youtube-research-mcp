import React, { useState, useEffect, useRef } from 'react';
import { Search, X, Hash, ArrowRight, FileText, Wrench, Code2, Server } from 'lucide-react';
import { DOCS_CATEGORIES } from '../docs/docsRegistry';
import { DocPage } from '../types/docs';

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectPage: (pageId: string) => void;
}

interface SearchResultItem {
  page: DocPage;
  matchedText: string;
  sectionId?: string;
  sectionTitle?: string;
}

export function SearchModal({ isOpen, onClose, onSelectPage }: SearchModalProps) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Compute search results
  const results: SearchResultItem[] = React.useMemo(() => {
    if (!query.trim()) {
      // Return top popular pages when query is empty
      const allPages = DOCS_CATEGORIES.flatMap((c) => c.pages);
      return allPages.slice(0, 6).map((page) => ({
        page,
        matchedText: page.description,
      }));
    }

    const q = query.toLowerCase().trim();
    const matches: SearchResultItem[] = [];

    for (const cat of DOCS_CATEGORIES) {
      for (const page of cat.pages) {
        const titleMatch = page.title.toLowerCase().includes(q);
        const descMatch = page.description.toLowerCase().includes(q);

        if (titleMatch || descMatch) {
          matches.push({
            page,
            matchedText: page.description,
          });
          continue;
        }

        // Search inside sections
        for (const sec of page.sections) {
          if (sec.title.toLowerCase().includes(q) || sec.content?.toLowerCase().includes(q)) {
            matches.push({
              page,
              sectionId: sec.id,
              sectionTitle: sec.title,
              matchedText: sec.content ? sec.content.slice(0, 140) + '...' : sec.title,
            });
            break;
          }
        }
      }
    }
    return matches;
  }, [query]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, results.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + results.length) % Math.max(1, results.length));
    } else if (e.key === 'Enter' && results[selectedIndex]) {
      e.preventDefault();
      onSelectPage(results[selectedIndex].page.id);
      onClose();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  if (!isOpen) return null;

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'MCP':
      case 'Tools':
        return <Wrench className="w-4 h-4 text-cyan-400" />;
      case 'REST API':
        return <Code2 className="w-4 h-4 text-primary-400" />;
      case 'Self Hosting':
        return <Server className="w-4 h-4 text-emerald-400" />;
      case 'Architecture':
        return <Code2 className="w-4 h-4 text-indigo-400" />;
      case 'Integrations':
        return <FileText className="w-4 h-4 text-purple-400" />;
      default:
        return <FileText className="w-4 h-4 text-gray-400" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="w-full max-w-2xl bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[75vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-border bg-surface-raised">
          <Search className="w-5 h-5 text-gray-400 mr-3" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search documentation, tools, API endpoints, errors... (Press ESC to close)"
            className="flex-1 bg-transparent text-gray-100 placeholder-gray-500 text-sm focus:outline-none"
          />
          <button
            onClick={onClose}
            className="p-1 rounded-md text-gray-400 hover:text-white hover:bg-surface transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {results.length === 0 ? (
            <div className="py-12 text-center text-gray-500 text-sm">
              No documentation pages found matching &ldquo;<span className="text-gray-300 font-mono">{query}</span>&rdquo;
            </div>
          ) : (
            results.map((res, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <button
                  key={`${res.page.id}-${res.sectionId || 'root'}-${idx}`}
                  onClick={() => {
                    onSelectPage(res.page.id);
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`w-full text-left p-3 rounded-xl transition-all flex items-start justify-between group ${
                    isSelected ? 'bg-primary-600/15 border border-primary-500/40 text-white' : 'text-gray-300 hover:bg-surface-raised border border-transparent'
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <div className="p-2 rounded-lg bg-surface border border-border mt-0.5">
                      {getCategoryIcon(res.page.category)}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-medium text-sm text-gray-100 group-hover:text-white">
                          {res.page.title}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-raised border border-border text-gray-400">
                          {res.page.category}
                        </span>
                        {res.sectionTitle && (
                          <span className="text-xs text-cyan-400 flex items-center">
                            <Hash className="w-3 h-3 mr-0.5" />
                            {res.sectionTitle}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-400 mt-1 line-clamp-2 leading-relaxed">
                        {res.matchedText}
                      </p>
                    </div>
                  </div>
                  <ArrowRight
                    className={`w-4 h-4 ml-2 mt-2 transition-transform ${
                      isSelected ? 'text-primary-400 translate-x-0.5' : 'text-gray-600 opacity-0 group-hover:opacity-100'
                    }`}
                  />
                </button>
              );
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2.5 bg-surface-raised border-t border-border flex items-center justify-between text-xs text-gray-500 font-mono">
          <div className="flex items-center space-x-3">
            <span><kbd className="px-1.5 py-0.5 rounded bg-surface border border-border text-[10px] text-gray-400">↑</kbd> <kbd className="px-1.5 py-0.5 rounded bg-surface border border-border text-[10px] text-gray-400">↓</kbd> Navigate</span>
            <span><kbd className="px-1.5 py-0.5 rounded bg-surface border border-border text-[10px] text-gray-400">↵</kbd> Select</span>
            <span><kbd className="px-1.5 py-0.5 rounded bg-surface border border-border text-[10px] text-gray-400">ESC</kbd> Close</span>
          </div>
          <span>Nexora Search v2.0</span>
        </div>
      </div>
    </div>
  );
}
