import EventEmitter from 'eventemitter3';
import { API_BASE, CLIENT_TOKEN } from '../config';

export interface ChatWSMessage { response?: string; error?: string; detail?: string; }

export class WebSocketService {
  private socket?: WebSocket;
  private ready = false;
  private emitter = new EventEmitter();
  constructor(private baseUrl: string) {}

  connect() {
    if (this.socket && this.ready) return;
  const url = this.baseUrl.replace(/^http/, 'ws') + `/ws/chat?token=${CLIENT_TOKEN}`;
    this.socket = new WebSocket(url);
  this.socket.onopen = () => { this.ready = true; this.emitter.emit('open'); };
    this.socket.onmessage = (e) => {
      try { this.emitter.emit('message', JSON.parse(e.data)); } catch { this.emitter.emit('message', { error: 'invalid_json' }); }
    };
    this.socket.onerror = (e) => this.emitter.emit('error', e as any);
    this.socket.onclose = () => { this.ready = false; this.emitter.emit('close'); };
  }

  isOpen() { return this.ready; }

  sendChat(message: string, userId = 'mobile_user', sessionId = 'mobile_session', stream: boolean = true) {
    if (!this.socket || !this.ready) throw new Error('ws_not_ready');
    this.socket.send(JSON.stringify({ message, user_id: userId, session_id: sessionId, stream }));
  }

  close() { this.socket?.close(); }

  // Typed convenience wrappers
  onMessage(fn: (m: ChatWSMessage) => void) { this.emitter.on('message', fn as any); }
  offMessage(fn: (m: ChatWSMessage) => void) { this.emitter.off('message', fn as any); }
}

export const wsService = new WebSocketService(API_BASE);
