import { SafetyAlert } from '../types';

type MessageListener = (event: { type: string; data: unknown }) => void;

class WebSocketFleetService {
  private ws: WebSocket | null = null;
  private listeners: Set<MessageListener> = new Set();
  private reconnectInterval: number | null = null;
  private isConnected: boolean = false;

  constructor() {
    this.connect();
  }

  public connect() {
    if (typeof window === 'undefined') return;

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws`;

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.isConnected = true;
        this.notifyListeners({ type: 'connection.status', data: { connected: true, liveServer: true } });
      };

      this.ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          this.notifyListeners(parsed);
        } catch {
          // ignore non-json
        }
      };

      this.ws.onerror = () => {
        this.ws?.close();
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        this.notifyListeners({ type: 'connection.status', data: { connected: false, liveServer: false } });
        this.scheduleReconnect();
      };
    } catch {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectInterval) return;
    this.reconnectInterval = window.setInterval(() => {
      if (!this.isConnected) {
        this.connect();
      } else {
        if (this.reconnectInterval) {
          clearInterval(this.reconnectInterval);
          this.reconnectInterval = null;
        }
      }
    }, 10000);
  }

  public subscribe(listener: MessageListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  public notifyListeners(event: { type: string; data: unknown }) {
    this.listeners.forEach(fn => {
      try {
        fn(event);
      } catch (e) {
        console.error('WebSocket subscriber error', e);
      }
    });
  }

  /** Local UI-only alert hook for edge controls; production alerts arrive from `/ws`. */
  public triggerLocalAlert(alert: SafetyAlert) {
    this.notifyListeners({ type: 'alert.received', data: alert });
  }

  public isLive(): boolean {
    return this.isConnected;
  }
}

export const wsService = new WebSocketFleetService();
