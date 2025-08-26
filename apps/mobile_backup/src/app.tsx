import React from 'react';
import { SafeAreaView, StatusBar } from 'react-native';
import { ChatScreen } from './ui/chat/ChatScreen';

export const App = () => (
  <SafeAreaView style={{ flex: 1 }}>
    <StatusBar barStyle="light-content" />
    <ChatScreen />
  </SafeAreaView>
);

export default App;
