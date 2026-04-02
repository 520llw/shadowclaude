import React, { useEffect, useRef } from 'react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';
import { useWebSocket } from '@hooks/useWebSocket';
import { TerminalIcon, X, Maximize2, Minimize2 } from 'lucide-react';
import { useAppStore } from '@stores/appStore';

export const Terminal: React.FC = () => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const { sendCommand } = useWebSocket();
  const { toggleTerminal } = useAppStore();
  const [isExpanded, setIsExpanded] = React.useState(false);

  useEffect(() => {
    if (!terminalRef.current) return;

    // Initialize xterm.js
    const term = new XTerm({
      fontSize: 14,
      fontFamily: 'JetBrains Mono, Fira Code, Menlo, Monaco, Consolas, monospace',
      theme: {
        background: '#0d1117',
        foreground: '#c9d1d9',
        cursor: '#58a6ff',
        selectionBackground: '#264f78',
        black: '#484f58',
        red: '#f85149',
        green: '#3fb950',
        yellow: '#d29922',
        blue: '#58a6ff',
        magenta: '#a371f7',
        cyan: '#39c5cf',
        white: '#f0f6fc',
        brightBlack: '#6e7681',
        brightRed: '#f85149',
        brightGreen: '#56d364',
        brightYellow: '#e3b341',
        brightBlue: '#79c0ff',
        brightMagenta: '#bc8cff',
        brightCyan: '#39c5cf',
        brightWhite: '#f0f6fc',
      },
      cursorBlink: true,
      cursorStyle: 'block',
      scrollback: 10000,
      rows: 10,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(new WebLinksAddon());

    term.open(terminalRef.current);
    fitAddon.fit();

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    // Welcome message
    term.writeln('\x1b[1;34m╔══════════════════════════════════════════════════════════════╗\x1b[0m');
    term.writeln('\x1b[1;34m║\x1b[0m           \x1b[1;36mWelcome to ShadowClaude Terminal\x1b[0m                  \x1b[1;34m║\x1b[0m');
    term.writeln('\x1b[1;34m╚══════════════════════════════════════════════════════════════╝\x1b[0m');
    term.writeln('');
    term.writeln('\x1b[1;32mshadowclaude\x1b[0m@\x1b[1;33mworkspace\x1b[0m:\x1b[1;34m~\x1b[0m$ ', false);

    // Handle input
    let currentLine = '';
    term.onData((data) => {
      const code = data.charCodeAt(0);

      if (code === 13) { // Enter
        term.writeln('');
        if (currentLine.trim()) {
          sendCommand(currentLine);
          // Echo response for demo
          setTimeout(() => {
            term.writeln(`\x1b[90m[Command executed: ${currentLine}]\x1b[0m`);
            term.write('\x1b[1;32mshadowclaude\x1b[0m@\x1b[1;33mworkspace\x1b[0m:\x1b[1;34m~\x1b[0m$ ');
          }, 100);
        } else {
          term.write('\x1b[1;32mshadowclaude\x1b[0m@\x1b[1;33mworkspace\x1b[0m:\x1b[1;34m~\x1b[0m$ ');
        }
        currentLine = '';
      } else if (code === 127) { // Backspace
        if (currentLine.length > 0) {
          currentLine = currentLine.slice(0, -1);
          term.write('\b \b');
        }
      } else if (code >= 32) { // Printable characters
        currentLine += data;
        term.write(data);
      }
    });

    // Handle resize
    const handleResize = () => {
      fitAddon.fit();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      term.dispose();
    };
  }, [sendCommand]);

  return (
    <div className={`flex flex-col bg-shadow-900 border-t border-shadow-600 
                      ${isExpanded ? 'fixed inset-0 z-50' : 'h-64'}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-shadow-800 border-b border-shadow-600">
        <div className="flex items-center gap-2">
          <TerminalIcon className="w-4 h-4 text-shadow-400" />
          <span className="text-sm font-medium text-shadow-200">Terminal</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 rounded hover:bg-shadow-700 text-shadow-400 transition-colors"
          >
            {isExpanded ? (
              <Minimize2 className="w-4 h-4" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </button>
          {!isExpanded && (
            <button
              onClick={toggleTerminal}
              className="p-1.5 rounded hover:bg-shadow-700 text-shadow-400 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Terminal Content */}
      <div 
        ref={terminalRef} 
        className="flex-1 p-2 overflow-hidden"
        style={{ background: '#0d1117' }}
      />
    </div>
  );
};

export default Terminal;