import React from 'react';
import { 
  Bot, 
  Activity, 
  CheckCircle2, 
  AlertCircle, 
  Clock,
  Cpu,
  Layers,
  Settings,
  MoreHorizontal,
  Pause,
  Play,
  X
} from 'lucide-react';
import { useAppStore } from '@stores/appStore';
import type { Agent } from '@types/index';

const getAgentIcon = (type: Agent['type']) => {
  switch (type) {
    case 'main':
      return <Bot className="w-5 h-5" />;
    case 'subagent':
      return <Layers className="w-5 h-5" />;
    case 'tool':
      return <Settings className="w-5 h-5" />;
    case 'swarm':
      return <Cpu className="w-5 h-5" />;
  }
};

const getStatusIcon = (status: Agent['status']) => {
  switch (status) {
    case 'idle':
      return <Clock className="w-4 h-4 text-shadow-400" />;
    case 'working':
      return <Activity className="w-4 h-4 text-accent-blue animate-pulse" />;
    case 'waiting':
      return <Pause className="w-4 h-4 text-accent-yellow" />;
    case 'error':
      return <AlertCircle className="w-4 h-4 text-accent-red" />;
  }
};

const getStatusColor = (status: Agent['status']) => {
  switch (status) {
    case 'idle':
      return 'bg-shadow-600 text-shadow-300';
    case 'working':
      return 'bg-accent-blue/20 text-accent-blue border-accent-blue/30';
    case 'waiting':
      return 'bg-accent-yellow/20 text-accent-yellow border-accent-yellow/30';
    case 'error':
      return 'bg-accent-red/20 text-accent-red border-accent-red/30';
  }
};

const getTypeColor = (type: Agent['type']) => {
  switch (type) {
    case 'main':
      return 'text-accent-purple';
    case 'subagent':
      return 'text-accent-blue';
    case 'tool':
      return 'text-accent-green';
    case 'swarm':
      return 'text-accent-orange';
  }
};

interface AgentCardProps {
  agent: Agent;
}

const AgentCard: React.FC<AgentCardProps> = ({ agent }) => {
  const [showMenu, setShowMenu] = React.useState(false);

  return (
    <div 
      className={`
        relative rounded-lg border p-4 transition-all
        ${agent.status === 'working' 
          ? 'bg-accent-blue/5 border-accent-blue/30' 
          : 'bg-shadow-800 border-shadow-600 hover:border-shadow-500'
        }
      `}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`
            w-10 h-10 rounded-lg flex items-center justify-center
            ${getTypeColor(agent.type)}
            ${agent.status === 'working' ? 'bg-accent-blue/20 animate-pulse' : 'bg-shadow-700'}
          `}>
            {getAgentIcon(agent.type)}
          </div>
          
          <div>
            <h3 className="font-medium text-sm">{agent.name}</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`
                text-xs px-1.5 py-0.5 rounded border
                ${getStatusColor(agent.status)}
              `}>
                {agent.status}
              </span>
              <span className="text-xs text-shadow-400 capitalize">{agent.type}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {agent.status === 'working' && (
            <div className="w-24 h-1.5 bg-shadow-700 rounded-full overflow-hidden">
              <div 
                className="h-full bg-accent-blue transition-all duration-500"
                style={{ width: `${agent.progress || 0}%` }}
              />
            </div>
          )}
          
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-1.5 rounded hover:bg-shadow-700 text-shadow-400 transition-colors"
          >
            <MoreHorizontal className="w-4 h-4" />
          </button>
        </div>
      </div>

      {agent.currentTask && (
        <div className="mt-3 text-sm text-shadow-300">
          <span className="text-shadow-500">Task: </span>
          {agent.currentTask}
        </div>
      )}

      {agent.lastActivity && (
        <div className="mt-2 text-xs text-shadow-400">
          Last activity: {new Date(agent.lastActivity).toLocaleTimeString()}
        </div>
      )}

      {showMenu && (
        <>
          <div 
            className="fixed inset-0 z-40"
            onClick={() => setShowMenu(false)}
          />
          <div className="absolute right-2 top-10 z-50 min-w-[140px] bg-shadow-700 rounded-lg shadow-xl border border-shadow-600 py-1">
            <button className="w-full px-3 py-2 text-left text-sm hover:bg-shadow-600 flex items-center gap-2">
              <Pause className="w-4 h-4" /> Pause
            </button>
            <button className="w-full px-3 py-2 text-left text-sm hover:bg-shadow-600 flex items-center gap-2">
              <Play className="w-4 h-4" /> Resume
            </button>
            <div className="h-px bg-shadow-600 my-1" />
            <button className="w-full px-3 py-2 text-left text-sm hover:bg-shadow-600 text-accent-red flex items-center gap-2">
              <X className="w-4 h-4" /> Terminate
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export const AgentPanel: React.FC = () => {
  const agents = useAppStore((state) => state.agents);
  const updateAgent = useAppStore((state) => state.updateAgent);
  const [filter, setFilter] = React.useState<Agent['type'] | 'all'>('all');

  // Mock data for demonstration
  React.useEffect(() => {
    const mockAgents: Agent[] = [
      {
        id: 'main-1',
        name: 'Main Agent',
        status: 'working',
        type: 'main',
        currentTask: 'Processing user request',
        progress: 65,
        lastActivity: Date.now(),
      },
      {
        id: 'sub-1',
        name: 'Code Analyzer',
        status: 'idle',
        type: 'subagent',
        lastActivity: Date.now() - 30000,
      },
      {
        id: 'sub-2',
        name: 'File Searcher',
        status: 'working',
        type: 'subagent',
        currentTask: 'Searching for references',
        progress: 40,
        lastActivity: Date.now() - 5000,
      },
      {
        id: 'tool-1',
        name: 'Git Helper',
        status: 'waiting',
        type: 'tool',
        lastActivity: Date.now() - 60000,
      },
    ];
    
    mockAgents.forEach(agent => updateAgent(agent));
  }, [updateAgent]);

  const filteredAgents = filter === 'all'
    ? agents
    : agents.filter(a => a.type === filter);

  const activeCount = agents.filter(a => a.status === 'working').length;
  const idleCount = agents.filter(a => a.status === 'idle').length;

  return (
    <div className="h-full flex flex-col bg-shadow-900 border-l border-shadow-600">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-shadow-600 bg-shadow-800">
        <div className="flex items-center gap-2">
          <Cpu className="w-5 h-5 text-accent-orange" />
          <span className="font-semibold">Agent Swarm</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded-full text-xs bg-accent-blue/20 text-accent-blue">
            {activeCount} active
          </span>
          <span className="px-2 py-0.5 rounded-full text-xs bg-shadow-700 text-shadow-300">
            {idleCount} idle
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-shadow-600">
        {(['all', 'main', 'subagent', 'tool', 'swarm'] as const).map((type) => (
          <button
            key={type}
            onClick={() => setFilter(type)}
            className={`
              px-3 py-1 rounded text-xs font-medium capitalize transition-colors
              ${filter === type 
                ? 'bg-accent-orange/20 text-accent-orange' 
                : 'text-shadow-400 hover:text-shadow-200 hover:bg-shadow-700'
              }
            `}
          >
            {type}
          </button>
        ))}
      </div>

      {/* Agent List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {filteredAgents.length === 0 ? (
          <div className="h-full flex items-center justify-center text-center">
            <div>
              <Cpu className="w-12 h-12 mx-auto mb-3 text-shadow-600" />
              <p className="text-shadow-400">No agents running</p>
            </div>
          </div>
        ) : (
          filteredAgents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))
        )}
      </div>

      {/* Stats */}
      <div className="px-4 py-3 border-t border-shadow-600 bg-shadow-800">
        <div className="grid grid-cols-4 gap-2 text-center">
          <div className="p-2 rounded bg-shadow-700">
            <div className="text-lg font-semibold text-accent-blue">{activeCount}</div>
            <div className="text-xs text-shadow-400">Active</div>
          </div>
          <div className="p-2 rounded bg-shadow-700">
            <div className="text-lg font-semibold text-accent-green">{idleCount}</div>
            <div className="text-xs text-shadow-400">Idle</div>
          </div>
          <div className="p-2 rounded bg-shadow-700">
            <div className="text-lg font-semibold text-accent-yellow">{agents.filter(a => a.status === 'waiting').length}</div>
            <div className="text-xs text-shadow-400">Waiting</div>
          </div>
          <div className="p-2 rounded bg-shadow-700">
            <div className="text-lg font-semibold text-accent-red">{agents.filter(a => a.status === 'error').length}</div>
            <div className="text-xs text-shadow-400">Error</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentPanel;