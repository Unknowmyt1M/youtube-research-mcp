import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { ResearchStudio } from './views/ResearchStudio';
import { PinpointPlayer } from './views/PinpointPlayer';
import { SearchExplorer } from './views/SearchExplorer';
import { TelemetryView } from './views/TelemetryView';
import { AdminDashboard } from './views/AdminDashboard';

export function App() {
  const [activeTab, setActiveTab] = useState<'research' | 'pinpoint' | 'search' | 'telemetry' | 'admin'>('research');

  return (
    <div className="min-h-screen bg-background text-gray-100 flex flex-col">
      {/* Top Navbar */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Content View */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'research' && <ResearchStudio />}
        {activeTab === 'pinpoint' && <PinpointPlayer />}
        {activeTab === 'search' && <SearchExplorer />}
        {activeTab === 'telemetry' && <TelemetryView />}
        {activeTab === 'admin' && <AdminDashboard />}
      </main>

      {/* Footer */}
      <footer className="border-t border-border/60 py-6 text-center text-xs text-gray-500 font-mono">
        <p>
          YouTube Research MCP Dashboard • Powered by FastMCP 2.0 & BM25s Hybrid Retrieval
        </p>
      </footer>
    </div>
  );
}

export default App;
