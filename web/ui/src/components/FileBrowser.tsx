import React from 'react';
import { 
  ChevronRight, 
  ChevronDown, 
  FileCode, 
  FileText, 
  Folder, 
  FolderOpen,
  FileJson,
  FileType,
  File
} from 'lucide-react';
import { useAppStore } from '@stores/appStore';
import type { FileNode } from '@types/index';

interface FileTreeNodeProps {
  node: FileNode;
  depth: number;
}

const getFileIcon = (filename: string, isOpen?: boolean) => {
  const ext = filename.split('.').pop()?.toLowerCase();
  
  switch (ext) {
    case 'tsx':
    case 'ts':
    case 'jsx':
    case 'js':
      return <FileCode className="w-4 h-4 text-accent-blue" />;
    case 'json':
      return <FileJson className="w-4 h-4 text-accent-yellow" />;
    case 'md':
    case 'txt':
      return <FileText className="w-4 h-4 text-shadow-300" />;
    case 'css':
    case 'scss':
    case 'less':
      return <FileType className="w-4 h-4 text-accent-blue" />;
    default:
      return <File className="w-4 h-4 text-shadow-400" />;
  }
};

const FileTreeNode: React.FC<FileTreeNodeProps> = ({ node, depth }) => {
  const { openFile, toggleFolder, activeFile } = useAppStore();
  const isActive = activeFile?.id === node.id;

  const handleClick = () => {
    if (node.type === 'directory') {
      toggleFolder(node.id);
    } else {
      openFile(node);
    }
  };

  const paddingLeft = 12 + depth * 16;

  return (
    <div>
      <button
        onClick={handleClick}
        className={`
          w-full flex items-center gap-1.5 px-2 py-1 text-sm transition-colors
          ${isActive 
            ? 'bg-accent-blue/20 text-shadow-100' 
            : 'text-shadow-200 hover:bg-shadow-700 hover:text-shadow-100'
          }
        `}
        style={{ paddingLeft: `${paddingLeft}px` }}
      >
        {node.type === 'directory' ? (
          <>
            <span className="w-4 h-4 flex items-center justify-center">
              {node.isOpen ? (
                <ChevronDown className="w-3.5 h-3.5 text-shadow-400" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-shadow-400" />
              )}
            </span>
            {node.isOpen ? (
              <FolderOpen className="w-4 h-4 text-accent-yellow" />
            ) : (
              <Folder className="w-4 h-4 text-accent-yellow" />
            )}
          </>
        ) : (
          <>
            <span className="w-4" />
            {getFileIcon(node.name)}
          </>
        )}
        <span className="truncate">{node.name}</span>
      </button>
      
      {node.type === 'directory' && node.isOpen && node.children && (
        <div>
          {node.children.map((child) => (
            <FileTreeNode key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
};

export const FileBrowser: React.FC = () => {
  const files = useAppStore((state) => state.files);
  const setFiles = useAppStore((state) => state.setFiles);

  // Mock data for demonstration
  React.useEffect(() => {
    const mockFiles: FileNode[] = [
      {
        id: 'root',
        name: 'shadowclaude',
        type: 'directory',
        path: '/',
        isOpen: true,
        children: [
          {
            id: 'src',
            name: 'src',
            type: 'directory',
            path: '/src',
            isOpen: true,
            children: [
              {
                id: 'components',
                name: 'components',
                type: 'directory',
                path: '/src/components',
                isOpen: false,
                children: [
                  { id: 'FileBrowser.tsx', name: 'FileBrowser.tsx', type: 'file', path: '/src/components/FileBrowser.tsx', language: 'typescript' },
                  { id: 'CodeEditor.tsx', name: 'CodeEditor.tsx', type: 'file', path: '/src/components/CodeEditor.tsx', language: 'typescript' },
                  { id: 'Chat.tsx', name: 'Chat.tsx', type: 'file', path: '/src/components/Chat.tsx', language: 'typescript' },
                  { id: 'Terminal.tsx', name: 'Terminal.tsx', type: 'file', path: '/src/components/Terminal.tsx', language: 'typescript' },
                  { id: 'ToolVisualizer.tsx', name: 'ToolVisualizer.tsx', type: 'file', path: '/src/components/ToolVisualizer.tsx', language: 'typescript' },
                  { id: 'AgentPanel.tsx', name: 'AgentPanel.tsx', type: 'file', path: '/src/components/AgentPanel.tsx', language: 'typescript' },
                ]
              },
              {
                id: 'stores',
                name: 'stores',
                type: 'directory',
                path: '/src/stores',
                isOpen: false,
                children: [
                  { id: 'appStore.ts', name: 'appStore.ts', type: 'file', path: '/src/stores/appStore.ts', language: 'typescript' },
                ]
              },
              {
                id: 'types',
                name: 'types',
                type: 'directory',
                path: '/src/types',
                isOpen: false,
                children: [
                  { id: 'index.ts', name: 'index.ts', type: 'file', path: '/src/types/index.ts', language: 'typescript' },
                ]
              },
              { id: 'main.tsx', name: 'main.tsx', type: 'file', path: '/src/main.tsx', language: 'typescript' },
              { id: 'App.tsx', name: 'App.tsx', type: 'file', path: '/src/App.tsx', language: 'typescript' },
            ]
          },
          { id: 'package.json', name: 'package.json', type: 'file', path: '/package.json', language: 'json' },
          { id: 'tsconfig.json', name: 'tsconfig.json', type: 'file', path: '/tsconfig.json', language: 'json' },
          { id: 'README.md', name: 'README.md', type: 'file', path: '/README.md', language: 'markdown' },
        ]
      }
    ];
    setFiles(mockFiles);
  }, [setFiles]);

  return (
    <div className="h-full bg-shadow-800 border-r border-shadow-600 overflow-y-auto">
      <div className="flex items-center justify-between px-4 py-2 border-b border-shadow-600">
        <span className="text-xs font-semibold text-shadow-400 uppercase tracking-wider">Explorer</span>
      </div>
      <div className="py-2">
        {files.map((file) => (
          <FileTreeNode key={file.id} node={file} depth={0} />
        ))}
      </div>
    </div>
  );
};

export default FileBrowser;