export interface FileNode {
  id: string;
  name: string;
  type: 'file' | 'directory';
  path: string;
  children?: FileNode[];
  isOpen?: boolean;
  language?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: number;
  metadata?: {
    toolCall?: ToolCall;
    thinking?: string;
    fileReferences?: string[];
  };
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: unknown;
  duration?: number;
}

export interface Agent {
  id: string;
  name: string;
  status: 'idle' | 'working' | 'waiting' | 'error';
  currentTask?: string;
  progress?: number;
  lastActivity?: number;
  type: 'main' | 'subagent' | 'tool' | 'swarm';
}

export interface TerminalLine {
  id: string;
  type: 'input' | 'output' | 'error' | 'system';
  content: string;
  timestamp: number;
}

export interface WorkspaceState {
  activeFile: FileNode | null;
  openFiles: FileNode[];
  selectedAgent: string | null;
  sidebarVisible: boolean;
  terminalVisible: boolean;
  agentPanelVisible: boolean;
}

export type WebSocketMessage =
  | { type: 'message'; payload: Message }
  | { type: 'tool_call'; payload: ToolCall }
  | { type: 'agent_update'; payload: Agent }
  | { type: 'file_change'; payload: FileNode }
  | { type: 'terminal_output'; payload: TerminalLine };