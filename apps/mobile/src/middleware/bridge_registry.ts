import EventEmitter from 'eventemitter3';

export interface BridgeHandler<I, O> { (input: I): Promise<O>; }

class BridgeRegistry extends EventEmitter {
  private handlers: Record<string, BridgeHandler<any, any>> = {};

  register(name: string, handler: BridgeHandler<any, any>, override = false) {
    if (!override && this.handlers[name]) throw new Error(`Handler exists: ${name}`);
    this.handlers[name] = handler;
    this.emit('registered', name);
  }

  async invoke<TIn, TOut>(name: string, payload: TIn): Promise<TOut> {
    const h = this.handlers[name];
    if (!h) throw new Error(`No handler: ${name}`);
    return h(payload);
  }

  list(): string[] { return Object.keys(this.handlers); }
}

export const bridgeRegistry = new BridgeRegistry();
