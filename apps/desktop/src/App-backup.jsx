import React, { useState, useEffect } from 'react';
import './styles/App.css';

// Components
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import VoiceInterface from './components/VoiceInterface';
import SkillsPanel from './components/SkillsPanel';
import SettingsPanel from './components/SettingsPanel';
import StatusBar from './components/StatusBar';

// Hooks
import { useBuddy } from './hooks/useBuddy';
import { useVoice } from './hooks/useVoice';

function App() {
  const [currentView, setCurrentView] = useState('chat');
  const [systemStats, setSystemStats] = useState({});
  const [skills, setSkills] = useState([]);
  const [settings, setSettings] = useState({});
  const [errors, setErrors] = useState([]);
  
  // Initialize BUDDY connection and voice
  const buddy = useBuddy();
  const voice = useVoice();

  // System monitoring
  useEffect(() => {
    const updateStats = async () => {
      try {
        if (window.electronAPI) {
          const stats = await window.electronAPI.invoke('get-system-stats');
          setSystemStats(stats);
        }
      } catch (error) {
        console.error('Failed to get system stats:', error);
        setErrors(prev => [...prev, {
          message: 'Failed to get system stats',
          timestamp: new Date().toISOString()
        }]);
      }
    };

    updateStats();
    const interval = setInterval(updateStats, 5000); // Update every 5 seconds
    return () => clearInterval(interval);
  }, []);

  // Load skills
  useEffect(() => {
    const loadSkills = async () => {
      try {
        if (window.electronAPI) {
          const skillsResponse = await window.electronAPI.invoke('get-skills');
          // Extract the skills array from the response object
          const skillsData = skillsResponse?.data?.skills || skillsResponse?.skills || [];
          setSkills(skillsData);
        }
      } catch (error) {
        console.error('Failed to load skills:', error);
        setErrors(prev => [...prev, {
          message: 'Failed to load skills',
          timestamp: new Date().toISOString()
        }]);
      }
    };

    loadSkills();
  }, []);

  // Load settings
  useEffect(() => {
    const loadSettings = async () => {
      try {
        if (window.electronAPI) {
          const settingsData = await window.electronAPI.invoke('get-settings');
          setSettings(settingsData || {});
        }
      } catch (error) {
        console.error('Failed to load settings:', error);
        setErrors(prev => [...prev, {
          message: 'Failed to load settings',
          timestamp: new Date().toISOString()
        }]);
      }
    };

    loadSettings();
  }, []);

  // Handle settings changes
  const handleSettingsChange = (newSettings) => {
    setSettings(newSettings);
  };

  // Handle settings save
  const handleSaveSettings = async (newSettings) => {
    try {
      if (window.electronAPI) {
        await window.electronAPI.invoke('save-settings', newSettings);
        setSettings(newSettings);
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
      setErrors(prev => [...prev, {
        message: 'Failed to save settings',
        timestamp: new Date().toISOString()
      }]);
      throw error;
    }
  };

  // Handle voice transcript
  const handleVoiceMessage = async (transcript) => {
    try {
      await buddy.sendMessage(transcript);
    } catch (error) {
      console.error('Failed to send voice message:', error);
      setErrors(prev => [...prev, {
        message: 'Failed to send voice message',
        timestamp: new Date().toISOString()
      }]);
    }
  };

  // Clear old errors (keep only last 10)
  useEffect(() => {
    if (errors.length > 10) {
      setErrors(prev => prev.slice(-10));
    }
  }, [errors]);

  const renderCurrentView = () => {
    switch (currentView) {
      case 'chat':
        return (
          <ChatInterface
            messages={buddy.messages}
            isLoading={buddy.isLoading}
            onSendMessage={buddy.sendMessage}
            isVoiceEnabled={voice.isSupported}
            onStartVoice={voice.startListening}
          />
        );
      case 'voice':
        return (
          <VoiceInterface
            isListening={voice.isListening}
            isSupported={voice.isSupported}
            onStartListening={voice.startListening}
            onStopListening={voice.stopListening}
            transcript={voice.transcript}
            onSendMessage={handleVoiceMessage}
          />
        );
      case 'skills':
        return (
          <SkillsPanel
            skills={skills}
            isLoading={false}
            error={null}
          />
        );
      case 'settings':
        return (
          <SettingsPanel
            currentSettings={settings}
            onSettingsChange={handleSettingsChange}
            onSave={handleSaveSettings}
          />
        );
      default:
        return <div>Unknown view: {currentView}</div>;
    }
  };

  return (
    <div className="app">
      <div className="app-sidebar">
        <Sidebar
          currentView={currentView}
          onViewChange={setCurrentView}
          connectionStatus={buddy.connectionStatus}
          voiceStatus={voice.isListening ? 'listening' : voice.isSupported ? 'ready' : 'disabled'}
          systemStats={systemStats}
        />
      </div>
      
      <div className="app-main">
        <div className="app-content">
          {renderCurrentView()}
        </div>
        
        <div className="app-status">
          <StatusBar
            connectionStatus={buddy.connectionStatus}
            systemStats={systemStats}
            voiceStatus={voice.isListening ? 'listening' : voice.isSupported ? 'enabled' : 'disabled'}
            lastActivity={buddy.lastActivity}
            activeSkills={Array.isArray(skills) ? skills.filter(s => s.enabled).length : 0}
            errors={errors}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
