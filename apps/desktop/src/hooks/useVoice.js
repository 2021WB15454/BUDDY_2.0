import { useState, useEffect, useCallback, useRef } from 'react';

export const useVoice = () => {
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState(null);
  const [hasPermission, setHasPermission] = useState(false);
  const recognitionRef = useRef(null);

  // Check if voice is supported and permissions
  useEffect(() => {
    const checkSupport = async () => {
      try {
        // Check Web Speech API support
        const speechSupported = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
        
        if (speechSupported) {
          setIsSupported(true);
          
          // Check microphone permissions
          try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            setHasPermission(true);
            // Close the stream since we just needed to check permissions
            stream.getTracks().forEach(track => track.stop());
          } catch (permError) {
            console.warn('Microphone permission denied:', permError);
            setHasPermission(false);
            setError('Microphone permission required. Please allow microphone access in your browser settings.');
          }
        } else {
          setIsSupported(false);
          setError('Speech recognition not supported in this browser. Try Chrome or Edge.');
        }
      } catch (err) {
        setIsSupported(false);
        setError(`Voice recognition error: ${err.message}`);
        console.error('Voice recognition check failed:', err);
      }
    };

    checkSupport();
  }, []);

  // Start listening
  const startListening = useCallback(async () => {
    if (!isSupported) {
      setError('Voice recognition not supported in this browser');
      return false;
    }

    if (!hasPermission) {
      // Try to request permission again
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        setHasPermission(true);
        stream.getTracks().forEach(track => track.stop());
      } catch (permError) {
        setError('Microphone permission denied. Please allow microphone access and try again.');
        return false;
      }
    }

    try {
      setError(null);
      
      // Use Web Speech API
      return startWebSpeechRecognition();
    } catch (err) {
      setError(`Failed to start listening: ${err.message}`);
      setIsListening(false);
      return false;
    }
  }, [isSupported, hasPermission]);

  // Stop listening
  const stopListening = useCallback(async () => {
    try {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
        recognitionRef.current = null;
      }
      setIsListening(false);
      return true;
    } catch (err) {
      setError(`Failed to stop listening: ${err.message}`);
      return false;
    }
  }, []);

  // Web Speech API implementation
  const startWebSpeechRecognition = useCallback(() => {
    const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      console.log('Speech recognition started');
      setIsListening(true);
      setError(null);
    };

    recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      // Update transcript with final result, or interim if no final result yet
      const currentTranscript = finalTranscript || interimTranscript;
      setTranscript(currentTranscript);
      
      console.log('Speech recognition result:', currentTranscript);
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      let errorMessage;
      
      switch (event.error) {
        case 'no-speech':
          errorMessage = 'No speech detected. Please try speaking again.';
          break;
        case 'audio-capture':
          errorMessage = 'Microphone not found or accessible. Please check your microphone connection.';
          break;
        case 'not-allowed':
          errorMessage = 'Microphone permission denied. Please allow microphone access.';
          setHasPermission(false);
          break;
        case 'network':
          errorMessage = 'Network error during speech recognition.';
          break;
        case 'aborted':
          errorMessage = 'Speech recognition was aborted.';
          break;
        default:
          errorMessage = `Speech recognition error: ${event.error}`;
      }
      
      setError(errorMessage);
      setIsListening(false);
    };

    recognition.onend = () => {
      console.log('Speech recognition ended');
      setIsListening(false);
      recognitionRef.current = null;
    };

    try {
      recognition.start();
      recognitionRef.current = recognition;
      return true;
    } catch (error) {
      console.error('Failed to start speech recognition:', error);
      setError('Failed to start speech recognition. Please try again.');
      return false;
    }
  }, []);

  // Clear transcript
  const clearTranscript = useCallback(() => {
    setTranscript('');
    setError(null);
  }, []);

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    isListening,
    isSupported,
    hasPermission,
    transcript,
    error,
    startListening,
    stopListening,
    clearTranscript,
    clearError
  };
};
