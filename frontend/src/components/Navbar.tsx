import React, { useState, useEffect } from 'react';
import { Sparkles, Activity, Search, Compass, ExternalLink, Settings as SettingsIcon, CheckCircle2, AlertCircle, ShieldAlert } from 'lucide-react';
import { api, getServerBaseUrl, setServerBaseUrl } from '../api/client';

interface NavbarProps {
  activeTab: 'research' | 'pinpoint' | 'search' | 'telemetry' | 'admin';
  setActiveTab: (tab: 'research' | 'pinpoint' | 'search' | 'telemetry' | 'admin') => void;
}

interface NavItem {
  id: 'research' | 'pinpoint' | 'search' | 'telemetry' | 'admin';
  label: string;
  icon: any;
  badge?: string;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const [isOnline, setIsOnline] = useState<boolean | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [customUrl, setCustomUrl] = useState(getServerBaseUrl());

  const checkStatus = async () => {
    try {
      await api.checkHealth();
      setIsOnline(true);
    } catch {
      setIsOnline(false);
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSaveUrl = () => {
    setServerBaseUrl(customUrl);
    setShowSettings(false);
    checkStatus();
  };

  const navItems: NavItem[] = [
    { id: 'research', label: 'Research Studio', icon: Sparkles, badge: 'Phase 2' },
    { id: 'pinpoint', label: 'Pinpoint Player', icon: Compass },
    { id: 'search', label: 'Search & Inspector', icon: Search },
    { id: 'telemetry', label: 'System Health', icon: Activity },
    { id: 'admin', label: 'Admin Control', icon: ShieldAlert, badge: 'Root' },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-surface/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Title */}
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-red-600 to-violet-600 p-[1px] flex items-center justify-center glow-red shadow-lg">
              <div className="w-full h-full bg-background rounded-[11px] flex items-center justify-center">
                <span className="text-red-500 font-bold text-lg">▶</span>
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-base tracking-tight text-white">YouTube Research</span>
                <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-red-500/10 text-red-400 border border-red-500/20">
                  MCP v2.0
                </span>
              </div>
              <p className="text-[11px] text-gray-400 font-mono hidden sm:block">Model-Agnostic Knowledge Engine</p>
            </div>
          </div>

          {/* Center Tabs */}
          <nav className="hidden md:flex items-center space-x-1 p-1 bg-background/80 rounded-xl border border-border">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-surface-raised text-white shadow-sm border border-border text-red-400'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-surface/50'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-red-400' : ''}`} />
                  <span>{item.label}</span>
                  {item.badge && (
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-red-500/20 text-red-300 font-mono">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Right Status & GitHub */}
          <div className="flex items-center space-x-3">
            {/* Online Status Badge */}
            <div
              onClick={() => setShowSettings(!showSettings)}
              className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-background border border-border cursor-pointer hover:border-gray-600 transition"
              title="Click to configure Backend URL"
            >
              <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-400 animate-pulse' : 'bg-red-500'}`} />
              <span className="text-gray-300">{isOnline ? 'MCP Live' : 'Disconnected'}</span>
              <SettingsIcon className="w-3 h-3 text-gray-500 ml-1" />
            </div>

            {/* GitHub Link */}
            <a
              href="https://github.com/Unknowmyt1M/youtube-research-mcp"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-raised text-gray-300 hover:text-white border border-border hover:border-gray-600 transition"
            >
              <span>GitHub</span>
              <ExternalLink className="w-3 h-3 text-gray-400" />
            </a>
          </div>
        </div>

        {/* Mobile Navigation Tabs */}
        <div className="flex md:hidden overflow-x-auto py-2 space-x-1 border-t border-border/50">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs whitespace-nowrap ${
                  isActive ? 'bg-surface-raised text-red-400 border border-border' : 'text-gray-400'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Settings Modal Dropdown */}
      {showSettings && (
        <div className="absolute right-6 top-18 w-80 p-4 rounded-xl glass-panel shadow-2xl z-50 animate-in fade-in slide-in-from-top-2">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-xs font-semibold text-white uppercase tracking-wider">Backend Server Connection</h4>
            {isOnline ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-400" />
            )}
          </div>
          <div className="space-y-2">
            <label className="text-[11px] text-gray-400">FastMCP / REST Endpoint URL</label>
            <input
              type="text"
              value={customUrl}
              onChange={(e) => setCustomUrl(e.target.value)}
              placeholder="http://127.0.0.1:8000"
              className="w-full px-3 py-1.5 text-xs bg-background border border-border rounded-lg text-white font-mono focus:outline-none focus:border-red-500"
            />
            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={() => setShowSettings(false)}
                className="px-3 py-1 text-xs text-gray-400 hover:text-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveUrl}
                className="px-3 py-1 text-xs bg-red-600 hover:bg-red-500 text-white rounded-lg font-medium transition"
              >
                Save & Connect
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};
