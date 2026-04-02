import React from 'react';
import Editor from '@monaco-editor/react';
import { X, Circle } from 'lucide-react';
import { useAppStore } from '@stores/appStore';
import type { FileNode } from '@types/index';

const getLanguage = (filename: string): string => {
  const ext = filename.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'ts':
    case 'tsx':
      return 'typescript';
    case 'js':
    case 'jsx':
      return 'javascript';
    case 'json':
      return 'json';
    case 'md':
      return 'markdown';
    case 'css':
      return 'css';
    case 'scss':
      return 'scss';
    case 'less':
      return 'less';
    case 'html':
      return 'html';
    case 'xml':
      return 'xml';
    case 'yaml':
    case 'yml':
      return 'yaml';
    case 'py':
      return 'python';
    case 'rs':
      return 'rust';
    case 'go':
      return 'go';
    default:
      return 'plaintext';
  }
};

const Tab: React.FC<{ file: FileNode; isActive: boolean }> = ({ file, isActive }) => {
  const { setActiveFile, closeFile } = useAppStore();

  return (
    <div
      onClick={() => setActiveFile(file)}
      className={`
        group flex items-center gap-2 px-3 py-2 min-w-fit cursor-pointer
        border-r border-shadow-600 transition-colors
        ${isActive 
          ? 'bg-shadow-800 text-shadow-100 border-t-2 border-t-accent-blue' 
          : 'bg-shadow-900 text-shadow-400 hover:bg-shadow-700 hover:text-shadow-200'
        }
      `}
    >
      <Circle className={`w-2 h-2 ${isActive ? 'fill-accent-blue text-accent-blue' : 'text-shadow-500'}`} />
      <span className="text-sm truncate max-w-[150px]">{file.name}</span>
      <button
        onClick={(e) => {
          e.stopPropagation();
          closeFile(file.id);
        }}
        className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-shadow-600 transition-all"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};

export const CodeEditor: React.FC = () => {
  const { activeFile, openFiles } = useAppStore();
  const [content, setContent] = React.useState('');

  // Mock content for demonstration
  React.useEffect(() => {
    if (activeFile) {
      setContent(`// ${activeFile.name}
// This is a mock content for demonstration

import React from 'react';
import { useAppStore } from '@stores/appStore';

export const ${activeFile.name.replace(/\.[^/.]+$/, '')} = () => {
  return (
    <div>
      <h1>${activeFile.name}</h1>
      <p>Component content goes here...</p>
    </div>
  );
};

export default ${activeFile.name.replace(/\.[^/.]+$/, '')};`);
    }
  }, [activeFile]);

  if (!activeFile) {
    return (
      <div className="h-full bg-shadow-900 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4 opacity-20">🌑</div>
          <p className="text-shadow-400 text-lg">ShadowClaude</p>
          <p className="text-shadow-500 text-sm mt-2">Select a file to start editing</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-shadow-900">
      {/* Tabs */}
      <div className="flex items-center bg-shadow-900 overflow-x-auto scrollbar-hide">
        {openFiles.map((file) => (
          <Tab 
            key={file.id} 
            file={file} 
            isActive={activeFile.id === file.id} 
          />
        ))}
      </div>

      {/* Editor */}
      <div className="flex-1 overflow-hidden">
        <Editor
          height="100%"
          language={getLanguage(activeFile.name)}
          value={content}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            fontFamily: 'JetBrains Mono, Fira Code, Menlo, Monaco, Consolas, monospace',
            lineNumbers: 'on',
            roundedSelection: false,
            scrollBeyondLastLine: false,
            readOnly: false,
            automaticLayout: true,
            padding: { top: 16 },
            folding: true,
            renderLineHighlight: 'all',
            selectOnLineNumbers: true,
            cursorBlinking: 'smooth',
            smoothScrolling: true,
          }}
          onChange={(value) => setContent(value || '')}
        />
      </div>
    </div>
  );
};

export default CodeEditor;