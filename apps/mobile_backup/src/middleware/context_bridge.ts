export interface ContextSnapshot {
  recentMessages: string[];
  driving?: boolean;
  speedKmh?: number;
  location?: any;
}

class ContextBridge {
  private cache: ContextSnapshot = { recentMessages: [] };

  appendMessage(text: string) {
    this.cache.recentMessages.unshift(text);
    this.cache.recentMessages = this.cache.recentMessages.slice(0, 20);
  }

  setDriving(speedKmh: number) {
    this.cache.speedKmh = speedKmh;
    this.cache.driving = speedKmh > 5;
  }

  snapshot(): ContextSnapshot { return { ...this.cache }; }
}

export const contextBridge = new ContextBridge();
