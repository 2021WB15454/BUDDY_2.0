import React, { useState } from 'react';
import { View, Text, TextInput, Button, FlatList } from 'react-native';
import { sendChat } from '@services/rest_api';
import { wsService } from '@services/websocket';
import { contextBridge } from '@middleware/context_bridge';
import { bridgeRegistry } from '@middleware/bridge_registry';
import '../..//middleware/nlp_bridge'; // ensure registration

interface Message { id: string; role: string; text: string; }

export const ChatScreen: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  // Use dynamic config base
  const { API_BASE } = require('../../config');
  const baseUrl = API_BASE;

  React.useEffect(() => {
    wsService.connect();
    let streamingId: string | null = null;
    let buffer = '';
    const onMsg = (msg: any) => {
      if (msg?.type === 'start') {
        streamingId = Date.now()+':s';
        buffer = '';
        setMessages((m: Message[]) => [{ id: streamingId!, role: 'assistant', text: '' }, ...m]);
      } else if (msg?.type === 'token' && streamingId) {
        buffer += msg.token || '';
        setMessages((m: Message[]) => m.map(mm => mm.id === streamingId ? { ...mm, text: buffer } : mm));
      } else if (msg?.type === 'end' && streamingId) {
        setMessages((m: Message[]) => m.map(mm => mm.id === streamingId ? { ...mm, text: buffer.trim() } : mm));
        streamingId = null; buffer='';
      } else if (msg?.response) {
        const botMsg: Message = { id: Date.now()+':a', role: 'assistant', text: String(msg.response) };
        setMessages((m: Message[]) => [botMsg, ...m]);
      } else if (msg?.error) {
        setMessages((m: Message[]) => [{ id: Date.now()+':e', role: 'assistant', text: 'WS Error: '+ msg.error }, ...m]);
      }
    };
  wsService.onMessage(onMsg as any);
  return () => { wsService.offMessage(onMsg as any); wsService.close(); };
  }, []);

  async function onSend() {
    if (!input.trim()) return;
    const userMsg: Message = { id: Date.now()+':u', role: 'user', text: input };
  setMessages((m: Message[]) => [userMsg, ...m]);
    contextBridge.appendMessage(input);
    try {
  const nlp = await bridgeRegistry.invoke<any, any>('nlp.detect', { text: input, context: contextBridge.snapshot() });
      if (nlp.blocked) {
        const blocked: Message = { id: Date.now()+':b', role: 'assistant', text: nlp.safety.message || 'Blocked' };
  setMessages((m: Message[]) => [blocked, ...m]);
        setInput('');
        return;
      }
      if (wsService.isOpen()) {
  wsService.sendChat(input); // TODO: add stream flag once backend expects it from client (currently default non-stream)
      } else {
        const resp: any = await sendChat(baseUrl, input);
        const botMsg: Message = { id: Date.now()+':a', role: 'assistant', text: String(resp.response) };
        setMessages((m: Message[]) => [botMsg, ...m]);
      }
    } catch (e: any) {
  setMessages((m: Message[]) => [{ id: Date.now()+':e', role: 'assistant', text: 'Error: '+ e.message }, ...m]);
    }
    setInput('');
  }

  return (
    <View style={{ flex: 1, backgroundColor: '#101317', padding: 12 }}>
      <View style={{ flexDirection: 'row', marginBottom: 8 }}>
        <TextInput
          value={input}
          onChangeText={setInput}
          style={{ flex: 1, backgroundColor: '#1e232b', color: '#fff', padding: 8, borderRadius: 6 }}
          placeholder="Type a message"
          placeholderTextColor="#556"
        />
        <Button title="Send" onPress={onSend} />
      </View>
      <FlatList
        data={messages}
        keyExtractor={(i: Message) => i.id}
        inverted
        renderItem={({ item }: { item: Message }) => (
          <View style={{ paddingVertical: 6 }}>
            <Text style={{ color: item.role === 'user' ? '#4fc3f7' : '#fff' }}>{item.role}: {item.text}</Text>
          </View>
        )}
      />
    </View>
  );
};
