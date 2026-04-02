import React, { useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Sparkles, Wrench } from 'lucide-react';
import { useAppStore } from '@stores/appStore';
import { useWebSocket } from '@hooks/useWebSocket';
import type { Message } from '@types/index';

const MessageBubble: React.FC<{ message: Message }> = ({ message }) => {
  const isUser = message.role === 'user';
  const isTool = message.role === 'tool';

  return (
    <div
      className={`
        flex gap-4 px-4 py-6 
        ${isUser ? 'bg-transparent' : 'bg-shadow-800/50'}
      `}
    >
      {/* Avatar */}
      <div className="flex-shrink-0">
        {isUser ? (
          <div className="w-8 h-8 rounded-full bg-accent-green/20 flex items-center justify-center">
            <User className="w-5 h-5 text-accent-green" />
          </div>
        ) : isTool ? (
          <div className="w-8 h-8 rounded-full bg-accent-purple/20 flex items-center justify-center">
            <Wrench className="w-5 h-5 text-accent-purple" />
          </div>
        ) : (
          <div className="w-8 h-8 rounded-full bg-accent-blue/20 flex items-center justify-center">
            <Bot className="w-5 h-5 text-accent-blue" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-semibold text-sm">
            {isUser ? 'You' : isTool ? 'Tool' : 'ShadowClaude'}
          </span>
          <span className="text-xs text-shadow-400">
            {new Date(message.timestamp).toLocaleTimeString()}
          </span>
        </div>
        
        <div className="prose prose-invert prose-sm max-w-none">
          {message.metadata?.thinking && (
            <div className="mb-3 p-3 bg-shadow-700/50 rounded-lg border border-shadow-600">
              <div className="flex items-center gap-2 text-accent-yellow mb-2">
                <Sparkles className="w-4 h-4" />
                <span className="text-xs font-medium">Thinking</span>
              </div>
              <div className="text-sm text-shadow-300 italic">
                {message.metadata.thinking}
              </div>
            </div>
          )}
          
          <div className="whitespace-pre-wrap">{message.content}</div>
        </div>

        {message.metadata?.toolCall && (
          <div className="mt-3 p-3 bg-accent-purple/10 rounded-lg border border-accent-purple/30">
            <div className="flex items-center gap-2 text-accent-purple mb-2">
              <Wrench className="w-4 h-4" />
              <span className="text-xs font-medium">Tool Call</span>
            </div>
            <div className="text-sm font-mono text-shadow-200">
              {message.metadata.toolCall.name}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export const Chat: React.FC = () => {
  const messages = useAppStore((state) => state.messages);
  const addMessage = useAppStore((state) => state.addMessage);
  const { sendChatMessage } = useWebSocket();
  const [input, setInput] = React.useState('');
  const [isTyping, setIsTyping] = React.useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input,
      timestamp: Date.now(),
    };

    addMessage(userMessage);
    sendChatMessage(input);
    setInput('');
    setIsTyping(true);

    // Simulate response for demo
    setTimeout(() => {
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `I received your message: "${userMessage.content}"\n\nThis is a demo response. In the actual implementation, this would be connected to the ShadowClaude backend through WebSocket.`,
        timestamp: Date.now(),
        metadata: {
          thinking: 'Analyzing user input and preparing response...',
        },
      };
      addMessage(assistantMessage);
      setIsTyping(false);
    }, 1500);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="h-full flex flex-col bg-shadow-900">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-shadow-600 bg-shadow-800">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-accent-blue" />
          <span className="font-semibold">ShadowClaude</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-shadow-400">
          <span className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
          Connected
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-accent-blue/10 flex items-center justify-center">
                <Bot className="w-8 h-8 text-accent-blue" />
              </div>
              <h2 className="text-xl font-semibold mb-2">Welcome to ShadowClaude</h2>
              <p className="text-shadow-400">
                I'm your AI coding assistant. Ask me to write code, explain concepts, 
                or help you debug. I can also spawn subagents to work on complex tasks in parallel.
              </p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isTyping && (
              <div className="flex gap-4 px-4 py-6">
                <div className="w-8 h-8 rounded-full bg-accent-blue/20 flex items-center justify-center">
                  <Bot className="w-5 h-5 text-accent-blue" />
                </div>
                <div className="flex items-center gap-1">
                  <Loader2 className="w-4 h-4 animate-spin text-accent-blue" />
                  <span className="text-sm text-shadow-400">ShadowClaude is thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-shadow-600 bg-shadow-800">
        <form onSubmit={handleSubmit} className="relative">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message ShadowClaude... (Shift+Enter for new line)"
            className="w-full px-4 py-3 pr-12 bg-shadow-700 border border-shadow-600 rounded-lg 
                       text-shadow-100 placeholder-shadow-400 resize-none
                       focus:outline-none focus:border-accent-blue focus:ring-1 focus:ring-accent-blue"
            rows={3}
          />
          <button
            type="submit"
            disabled={!input.trim()}
            className="absolute right-3 bottom-3 p-2 rounded-md
                       bg-accent-blue text-shadow-900
                       disabled:opacity-50 disabled:cursor-not-allowed
                       hover:bg-accent-blue/90 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
        <p className="mt-2 text-xs text-center text-shadow-500">
          ShadowClaude can make mistakes. Consider checking important information.
        </p>
      </div>
    </div>
  );
};

export default Chat;