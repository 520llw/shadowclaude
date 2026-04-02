import { create } from 'zustand';
import type { FileNode, Message, ToolCall, Agent, WorkspaceState } from '@types/index';

interface AppState {
  // File System
  files: FileNode[];
  activeFile: FileNode | null;
  openFiles: FileNode[];
  setFiles: (files: FileNode[]) => void;
  setActiveFile: (file: FileNode | null) => void;
  openFile: (file: FileNode) => void;
  closeFile: (fileId: string) => void;
  toggleFolder: (folderId: string) => void;
  
  // Messages
  messages: Message[];
  addMessage: (message: Message) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  clearMessages: () => void;
  
  // Tool Calls
  toolCalls: ToolCall[];
  addToolCall: (toolCall: ToolCall) => void;
  updateToolCall: (id: string, updates: Partial<ToolCall>) => void;
  
  // Agents
  agents: Agent[];
  updateAgent: (agent: Agent) => void;
  removeAgent: (agentId: string) => void;
  
  // UI State
  sidebarVisible: boolean;
  terminalVisible: boolean;
  agentPanelVisible: boolean;
  toggleSidebar: () => void;
  toggleTerminal: () => void;
  toggleAgentPanel: () => void;
  
  // Workspace
  workspace: WorkspaceState;
  updateWorkspace: (updates: Partial<WorkspaceState>) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // File System
  files: [],
  activeFile: null,
  openFiles: [],
  setFiles: (files) => set({ files }),
  setActiveFile: (file) => set({ activeFile: file }),
  openFile: (file) => set((state) => {
    if (file.type === 'directory') return state;
    const alreadyOpen = state.openFiles.find(f => f.id === file.id);
    if (!alreadyOpen) {
      return { openFiles: [...state.openFiles, file], activeFile: file };
    }
    return { activeFile: file };
  }),
  closeFile: (fileId) => set((state) => {
    const newOpenFiles = state.openFiles.filter(f => f.id !== fileId);
    const newActiveFile = state.activeFile?.id === fileId
      ? newOpenFiles[newOpenFiles.length - 1] || null
      : state.activeFile;
    return { openFiles: newOpenFiles, activeFile: newActiveFile };
  }),
  toggleFolder: (folderId) => set((state) => ({
    files: toggleFolderRecursive(state.files, folderId)
  })),

  // Messages
  messages: [],
  addMessage: (message) => set((state) => ({ 
    messages: [...state.messages, message] 
  })),
  updateMessage: (id, updates) => set((state) => ({
    messages: state.messages.map(m => m.id === id ? { ...m, ...updates } : m)
  })),
  clearMessages: () => set({ messages: [] }),

  // Tool Calls
  toolCalls: [],
  addToolCall: (toolCall) => set((state) => ({
    toolCalls: [...state.toolCalls, toolCall]
  })),
  updateToolCall: (id, updates) => set((state) => ({
    toolCalls: state.toolCalls.map(t => t.id === id ? { ...t, ...updates } : t)
  })),

  // Agents
  agents: [],
  updateAgent: (agent) => set((state) => {
    const exists = state.agents.find(a => a.id === agent.id);
    if (exists) {
      return {
        agents: state.agents.map(a => a.id === agent.id ? { ...a, ...agent } : a)
      };
    }
    return { agents: [...state.agents, agent] };
  }),
  removeAgent: (agentId) => set((state) => ({
    agents: state.agents.filter(a => a.id !== agentId)
  })),

  // UI State
  sidebarVisible: true,
  terminalVisible: true,
  agentPanelVisible: true,
  toggleSidebar: () => set((state) => ({ sidebarVisible: !state.sidebarVisible })),
  toggleTerminal: () => set((state) => ({ terminalVisible: !state.terminalVisible })),
  toggleAgentPanel: () => set((state) => ({ agentPanelVisible: !state.agentPanelVisible })),

  // Workspace
  workspace: {
    activeFile: null,
    openFiles: [],
    selectedAgent: null,
    sidebarVisible: true,
    terminalVisible: true,
    agentPanelVisible: true,
  },
  updateWorkspace: (updates) => set((state) => ({
    workspace: { ...state.workspace, ...updates }
  })),
}));

function toggleFolderRecursive(files: FileNode[], folderId: string): FileNode[] {
  return files.map(file => {
    if (file.id === folderId) {
      return { ...file, isOpen: !file.isOpen };
    }
    if (file.children) {
      return { ...file, children: toggleFolderRecursive(file.children, folderId) };
    }
    return file;
  });
}