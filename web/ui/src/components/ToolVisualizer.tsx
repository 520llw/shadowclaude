import React from 'react';
import { 
  Wrench, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Play, 
  ChevronDown, 
  ChevronRight,
  Terminal,
  Search,
  FileEdit,
  Globe,
  Code2,
  Database
} from 'lucide-react';
import { useAppStore } from '@stores/appStore';
import type { ToolCall } from '@types/index';

const getToolIcon = (toolName: string) => {
  const name = toolName.toLowerCase();
  if (name.includes('exec') || name.includes('bash') || name.includes('shell')) {
    return <Terminal className="w-4 h-4" />;
  }
  if (name.includes('read') || name.includes('write') || name.includes('file')) {
    return <FileEdit className="w-4 h-4" />;
  }
  if (name.includes('search') || name.includes('find')) {
    return <Search className="w-4 h-4" />;
  }
  if (name.includes('web') || name.includes('fetch') || name.includes('http')) {
    return <Globe className="w-4 h-4" />;
  }
  if (name.includes('code') || name.includes('edit')) {
    return <Code2 className="w-4 h-4" />;
  }
  if (name.includes('db') || name.includes('query')) {
    return <Database className="w-4 h-4" />;
  }
  return <Wrench className="w-4 h-4" />;
};

const getStatusIcon = (status: ToolCall['status']) => {
  switch (status) {
    case 'pending':
      return <Clock className="w-4 h-4 text-accent-yellow" />;
    case 'running':
      return <Play className="w-4 h-4 text-accent-blue animate-pulse" />;
    case 'completed':
      return <CheckCircle2 className="w-4 h-4 text-accent-green" />;
    case 'failed':
      return <XCircle className="w-4 h-4 text-accent-red" />;
  }
};

const getStatusColor = (status: ToolCall['status']) => {
  switch (status) {
    case 'pending':
      return 'text-accent-yellow border-accent-yellow/30 bg-accent-yellow/5';
    case 'running':
      return 'text-accent-blue border-accent-blue/30 bg-accent-blue/5';
    case 'completed':
      return 'text-accent-green border-accent-green/30 bg-accent-green/5';
    case 'failed':
      return 'text-accent-red border-accent-red/30 bg-accent-red/5';
  }
};

interface ToolCallCardProps {
  toolCall: ToolCall;
}

const ToolCallCard: React.FC<ToolCallCardProps> = ({ toolCall }) => {
  const [isExpanded, setIsExpanded] = React.useState(false);

  return (
    <div 
      className={`
        rounded-lg border overflow-hidden transition-all
        ${getStatusColor(toolCall.status)}
      `}
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-black/10 transition-colors"
      >
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 flex-shrink-0" />
        )}
        
        <div className="w-6 h-6 rounded-full bg-black/20 flex items-center justify-center">
          {getToolIcon(toolCall.name)}
        </div>
        
        <span className="font-medium text-sm flex-1 text-left">{toolCall.name}</span>
        
        <div className="flex items-center gap-2">
          {toolCall.duration && (
            <span className="text-xs opacity-70">{toolCall.duration}ms</span>
          )}
          {getStatusIcon(toolCall.status)}
        </div>
      </button>

      {/* Details */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-current/20">
          <div className="mt-3 space-y-3">
            <div>
              <p className="text-xs font-medium opacity-70 mb-1">Arguments</p>
              <pre className="p-3 rounded bg-black/20 text-xs overflow-x-auto">
                <code>{JSON.stringify(toolCall.arguments, null, 2)}</code>
              </pre>
            </div>

            {toolCall.result && (
              <div>
                <p className="text-xs font-medium opacity-70 mb-1">Result</p>
                <pre className="p-3 rounded bg-black/20 text-xs overflow-x-auto">
                  <code>{JSON.stringify(toolCall.result, null, 2)}</code>
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export const ToolVisualizer: React.FC = () => {
  const toolCalls = useAppStore((state) => state.toolCalls);
  const [filter, setFilter] = React.useState<ToolCall['status'] | 'all'>('all');

  const filteredTools = filter === 'all' 
    ? toolCalls 
    : toolCalls.filter(t => t.status === filter);

  const runningCount = toolCalls.filter(t => t.status === 'running').length;
  const completedCount = toolCalls.filter(t => t.status === 'completed').length;
  const failedCount = toolCalls.filter(t => t.status === 'failed').length;

  return (
    <div className="h-full flex flex-col bg-shadow-900">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-shadow-600 bg-shadow-800">
        <div className="flex items-center gap-2">
          <Wrench className="w-5 h-5 text-accent-purple" />
          <span className="font-semibold">Tool Calls</span>
        </div>

        <div className="flex items-center gap-2">
          {runningCount > 0 && (
            <span className="px-2 py-0.5 rounded-full text-xs bg-accent-blue/20 text-accent-blue">
              {runningCount} running
            </span>
          )}
          {completedCount > 0 && (
            <span className="px-2 py-0.5 rounded-full text-xs bg-accent-green/20 text-accent-green">
              {completedCount} completed
            </span>
          )}
          {failedCount > 0 && (
            <span className="px-2 py-0.5 rounded-full text-xs bg-accent-red/20 text-accent-red">
              {failedCount} failed
            </span>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-shadow-600">
        {(['all', 'running', 'completed', 'failed'] as const).map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`
              px-3 py-1 rounded text-xs font-medium capitalize transition-colors
              ${filter === status 
                ? 'bg-accent-blue/20 text-accent-blue' 
                : 'text-shadow-400 hover:text-shadow-200 hover:bg-shadow-700'
              }
            `}
          >
            {status}
          </button>
        ))}
      </div>

      {/* Tool List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {filteredTools.length === 0 ? (
          <div className="h-full flex items-center justify-center text-center">
            <div>
              <Wrench className="w-12 h-12 mx-auto mb-3 text-shadow-600" />
              <p className="text-shadow-400">
                {toolCalls.length === 0 
                  ? "No tool calls yet" 
                  : "No tools match the selected filter"
                }
              </p>
            </div>
          </div>
        ) : (
          filteredTools.map((toolCall) => (
            <ToolCallCard key={toolCall.id} toolCall={toolCall} />
          ))
        )}
      </div>
    </div>
  );
};

export default ToolVisualizer;