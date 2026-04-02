import React from 'react';
import { 
  Menu, 
  LayoutTemplate, 
  MessageSquare, 
  Terminal, 
  Wrench, 
  Bot,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { FileBrowser } from '@components/FileBrowser';
import { CodeEditor } from '@components/CodeEditor';
import { Chat } from '@components/Chat';
import { Terminal as TerminalPanel } from '@components/Terminal';
import { ToolVisualizer } from '@components/ToolVisualizer';
import { AgentPanel } from '@components/AgentPanel';
import { useAppStore } from '@stores/appStore';

type ViewMode = 'editor' | 'split' | 'chat';

export const Layout: React.FC = () => {
  const [viewMode, setViewMode] = React.useState<ViewMode>('split');
  const { sidebarVisible, terminalVisible, agentPanelVisible, toggleSidebar, toggleTerminal, toggleAgentPanel } = useAppStore();

  const renderMainContent = () => {
    if (viewMode === 'editor') {
      return <CodeEditor />;
    }
    
    if (viewMode === 'chat') {
      return <Chat />;
    }

    // Split view - Chat and Editor side by side
    return (
      <PanelGroup direction="horizontal">
        <Panel defaultSize={45} minSize={30}>
          <Chat />
        </Panel>
        <PanelResizeHandle className="w-1 bg-shadow-600 hover:bg-accent-blue/50 transition-colors" />
        <Panel defaultSize={55} minSize={30}>
          <CodeEditor />
        </Panel>
      </PanelGroup>
    );
  };

  return (
    <div className="h-screen flex flex-col bg-shadow-900">
      {/* Top Bar */}
      <header className="h-12 flex items-center justify-between px-3 bg-shadow-800 border-b border-shadow-600">
        <div className="flex items-center gap-2">
          <button
            onClick={toggleSidebar}
            className="p-2 rounded hover:bg-shadow-700 text-shadow-400 transition-colors"
          >
            {sidebarVisible ? <ChevronLeft className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
          
          <div className="flex items-center gap-2 ml-4">
            <div className="w-6 h-6 rounded bg-accent-blue flex items-center justify-center">
              <span className="text-sm font-bold text-shadow-900">S</span>
            </div>
            <span className="font-semibold">ShadowClaude</span>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setViewMode('editor')}
            className={`
              p-2 rounded transition-colors
              ${viewMode === 'editor' 
                ? 'bg-accent-blue/20 text-accent-blue' 
                : 'hover:bg-shadow-700 text-shadow-400'
              }
            `}
            title="Editor Only"
          >
            <LayoutTemplate className="w-5 h-5" />
          </button>
          
          <button
            onClick={() => setViewMode('split')}
            className={`
              p-2 rounded transition-colors
              ${viewMode === 'split' 
                ? 'bg-accent-blue/20 text-accent-blue' 
                : 'hover:bg-shadow-700 text-shadow-400'
              }
            `}
            title="Split View"
          >
            <MessageSquare className="w-5 h-5" />
          </button>
          
          <button
            onClick={() => setViewMode('chat')}
            className={`
              p-2 rounded transition-colors
              ${viewMode === 'chat' 
                ? 'bg-accent-blue/20 text-accent-blue' 
                : 'hover:bg-shadow-700 text-shadow-400'
              }
            `}
            title="Chat Only"
          >
            <MessageSquare className="w-5 h-5" />
          </button>

          <div className="w-px h-6 bg-shadow-600 mx-2" />

          <button
            onClick={toggleTerminal}
            className={`
              p-2 rounded transition-colors
              ${terminalVisible 
                ? 'bg-accent-blue/20 text-accent-blue' 
                : 'hover:bg-shadow-700 text-shadow-400'
              }
            `}
            title="Toggle Terminal"
          >
            <Terminal className="w-5 h-5" />
          </button>
          
          <button
            onClick={toggleAgentPanel}
            className={`
              p-2 rounded transition-colors
              ${agentPanelVisible 
                ? 'bg-accent-orange/20 text-accent-orange' 
                : 'hover:bg-shadow-700 text-shadow-400'
              }
            `}
            title="Toggle Agent Panel"
          >
            <Bot className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - File Browser */}
        {sidebarVisible && (
          <div className="w-64 flex-shrink-0">
            <FileBrowser />
          </div>
        )}

        {/* Center Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 overflow-hidden">
            {renderMainContent()}
          </div>

          {/* Terminal */}
          {terminalVisible && (
            <TerminalPanel />
          )}
        </div>

        {/* Right Panel - Tools */}
        {agentPanelVisible && (
          <div className="w-80 flex-shrink-0 flex">
            <PanelGroup direction="horizontal">
              <Panel defaultSize={50} minSize={30}>
                <ToolVisualizer />
              </Panel>
              <PanelResizeHandle className="w-1 bg-shadow-600 hover:bg-accent-blue/50 transition-colors" />
              <Panel defaultSize={50} minSize={30}>
                <AgentPanel />
              </Panel>
            </PanelGroup>
          </div>
        )}
      </div>
    </div>
  );
};

export default Layout;