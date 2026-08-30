import { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { DocsSidebar } from './components/DocsSidebar';
import { TableOfContents } from './components/TableOfContents';
import { DocPageRenderer } from './components/DocPageRenderer';
import { SearchModal } from './components/SearchModal';
import { InteractiveExplorer } from './components/InteractiveExplorer';
import { Footer } from './components/Footer';
import { DOCS_CATEGORIES } from './docs/docsRegistry';

export function App() {
  const [currentView, setCurrentView] = useState<'docs' | 'explorer'>('docs');
  const [activePageId, setActivePageId] = useState<string>('what-is-nexora');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Sync hash with active page ID on mount / hashchange
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '').trim();
      if (hash === 'explorer') {
        setCurrentView('explorer');
      } else if (hash) {
        const allPages = DOCS_CATEGORIES.flatMap((c) => c.pages);
        const match = allPages.find((p) => p.id === hash);
        if (match) {
          setActivePageId(match.id);
          setCurrentView('docs');
        }
      }
    };

    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // Global keyboard shortcut for Search (Cmd+K / Ctrl+K / /)
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      } else if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) {
        e.preventDefault();
        setIsSearchOpen(true);
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  const navigateToPage = (pageId: string) => {
    setActivePageId(pageId);
    setCurrentView('docs');
    window.location.hash = pageId;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Find active doc page
  const allPages = DOCS_CATEGORIES.flatMap((c) => c.pages);
  const activePage = allPages.find((p) => p.id === activePageId) || allPages[0];

  return (
    <div className="min-h-screen bg-background text-gray-100 flex flex-col font-sans selection:bg-primary-500/30 selection:text-primary-200">
      {/* Top Navbar */}
      <Navbar
        currentView={currentView}
        setCurrentView={(view) => {
          setCurrentView(view);
          if (view === 'explorer') {
            window.location.hash = 'explorer';
          }
        }}
        onOpenSearch={() => setIsSearchOpen(true)}
        onToggleMobileSidebar={() => setIsMobileSidebarOpen(true)}
        onNavigatePage={navigateToPage}
      />

      {/* Main Container */}
      <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8">
        {currentView === 'docs' ? (
          <div className="flex gap-8 py-6">
            {/* Left Sidebar */}
            <DocsSidebar
              activePageId={activePageId}
              onSelectPage={navigateToPage}
              onOpenSearch={() => setIsSearchOpen(true)}
              isOpenMobile={isMobileSidebarOpen}
              onCloseMobile={() => setIsMobileSidebarOpen(false)}
            />

            {/* Center Documentation Content */}
            <main className="flex-1 min-w-0 px-2 sm:px-4">
              <DocPageRenderer
                page={activePage}
                onNavigatePage={navigateToPage}
              />
            </main>

            {/* Right On-Page Table of Contents */}
            <aside className="hidden xl:block w-64 h-[calc(100vh-5rem)] sticky top-20 shrink-0">
              <TableOfContents page={activePage} />
            </aside>
          </div>
        ) : (
          /* Interactive Live Explorer View */
          <main className="py-8">
            <InteractiveExplorer />
          </main>
        )}
      </div>

      {/* Search Modal */}
      <SearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onSelectPage={navigateToPage}
      />

      {/* Footer */}
      <Footer onNavigatePage={navigateToPage} />
    </div>
  );
}

export default App;
