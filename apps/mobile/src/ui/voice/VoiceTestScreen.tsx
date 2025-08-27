import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
  Dimensions,
} from 'react-native';
import { voiceService, STTResult } from '../services/voice_service';

const { width } = Dimensions.get('window');

interface VoiceTestScreenProps {
  navigation?: any;
}

export const VoiceTestScreen: React.FC<VoiceTestScreenProps> = ({ navigation }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [transcription, setTranscription] = useState('');
  const [partialTranscription, setPartialTranscription] = useState('');
  const [volume, setVolume] = useState(0);
  const [isAvailable, setIsAvailable] = useState(false);
  const [supportedLocales, setSupportedLocales] = useState<string[]>([]);
  const [selectedLocale, setSelectedLocale] = useState('en-US');
  const [transcriptionHistory, setTranscriptionHistory] = useState<string[]>([]);

  // Initialize voice service and check availability
  useEffect(() => {
    const initializeVoice = async () => {
      try {
        const available = await voiceService.isAvailable();
        setIsAvailable(available);

        if (available) {
          const locales = await voiceService.getSupportedLocales();
          setSupportedLocales(locales);
        }
      } catch (error) {
        console.error('Failed to initialize voice service:', error);
        Alert.alert('Error', 'Failed to initialize voice recognition');
      }
    };

    initializeVoice();
  }, []);

  // Set up voice event listeners
  useEffect(() => {
    const cleanupCallbacks: (() => void)[] = [];

    // Final transcription
    const onTranscription = voiceService.onTranscription((result: STTResult) => {
      setTranscription(result.text);
      setPartialTranscription('');
      setTranscriptionHistory(prev => [...prev, result.text]);
      setIsRecording(false);
    });
    cleanupCallbacks.push(onTranscription);

    // Partial transcription (real-time)
    const onPartialTranscription = voiceService.onPartialTranscription((result: STTResult) => {
      setPartialTranscription(result.text);
    });
    cleanupCallbacks.push(onPartialTranscription);

    // Error handling
    const onError = voiceService.onError((error) => {
      console.error('Voice recognition error:', error);
      Alert.alert('Voice Error', error.message || 'An error occurred during voice recognition');
      setIsRecording(false);
      setPartialTranscription('');
    });
    cleanupCallbacks.push(onError);

    // Recording state changes
    const onStart = voiceService.onStart(() => {
      setIsRecording(true);
      setTranscription('');
      setPartialTranscription('');
    });
    cleanupCallbacks.push(onStart);

    const onStop = voiceService.onStop(() => {
      setIsRecording(false);
      setPartialTranscription('');
    });
    cleanupCallbacks.push(onStop);

    // Volume level for visual feedback
    const onVolumeChanged = voiceService.onVolumeChanged((volumeLevel: number) => {
      setVolume(volumeLevel);
    });
    cleanupCallbacks.push(onVolumeChanged);

    // Cleanup on unmount
    return () => {
      cleanupCallbacks.forEach(cleanup => cleanup());
    };
  }, []);

  const startRecording = useCallback(async () => {
    if (!isAvailable) {
      Alert.alert('Error', 'Voice recognition is not available on this device');
      return;
    }

    try {
      await voiceService.startListening(selectedLocale);
    } catch (error) {
      console.error('Failed to start recording:', error);
      Alert.alert('Error', 'Failed to start voice recording');
    }
  }, [isAvailable, selectedLocale]);

  const stopRecording = useCallback(async () => {
    try {
      await voiceService.stopListening();
    } catch (error) {
      console.error('Failed to stop recording:', error);
      Alert.alert('Error', 'Failed to stop voice recording');
    }
  }, []);

  const cancelRecording = useCallback(async () => {
    try {
      await voiceService.cancelListening();
      setPartialTranscription('');
      setIsRecording(false);
    } catch (error) {
      console.error('Failed to cancel recording:', error);
      Alert.alert('Error', 'Failed to cancel voice recording');
    }
  }, []);

  const clearHistory = useCallback(() => {
    setTranscriptionHistory([]);
    setTranscription('');
    setPartialTranscription('');
  }, []);

  const renderVolumeIndicator = () => {
    const volumeWidth = Math.max(10, volume * width * 0.8);
    return (
      <View style={styles.volumeContainer}>
        <Text style={styles.volumeLabel}>Volume:</Text>
        <View style={styles.volumeBar}>
          <View style={[styles.volumeLevel, { width: volumeWidth }]} />
        </View>
      </View>
    );
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <Text style={styles.title}>Voice Recognition Test</Text>
      
      {/* Availability Status */}
      <View style={styles.statusContainer}>
        <Text style={styles.statusLabel}>Status:</Text>
        <Text style={[styles.statusText, { color: isAvailable ? '#4CAF50' : '#F44336' }]}>
          {isAvailable ? 'Available' : 'Not Available'}
        </Text>
      </View>

      {/* Locale Selection */}
      {supportedLocales.length > 0 && (
        <View style={styles.localeContainer}>
          <Text style={styles.localeLabel}>Language: {selectedLocale}</Text>
          <Text style={styles.localeNote}>
            Supported: {supportedLocales.slice(0, 3).join(', ')}
            {supportedLocales.length > 3 && '...'}
          </Text>
        </View>
      )}

      {/* Recording Controls */}
      <View style={styles.controlsContainer}>
        <TouchableOpacity
          style={[styles.button, styles.startButton, !isAvailable && styles.disabledButton]}
          onPress={startRecording}
          disabled={!isAvailable || isRecording}
        >
          <Text style={styles.buttonText}>Start Recording</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, styles.stopButton, !isRecording && styles.disabledButton]}
          onPress={stopRecording}
          disabled={!isRecording}
        >
          <Text style={styles.buttonText}>Stop</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, styles.cancelButton, !isRecording && styles.disabledButton]}
          onPress={cancelRecording}
          disabled={!isRecording}
        >
          <Text style={styles.buttonText}>Cancel</Text>
        </TouchableOpacity>
      </View>

      {/* Recording Indicator */}
      {isRecording && (
        <View style={styles.recordingIndicator}>
          <View style={styles.recordingDot} />
          <Text style={styles.recordingText}>Recording...</Text>
        </View>
      )}

      {/* Volume Indicator */}
      {isRecording && renderVolumeIndicator()}

      {/* Partial Transcription (Real-time) */}
      {partialTranscription && (
        <View style={styles.transcriptionContainer}>
          <Text style={styles.transcriptionLabel}>Partial (Real-time):</Text>
          <Text style={styles.partialTranscription}>{partialTranscription}</Text>
        </View>
      )}

      {/* Final Transcription */}
      {transcription && (
        <View style={styles.transcriptionContainer}>
          <Text style={styles.transcriptionLabel}>Final Result:</Text>
          <Text style={styles.transcription}>{transcription}</Text>
        </View>
      )}

      {/* Transcription History */}
      {transcriptionHistory.length > 0 && (
        <View style={styles.historyContainer}>
          <View style={styles.historyHeader}>
            <Text style={styles.historyLabel}>History ({transcriptionHistory.length}):</Text>
            <TouchableOpacity onPress={clearHistory} style={styles.clearButton}>
              <Text style={styles.clearButtonText}>Clear</Text>
            </TouchableOpacity>
          </View>
          {transcriptionHistory.map((item, index) => (
            <View key={index} style={styles.historyItem}>
              <Text style={styles.historyIndex}>{index + 1}.</Text>
              <Text style={styles.historyText}>{item}</Text>
            </View>
          ))}
        </View>
      )}

      {/* Instructions */}
      <View style={styles.instructionsContainer}>
        <Text style={styles.instructionsTitle}>Instructions:</Text>
        <Text style={styles.instructionsText}>
          1. Tap "Start Recording" to begin voice recognition{'\n'}
          2. Speak clearly into your device's microphone{'\n'}
          3. Watch the real-time transcription appear{'\n'}
          4. Tap "Stop" when finished, or "Cancel" to discard{'\n'}
          5. Final transcription will appear below
        </Text>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  contentContainer: {
    padding: 20,
    paddingBottom: 40,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 20,
    color: '#333',
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
    padding: 10,
    backgroundColor: '#fff',
    borderRadius: 8,
  },
  statusLabel: {
    fontSize: 16,
    fontWeight: '600',
    marginRight: 10,
    color: '#333',
  },
  statusText: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  localeContainer: {
    marginBottom: 15,
    padding: 10,
    backgroundColor: '#fff',
    borderRadius: 8,
  },
  localeLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 5,
  },
  localeNote: {
    fontSize: 14,
    color: '#666',
  },
  controlsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 20,
  },
  button: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 8,
    minWidth: 80,
    alignItems: 'center',
  },
  startButton: {
    backgroundColor: '#4CAF50',
  },
  stopButton: {
    backgroundColor: '#2196F3',
  },
  cancelButton: {
    backgroundColor: '#FF9800',
  },
  disabledButton: {
    backgroundColor: '#ccc',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  recordingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 15,
    padding: 10,
    backgroundColor: '#ffebee',
    borderRadius: 8,
  },
  recordingDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#f44336',
    marginRight: 10,
  },
  recordingText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#f44336',
  },
  volumeContainer: {
    marginBottom: 15,
    padding: 10,
    backgroundColor: '#fff',
    borderRadius: 8,
  },
  volumeLabel: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 5,
    color: '#333',
  },
  volumeBar: {
    height: 8,
    backgroundColor: '#e0e0e0',
    borderRadius: 4,
    overflow: 'hidden',
  },
  volumeLevel: {
    height: '100%',
    backgroundColor: '#4CAF50',
    borderRadius: 4,
  },
  transcriptionContainer: {
    marginBottom: 15,
    padding: 15,
    backgroundColor: '#fff',
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#2196F3',
  },
  transcriptionLabel: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
    color: '#333',
  },
  transcription: {
    fontSize: 16,
    lineHeight: 24,
    color: '#333',
  },
  partialTranscription: {
    fontSize: 16,
    lineHeight: 24,
    color: '#666',
    fontStyle: 'italic',
  },
  historyContainer: {
    marginBottom: 20,
    padding: 15,
    backgroundColor: '#fff',
    borderRadius: 8,
  },
  historyHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  historyLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  clearButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#f44336',
    borderRadius: 4,
  },
  clearButtonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  historyItem: {
    flexDirection: 'row',
    marginBottom: 8,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  historyIndex: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
    marginRight: 8,
    minWidth: 20,
  },
  historyText: {
    fontSize: 14,
    flex: 1,
    color: '#333',
  },
  instructionsContainer: {
    padding: 15,
    backgroundColor: '#e3f2fd',
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#2196F3',
  },
  instructionsTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
    color: '#1976d2',
  },
  instructionsText: {
    fontSize: 14,
    lineHeight: 20,
    color: '#1976d2',
  },
});

export default VoiceTestScreen;
export interface STTResult {
  text: string;
  confidence: number;
  isFinal: boolean;
  timestamp: number;
}

export interface VoiceService {
  startListening(): Promise<void>;
  stopListening(): Promise<void>;
  isListening(): boolean;
  onResult(callback: (result: STTResult) => void): void;
  onError(callback: (error: Error) => void): void;
}

class VoiceServiceImpl implements VoiceService {
  private listening = false;
  private resultCallback?: (result: STTResult) => void;
  private errorCallback?: (error: Error) => void;

  async startListening(): Promise<void> {
    this.listening = true;
    // TODO: Implement native voice recognition
  }

  async stopListening(): Promise<void> {
    this.listening = false;
  }

  isListening(): boolean {
    return this.listening;
  }

  onResult(callback: (result: STTResult) => void): void {
    this.resultCallback = callback;
  }

  onError(callback: (error: Error) => void): void {
    this.errorCallback = callback;
  }
}

export const voiceService = new VoiceServiceImpl();
