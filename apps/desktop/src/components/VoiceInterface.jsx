import React from 'react';
import { Mic, MicOff, Volume2, AlertTriangle, Shield, RefreshCw } from 'lucide-react';

const VoiceInterface = ({
  isListening,
  isSupported,
  hasPermission,
  onStartListening,
  onStopListening,
  transcript,
  error,
  onSendMessage,
  onClearError
}) => {
  // Show permission request if needed
  if (isSupported && !hasPermission) {
    return (
      <div className="voice-interface">
        <div className="voice-permission-request">
          <Shield size={48} className="text-warning" />
          <h3>Microphone Permission Required</h3>
          <p>BUDDY needs access to your microphone to enable voice commands.</p>
          <div className="permission-actions">
            <button 
              className="btn btn-primary"
              onClick={onStartListening}
            >
              Grant Microphone Access
            </button>
          </div>
          <div className="permission-help">
            <h4>Troubleshooting:</h4>
            <ul>
              <li>Click the microphone icon in your browser's address bar</li>
              <li>Select "Always allow" for this site</li>
              <li>Refresh the page if needed</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  // Show not supported message
  if (!isSupported) {
    return (
      <div className="voice-interface">
        <div className="voice-not-supported">
          <AlertTriangle size={48} className="text-warning" />
          <h3>Voice Recognition Not Available</h3>
          <p>Voice recognition is not supported in this browser.</p>
          <div className="browser-help">
            <h4>Supported Browsers:</h4>
            <ul>
              <li>✅ Google Chrome</li>
              <li>✅ Microsoft Edge</li>
              <li>✅ Safari (macOS)</li>
              <li>❌ Firefox (limited support)</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  const handleToggleListening = async () => {
    if (isListening) {
      await onStopListening();
    } else {
      await onStartListening();
    }
  };

  const handleSendTranscript = async () => {
    if (transcript.trim()) {
      try {
        await onSendMessage(transcript);
      } catch (error) {
        console.error('Failed to send voice message:', error);
      }
    }
  };

  const handleClearError = () => {
    if (onClearError) {
      onClearError();
    }
  };

  return (
    <div className="voice-interface">
      <div className="voice-header">
        <h2>Voice Interface</h2>
        <p>Click the microphone to start talking to BUDDY</p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="voice-error">
          <div className="error-content">
            <AlertTriangle size={20} />
            <span>{error}</span>
            <button 
              className="error-dismiss"
              onClick={handleClearError}
              title="Dismiss error"
            >
              ×
            </button>
          </div>
        </div>
      )}

      <div className="voice-main">
        {/* Microphone Button */}
        <div className="voice-controls">
          <button
            className={`voice-mic-btn ${isListening ? 'listening' : ''} ${error ? 'error' : ''}`}
            onClick={handleToggleListening}
            title={isListening ? 'Stop listening' : 'Start listening'}
            disabled={!hasPermission}
          >
            {isListening ? (
              <MicOff size={48} />
            ) : (
              <Mic size={48} />
            )}
          </button>
          
          <div className="voice-status">
            {isListening ? (
              <span className="status-listening">🎤 Listening... Speak now!</span>
            ) : error ? (
              <span className="status-error">❌ Error occurred</span>
            ) : (
              <span className="status-ready">✅ Ready to listen</span>
            )}
          </div>
        </div>

        {/* Transcript Display */}
        {transcript && (
          <div className="voice-transcript">
            <h4>What you said:</h4>
            <div className="transcript-text">
              {transcript}
            </div>
            
            <div className="transcript-actions">
              <button
                className="btn btn-primary"
                onClick={handleSendTranscript}
              >
                Send Message
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  // Clear transcript (this should be a prop)
                  if (onClearError) onClearError();
                }}
              >
                Clear
              </button>
            </div>
          </div>
        )}

        {/* Voice Visualization */}
        {isListening && (
          <div className="voice-visualizer">
            <div className="wave-container">
              {[...Array(5)].map((_, i) => (
                <div 
                  key={i} 
                  className="wave-bar"
                  style={{ animationDelay: `${i * 0.1}s` }}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="voice-tips">
        <h4>Voice Commands:</h4>
        <div className="tips-grid">
          <div className="tip-category">
            <h5>🕐 Time & Reminders</h5>
            <ul>
              <li>"What time is it?"</li>
              <li>"Set reminder for 6pm"</li>
              <li>"Show my reminders"</li>
            </ul>
          </div>
          <div className="tip-category">
            <h5>🧮 Math & Conversions</h5>
            <ul>
              <li>"Calculate 25 times 4"</li>
              <li>"Convert 50 USD to INR"</li>
              <li>"What's 20 percent of 100?"</li>
            </ul>
          </div>
          <div className="tip-category">
            <h5>🌤️ Weather & Info</h5>
            <ul>
              <li>"What's the weather today?"</li>
              <li>"Tell me a joke"</li>
              <li>"System status"</li>
            </ul>
          </div>
        </div>
        
        <div className="voice-tips-footer">
          <p><strong>Pro Tip:</strong> Speak clearly and at normal pace. BUDDY understands natural language!</p>
        </div>
      </div>
    </div>
  );
};

export default VoiceInterface;
