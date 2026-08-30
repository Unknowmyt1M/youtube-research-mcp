import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
  showLineNumbers?: boolean;
}

export function CodeBlock({ code, language = 'text', filename, showLineNumbers = false }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code', err);
    }
  };

  const lines = code.trim().split('\n');

  return (
    <div className="my-4 rounded-xl overflow-hidden border border-border bg-surface shadow-lg group">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-surface-raised border-b border-border/80 text-xs font-mono text-gray-400">
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1.5 mr-2">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-green-500/60" />
          </div>
          {filename ? (
            <span className="text-gray-200 font-medium">{filename}</span>
          ) : (
            <span className="uppercase tracking-wider text-cyan-400/90 font-semibold">{language}</span>
          )}
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-surface hover:bg-surface-hover border border-border text-gray-300 hover:text-white transition-all text-xs font-sans cursor-pointer active:scale-95"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400 font-medium">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5 text-gray-400" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code body */}
      <div className="p-4 overflow-x-auto text-sm font-mono leading-relaxed bg-[#0a0c14]">
        <pre className="text-gray-200">
          {showLineNumbers ? (
            <table className="border-collapse w-full">
              <tbody>
                {lines.map((line, idx) => (
                  <tr key={idx} className="hover:bg-white/[0.02]">
                    <td className="pr-4 text-right select-none text-gray-600 text-xs font-mono w-8 align-top">
                      {idx + 1}
                    </td>
                    <td className="whitespace-pre align-top">{line || ' '}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <code>{code.trim()}</code>
          )}
        </pre>
      </div>
    </div>
  );
}
