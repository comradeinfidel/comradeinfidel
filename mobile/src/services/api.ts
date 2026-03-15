/**
 * WebSocket-based API service for the AI assistant backend.
 */

const WS_URL = __DEV__
  ? 'ws://localhost:8000/ws/chat'
  : 'wss://your-production-server.com/ws/chat';

export type StreamEvent =
  | { type: 'text_start' }
  | { type: 'text_delta'; text: string }
  | { type: 'thinking_start' }
  | { type: 'thinking_delta'; thinking: string }
  | { type: 'tool_start'; tool_name: string }
  | { type: 'tool_executing'; tool_name: string; tool_input: Record<string, unknown> }
  | { type: 'tool_result'; tool_name: string; result: Record<string, unknown> }
  | { type: 'done' }
  | { type: 'error'; message: string };

export type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
};

type EventCallback = (event: StreamEvent) => void;

class AssistantAPI {
  private ws: WebSocket | null = null;
  private onEvent: EventCallback | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private isConnected = false;
  private pendingMessages: string[] = [];

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(WS_URL);

    this.ws.onopen = () => {
      this.isConnected = true;
      // Flush any pending messages
      this.pendingMessages.forEach(msg => this.ws?.send(msg));
      this.pendingMessages = [];
    };

    this.ws.onmessage = (event) => {
      try {
        const parsed: StreamEvent = JSON.parse(event.data);
        this.onEvent?.(parsed);
      } catch {
        // Ignore parse errors
      }
    };

    this.ws.onclose = () => {
      this.isConnected = false;
      // Auto-reconnect after 2 seconds
      this.reconnectTimer = setTimeout(() => this.connect(), 2000);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
    this.isConnected = false;
  }

  sendMessage(messages: ChatMessage[], onEvent: EventCallback) {
    this.onEvent = onEvent;
    const payload = JSON.stringify({ messages });

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(payload);
    } else {
      this.pendingMessages.push(payload);
      this.connect();
    }
  }
}

export const assistantAPI = new AssistantAPI();
