import { useState, useEffect } from 'react';
import { DocPage } from '../types/docs';
import { Share2, Check, ExternalLink, Sparkles } from 'lucide-react';

interface TableOfContentsProps {
  page: DocPage;
}

export function TableOfContents({ page }: TableOfContentsProps) {
  const [activeId, setActiveId] = useState<string>('');
  const [copiedEndpoint, setCopiedEndpoint] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        });
      },
      { rootMargin: '-80px 0% -60% 0%' }
    );

    page.sections.forEach((section) => {
      const el = document.getElementById(section.id);
      if (el) observer.observe(el);
      section.subsections?.forEach((sub) => {
        const subEl = document.getElementById(sub.id);
        if (subEl) observer.observe(subEl);
      });
    });

    return () => observer.disconnect();
  }, [page]);

  const copyEndpoint = async () => {
    try {
      await navigator.clipboard.writeText('https://youtube-research-mcp-production.up.railway.app/mcp');
      setCopiedEndpoint(true);
      setTimeout(() => setCopiedEndpoint(false), 2000);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  };

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      const topOffset = 80;
      const elementPosition = el.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - topOffset;
      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth',
      });
    }
  };

  return (
    <div className="space-y-6 text-xs">
      {/* On this page nav */}
      <div>
        <h4 className="font-semibold text-gray-200 uppercase tracking-wider mb-3 text-[11px]">
          On This Page
        </h4>
        <ul className="space-y-2 border-l border-border/80 pl-3">
          {page.sections.map((sec) => {
            const isActive = activeId === sec.id;
            return (
              <li key={sec.id}>
                <button
                  onClick={() => scrollTo(sec.id)}
                  className={`text-left block transition-colors leading-relaxed hover:text-white ${
                    isActive ? 'text-primary-400 font-semibold -ml-[13px] border-l-2 border-primary-500 pl-2.5' : 'text-gray-400'
                  }`}
                >
                  {sec.title}
                </button>
                {sec.subsections && sec.subsections.length > 0 && (
                  <ul className="mt-1.5 pl-3 space-y-1.5 border-l border-border/40">
                    {sec.subsections.map((sub) => (
                      <li key={sub.id}>
                        <button
                          onClick={() => scrollTo(sub.id)}
                          className={`text-left block transition-colors leading-snug hover:text-white ${
                            activeId === sub.id ? 'text-cyan-400 font-medium' : 'text-gray-500'
                          }`}
                        >
                          {sub.title}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      </div>

      {/* Production Quick Action Card */}
      <div className="p-3.5 rounded-xl bg-gradient-to-br from-surface-raised to-surface border border-border/80 space-y-3">
        <div className="flex items-center space-x-2 text-primary-400 font-medium text-xs">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Live Production MCP</span>
        </div>
        <p className="text-gray-400 text-[11px] leading-relaxed">
          Connect your AI client directly to the hosted Streamable HTTP endpoint.
        </p>
        <button
          onClick={copyEndpoint}
          className="w-full flex items-center justify-center space-x-1.5 py-1.5 px-2.5 rounded-lg bg-primary-600/20 hover:bg-primary-600/30 text-primary-300 border border-primary-500/30 text-xs font-mono font-medium transition-all active:scale-98 cursor-pointer"
        >
          {copiedEndpoint ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span>Copied URL</span>
            </>
          ) : (
            <>
              <Share2 className="w-3.5 h-3.5" />
              <span>Copy MCP URL</span>
            </>
          )}
        </button>
      </div>

      {/* Community / GitHub link */}
      <div className="pt-2 border-t border-border/60">
        <a
          href="https://github.com/Unknowmyt1M/youtube-research-mcp"
          target="_blank"
          rel="noreferrer"
          className="flex items-center justify-between text-gray-400 hover:text-white transition-colors"
        >
          <span>Edit page on GitHub</span>
          <ExternalLink className="w-3 h-3 text-gray-500" />
        </a>
      </div>
    </div>
  );
}
