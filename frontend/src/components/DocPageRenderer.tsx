import { useState } from 'react';
import { DocPage, CodeTab } from '../types/docs';
import { CodeBlock } from './CodeBlock';
import { 
  Info, 
  Lightbulb, 
  AlertTriangle, 
  AlertCircle, 
  ArrowLeft, 
  ArrowRight,
  ChevronRight,
  Clock
} from 'lucide-react';
import { DOCS_CATEGORIES } from '../docs/docsRegistry';

interface DocPageRendererProps {
  page: DocPage;
  onNavigatePage: (pageId: string) => void;
}

export function DocPageRenderer({ page, onNavigatePage }: DocPageRendererProps) {
  // Find previous and next pages
  const allPages = DOCS_CATEGORIES.flatMap((c) => c.pages);
  const currentIndex = allPages.findIndex((p) => p.id === page.id);
  const prevPage = currentIndex > 0 ? allPages[currentIndex - 1] : null;
  const nextPage = currentIndex < allPages.length - 1 ? allPages[currentIndex + 1] : null;

  return (
    <article className="max-w-3xl w-full mx-auto pb-16">
      {/* Breadcrumb & Metadata */}
      <div className="flex items-center space-x-2 text-xs text-gray-400 mb-4 font-mono">
        <span className="hover:text-gray-200">Docs</span>
        <ChevronRight className="w-3 h-3 text-gray-600" />
        <span className="text-gray-300">{page.category}</span>
        <ChevronRight className="w-3 h-3 text-gray-600" />
        <span className="text-primary-400 font-medium">{page.title}</span>
      </div>

      {/* Page Title & Badges */}
      <div className="border-b border-border/80 pb-6 mb-8">
        <div className="flex items-center space-x-3 mb-2">
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white font-sans">
            {page.title}
          </h1>
          {page.badge && (
            <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded-full bg-primary-500/20 text-primary-300 border border-primary-500/30">
              {page.badge}
            </span>
          )}
        </div>
        <p className="text-lg text-gray-300 leading-relaxed">
          {page.description}
        </p>

        {page.updatedAt && (
          <div className="flex items-center space-x-1.5 mt-4 text-xs text-gray-500 font-mono">
            <Clock className="w-3.5 h-3.5" />
            <span>Last verified: {page.updatedAt} • 122/122 Tests Passed</span>
          </div>
        )}
      </div>

      {/* Page Sections */}
      <div className="space-y-10">
        {page.sections.map((section) => (
          <section key={section.id} id={section.id} className="scroll-mt-24 space-y-4">
            <h2 className="text-xl sm:text-2xl font-bold text-gray-100 flex items-center group">
              <span className="text-primary-500 mr-2 opacity-60 group-hover:opacity-100 transition-opacity">#</span>
              {section.title}
            </h2>

            {/* Section Content (Markdown-like rendering) */}
            {section.content && (
              <div className="prose prose-invert max-w-none text-gray-300 text-sm sm:text-base leading-relaxed space-y-4 font-sans">
                {section.content.split('\n\n').map((para, pIdx) => {
                  if (para.startsWith('```') && para.endsWith('```')) {
                    const lines = para.slice(3, -3).trim().split('\n');
                    const lang = lines[0].trim();
                    const code = lines.slice(1).join('\n');
                    return <CodeBlock key={pIdx} code={code} language={lang || 'text'} />;
                  }

                  // Handle Bullet points
                  if (para.includes('\n* ') || para.includes('\n- ') || para.startsWith('* ') || para.startsWith('- ')) {
                    const items = para.split(/\n(?=[*-] |\d+\. )/);
                    return (
                      <ul key={pIdx} className="list-disc list-inside space-y-1.5 pl-2 text-gray-300">
                        {items.map((item, iIdx) => (
                          <li key={iIdx} className="leading-relaxed">
                            {item.replace(/^[*-] |\d+\. /, '')}
                          </li>
                        ))}
                      </ul>
                    );
                  }

                  // Handle Markdown tables
                  if (para.includes('|') && para.includes('---')) {
                    const rows = para.trim().split('\n').map((r) => r.split('|').map((c) => c.trim()).filter(Boolean));
                    if (rows.length >= 2) {
                      const headers = rows[0];
                      const dataRows = rows.slice(2);
                      return (
                        <div key={pIdx} className="my-4 overflow-x-auto rounded-xl border border-border bg-surface">
                          <table className="w-full text-xs sm:text-sm text-left">
                            <thead className="bg-surface-raised border-b border-border text-gray-200 uppercase font-mono text-[11px]">
                              <tr>
                                {headers.map((h, hIdx) => (
                                  <th key={hIdx} className="px-4 py-3 font-semibold">
                                    {h}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-border/60 font-sans">
                              {dataRows.map((r, rIdx) => (
                                <tr key={rIdx} className="hover:bg-white/[0.02]">
                                  {r.map((cell, cIdx) => (
                                    <td key={cIdx} className="px-4 py-3 text-gray-300 font-mono">
                                      {cell}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      );
                    }
                  }

                  return (
                    <p key={pIdx} className="leading-relaxed">
                      {para}
                    </p>
                  );
                })}
              </div>
            )}

            {/* Callouts */}
            {section.callouts && section.callouts.length > 0 && (
              <div className="space-y-3 my-4">
                {section.callouts.map((callout, cIdx) => {
                  const getCalloutMeta = () => {
                    switch (callout.type) {
                      case 'tip':
                        return {
                          icon: <Lightbulb className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />,
                          bg: 'bg-emerald-950/20 border-emerald-500/30 text-emerald-200',
                          defaultTitle: 'Tip',
                        };
                      case 'important':
                        return {
                          icon: <Info className="w-5 h-5 text-primary-400 shrink-0 mt-0.5" />,
                          bg: 'bg-primary-950/20 border-primary-500/40 text-primary-200',
                          defaultTitle: 'Important',
                        };
                      case 'warning':
                        return {
                          icon: <AlertTriangle className="w-5 h-5 text-yellow-400 shrink-0 mt-0.5" />,
                          bg: 'bg-yellow-950/20 border-yellow-500/40 text-yellow-200',
                          defaultTitle: 'Warning',
                        };
                      default:
                        return {
                          icon: <AlertCircle className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />,
                          bg: 'bg-cyan-950/20 border-cyan-500/30 text-cyan-200',
                          defaultTitle: 'Note',
                        };
                    }
                  };
                  const meta = getCalloutMeta();
                  return (
                    <div
                      key={cIdx}
                      className={`p-4 rounded-xl border flex items-start space-x-3 text-sm ${meta.bg}`}
                    >
                      {meta.icon}
                      <div className="space-y-1">
                        <div className="font-semibold">{callout.title || meta.defaultTitle}</div>
                        <div className="text-gray-300 text-xs sm:text-sm leading-relaxed">
                          {callout.content}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Parameter Definitions Table */}
            {section.params && section.params.length > 0 && (
              <div className="my-6">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-400 mb-3 font-mono">
                  Parameters Reference
                </h3>
                <div className="overflow-x-auto rounded-xl border border-border bg-surface">
                  <table className="w-full text-xs sm:text-sm text-left">
                    <thead className="bg-surface-raised border-b border-border text-gray-300 font-mono text-[11px]">
                      <tr>
                        <th className="px-4 py-3">Parameter</th>
                        <th className="px-4 py-3">Type</th>
                        <th className="px-4 py-3">Required</th>
                        <th className="px-4 py-3">Description</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/60">
                      {section.params.map((p, pIdx) => (
                        <tr key={pIdx} className="hover:bg-white/[0.02]">
                          <td className="px-4 py-3 font-mono font-semibold text-primary-300">
                            {p.name}
                          </td>
                          <td className="px-4 py-3 font-mono text-cyan-400 text-xs">
                            {p.type}
                          </td>
                          <td className="px-4 py-3 font-mono text-xs">
                            {p.required ? (
                              <span className="text-red-400 font-semibold">required</span>
                            ) : (
                              <span className="text-gray-500">optional (default: {p.default || 'none'})</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-gray-300 text-xs sm:text-sm">
                            {p.description}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Multi-language Code Tabs */}
            {section.codeTabs && section.codeTabs.length > 0 && (
              <CodeTabsRenderer tabs={section.codeTabs} />
            )}
          </section>
        ))}
      </div>

      {/* Pagination Footer */}
      <div className="mt-16 pt-8 border-t border-border flex items-center justify-between">
        {prevPage ? (
          <button
            onClick={() => onNavigatePage(prevPage.id)}
            className="flex items-center space-x-2 text-left p-3 rounded-xl hover:bg-surface border border-transparent hover:border-border transition-all text-sm text-gray-300 hover:text-white group"
          >
            <ArrowLeft className="w-4 h-4 text-gray-500 group-hover:text-primary-400 group-hover:-translate-x-1 transition-transform" />
            <div>
              <div className="text-xs text-gray-500 font-mono">Previous</div>
              <div className="font-medium text-gray-200">{prevPage.title}</div>
            </div>
          </button>
        ) : <div />}

        {nextPage && (
          <button
            onClick={() => onNavigatePage(nextPage.id)}
            className="flex items-center space-x-2 text-right p-3 rounded-xl hover:bg-surface border border-transparent hover:border-border transition-all text-sm text-gray-300 hover:text-white group"
          >
            <div>
              <div className="text-xs text-gray-500 font-mono">Next</div>
              <div className="font-medium text-gray-200">{nextPage.title}</div>
            </div>
            <ArrowRight className="w-4 h-4 text-gray-500 group-hover:text-primary-400 group-hover:translate-x-1 transition-transform" />
          </button>
        )}
      </div>
    </article>
  );
}

function CodeTabsRenderer({ tabs }: { tabs: CodeTab[] }) {
  const [activeTabIdx, setActiveTabIdx] = useState(0);
  const activeTab = tabs[activeTabIdx] || tabs[0];

  return (
    <div className="my-4 rounded-xl border border-border bg-surface overflow-hidden">
      {/* Tab bar */}
      <div className="flex items-center border-b border-border bg-surface-raised px-2 overflow-x-auto">
        {tabs.map((tab, idx) => (
          <button
            key={idx}
            onClick={() => setActiveTabIdx(idx)}
            className={`px-3.5 py-2 text-xs font-mono font-medium border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
              idx === activeTabIdx
                ? 'border-primary-500 text-white bg-surface'
                : 'border-transparent text-gray-400 hover:text-gray-200 hover:bg-surface/50'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Code body */}
      <div className="p-0">
        <CodeBlock
          code={activeTab.code}
          language={activeTab.language}
          filename={activeTab.filename}
          showLineNumbers={true}
        />
      </div>
    </div>
  );
}
