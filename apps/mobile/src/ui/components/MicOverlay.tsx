import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

export interface MicOverlayProps { onPressIn(): void; onPressOut(): void; recording: boolean; }

export const MicOverlay: React.FC<MicOverlayProps> = ({ onPressIn, onPressOut, recording }) => (
  <View style={styles.container} pointerEvents="box-none">
    <TouchableOpacity
      accessibilityLabel="Push to talk"
      onPressIn={onPressIn}
      onPressOut={onPressOut}
      style={[styles.button, recording && styles.active]}
    >
      <Text style={styles.text}>{recording ? '●' : '🎤'}</Text>
    </TouchableOpacity>
  </View>
);

const styles = StyleSheet.create({
  container: { position: 'absolute', bottom: 40, right: 24 },
  button: { backgroundColor: '#263238', width: 56, height: 56, borderRadius: 28, alignItems: 'center', justifyContent: 'center' },
  active: { backgroundColor: '#d32f2f' },
  text: { color: '#fff', fontSize: 24 }
});
