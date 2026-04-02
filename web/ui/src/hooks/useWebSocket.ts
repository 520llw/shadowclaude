import { useEffect, useRef, useCallback } from 'react';
import ReconnectingWebSocket from 'reconnecting-websocket';
import { useAppStore } from '@stores/appStore';
import type { WebSocketMessage } from '@types/index';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080/ws';

export function useWebSocket() {
  const wsRef = useRef<ReconnectingWebSocket | null>(null);
  const addMessage = useAppStore((state) => state.addMessage);
  const addToolCall = useAppStore((state) => state.addToolCall);
  const updateToolCall = useAppStore((state) => state.updateToolCall);
  const updateAgent = useAppStore((state) => state.updateAgent);
  const setFiles = useAppStore((state) => state.setFiles);

  useEffect(() => {
    const ws = new ReconnectingWebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data);
        handleMessage(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    return () => {
      ws.close();
    };
  }, []);

  const handleMessage = useCallback((data: WebSocketMessage) => {
    switch (data.type) {
      case 'message':
        addMessage(data.payload);
        break;
      case 'tool_call':
        addToolCall(data.payload);
        break;
      case 'agent_update':
        updateAgent(data.payload);
        break;
      case 'file_change':
        // Refresh file tree
        break;
      case 'terminal_output':
        // Handle terminal output
        break;
    }
  }, [addMessage, addToolCall, updateAgent]);

  const sendMessage = useCallback((message: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  const sendChatMessage = useCallback((content: string) => {
    sendMessage({
      type: 'chat',
      payload: { content, timestamp: Date.now() }
    });
  }, [sendMessage]);

  const sendCommand = useCallback((command: string) => {
    sendMessage({
      type: 'command',
      payload: { command, timestamp: Date.now() }
    });
  }, [sendMessage]);

  return {
    sendMessage,
    sendChatMessage,
    sendCommand,
  };
}