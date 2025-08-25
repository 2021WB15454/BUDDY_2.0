import React, { useState, useEffect } from 'react';
import { 
  Settings, 
  User, 
  Volume2, 
  Mic, 
  Shield, 
  RefreshCw, 
  Database,
  Wifi,
  Bell,
  Moon,
  Save,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';

const SettingsPanel = ({ currentSettings = {}, onSettingsChange, onSave }) => {
  const [settings, setSettings] = useState({
    // General Settings
    name: 'BUDDY',
    language: 'en-US',
    theme: 'auto', // light, dark, auto
    
    // Voice Settings
    voiceEnabled: true,
    wakeWord: 'hey buddy',
    voiceModel: 'whisper-base',
    ttsVoice: 'neural-jenny',
    voiceVolume: 0.8,
    micSensitivity: 0.5,
    
    // Privacy Settings
    dataCollection: false,
    analytics: false,
    conversationHistory: true,
    encryptData: true,
    
    // Sync Settings
    syncEnabled: false,
    syncEndpoint: '',
    syncInterval: 300, // seconds
    
    // Notification Settings
    notifications: true,
    soundAlerts: true,
    quietHours: false,
    quietStart: '22:00',
    quietEnd: '08:00',
    
    // Advanced Settings
    debugMode: false,
    logLevel: 'info',
    maxConcurrentSkills: 5,
    responseTimeout: 30,
    
    ...currentSettings
  });

  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null); // 'success', 'error'

  // Available options for dropdowns
  const languages = [
    { value: 'en-US', label: 'English (US)' },
    { value: 'en-GB', label: 'English (UK)' },
    { value: 'es-ES', label: 'Spanish' },
    { value: 'fr-FR', label: 'French' },
    { value: 'de-DE', label: 'German' },
    { value: 'it-IT', label: 'Italian' },
    { value: 'pt-BR', label: 'Portuguese (Brazil)' },
    { value: 'ja-JP', label: 'Japanese' },
    { value: 'ko-KR', label: 'Korean' },
    { value: 'zh-CN', label: 'Chinese (Simplified)' }
  ];

  const voiceModels = [
    { value: 'whisper-tiny', label: 'Whisper Tiny (Fastest)' },
    { value: 'whisper-base', label: 'Whisper Base (Balanced)' },
    { value: 'whisper-small', label: 'Whisper Small (Better)' },
    { value: 'whisper-medium', label: 'Whisper Medium (Best)' }
  ];

  const ttsVoices = [
    { value: 'neural-jenny', label: 'Jenny (Neural)' },
    { value: 'neural-aria', label: 'Aria (Neural)' },
    { value: 'neural-guy', label: 'Guy (Neural)' },
    { value: 'standard-joanna', label: 'Joanna (Standard)' },
    { value: 'standard-matthew', label: 'Matthew (Standard)' }
  ];

  const logLevels = [
    { value: 'debug', label: 'Debug (Verbose)' },
    { value: 'info', label: 'Info (Normal)' },
    { value: 'warning', label: 'Warning (Important)' },
    { value: 'error', label: 'Error (Critical Only)' }
  ];

  const handleInputChange = (key, value) => {
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);
    onSettingsChange?.(newSettings);
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveStatus(null);
    
    try {
      await onSave?.(settings);
      setSaveStatus('success');
      setTimeout(() => setSaveStatus(null), 3000);
    } catch (error) {
      console.error('Failed to save settings:', error);
      setSaveStatus('error');
      setTimeout(() => setSaveStatus(null), 5000);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    if (confirm('Are you sure you want to reset all settings to defaults?')) {
      const defaultSettings = {
        name: 'BUDDY',
        language: 'en-US',
        theme: 'auto',
        voiceEnabled: true,
        wakeWord: 'hey buddy',
        voiceModel: 'whisper-base',
        ttsVoice: 'neural-jenny',
        voiceVolume: 0.8,
        micSensitivity: 0.5,
        dataCollection: false,
        analytics: false,
        conversationHistory: true,
        encryptData: true,
        syncEnabled: false,
        syncEndpoint: '',
        syncInterval: 300,
        notifications: true,
        soundAlerts: true,
        quietHours: false,
        quietStart: '22:00',
        quietEnd: '08:00',
        debugMode: false,
        logLevel: 'info',
        maxConcurrentSkills: 5,
        responseTimeout: 30
      };
      setSettings(defaultSettings);
      onSettingsChange?.(defaultSettings);
    }
  };

  const SettingSection = ({ title, icon: Icon, children }) => (
    <div className="setting-section">
      <div className="setting-section-header">
        <Icon size={20} />
        <h3>{title}</h3>
      </div>
      <div className="setting-section-content">
        {children}
      </div>
    </div>
  );

  const SettingRow = ({ label, description, children }) => (
    <div className="setting-row">
      <div className="setting-info">
        <label className="setting-label">{label}</label>
        {description && <p className="setting-description">{description}</p>}
      </div>
      <div className="setting-control">
        {children}
      </div>
    </div>
  );

  return (
    <div className="settings-panel">
      <div className="settings-header">
        <h2>Settings</h2>
        <div className="settings-actions">
          {saveStatus === 'success' && (
            <span className="save-status success">
              <CheckCircle size={16} />
              Saved successfully
            </span>
          )}
          {saveStatus === 'error' && (
            <span className="save-status error">
              <AlertTriangle size={16} />
              Failed to save
            </span>
          )}
          <button
            className="btn btn-outline-secondary"
            onClick={handleReset}
            disabled={isSaving}
          >
            <RefreshCw size={16} />
            Reset
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={isSaving}
          >
            {isSaving ? (
              <>
                <RefreshCw size={16} className="spinning" />
                Saving...
              </>
            ) : (
              <>
                <Save size={16} />
                Save
              </>
            )}
          </button>
        </div>
      </div>

      <div className="settings-content">
        {/* General Settings */}
        <SettingSection title="General" icon={Settings}>
          <SettingRow label="Assistant Name" description="What would you like to call your assistant?">
            <input
              type="text"
              value={settings.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              className="form-control"
            />
          </SettingRow>

          <SettingRow label="Language" description="Primary language for interactions">
            <select
              value={settings.language}
              onChange={(e) => handleInputChange('language', e.target.value)}
              className="form-select"
            >
              {languages.map(lang => (
                <option key={lang.value} value={lang.value}>{lang.label}</option>
              ))}
            </select>
          </SettingRow>

          <SettingRow label="Theme" description="Choose your preferred appearance">
            <select
              value={settings.theme}
              onChange={(e) => handleInputChange('theme', e.target.value)}
              className="form-select"
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="auto">Auto (System)</option>
            </select>
          </SettingRow>
        </SettingSection>

        {/* Voice Settings */}
        <SettingSection title="Voice & Speech" icon={Mic}>
          <SettingRow label="Voice Interaction" description="Enable voice commands and responses">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.voiceEnabled}
                onChange={(e) => handleInputChange('voiceEnabled', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </SettingRow>

          <SettingRow label="Wake Word" description="Word or phrase to activate voice mode">
            <input
              type="text"
              value={settings.wakeWord}
              onChange={(e) => handleInputChange('wakeWord', e.target.value)}
              className="form-control"
              disabled={!settings.voiceEnabled}
            />
          </SettingRow>

          <SettingRow label="Speech Recognition Model" description="Quality vs speed trade-off">
            <select
              value={settings.voiceModel}
              onChange={(e) => handleInputChange('voiceModel', e.target.value)}
              className="form-select"
              disabled={!settings.voiceEnabled}
            >
              {voiceModels.map(model => (
                <option key={model.value} value={model.value}>{model.label}</option>
              ))}
            </select>
          </SettingRow>

          <SettingRow label="Text-to-Speech Voice" description="Choose the voice for responses">
            <select
              value={settings.ttsVoice}
              onChange={(e) => handleInputChange('ttsVoice', e.target.value)}
              className="form-select"
              disabled={!settings.voiceEnabled}
            >
              {ttsVoices.map(voice => (
                <option key={voice.value} value={voice.value}>{voice.label}</option>
              ))}
            </select>
          </SettingRow>

          <SettingRow label="Voice Volume" description="Adjust response volume">
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={settings.voiceVolume}
              onChange={(e) => handleInputChange('voiceVolume', parseFloat(e.target.value))}
              className="form-range"
              disabled={!settings.voiceEnabled}
            />
            <span className="range-value">{Math.round(settings.voiceVolume * 100)}%</span>
          </SettingRow>

          <SettingRow label="Microphone Sensitivity" description="Adjust voice detection sensitivity">
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={settings.micSensitivity}
              onChange={(e) => handleInputChange('micSensitivity', parseFloat(e.target.value))}
              className="form-range"
              disabled={!settings.voiceEnabled}
            />
            <span className="range-value">{Math.round(settings.micSensitivity * 100)}%</span>
          </SettingRow>
        </SettingSection>

        {/* Privacy Settings */}
        <SettingSection title="Privacy & Security" icon={Shield}>
          <SettingRow label="Data Collection" description="Allow anonymous usage data collection">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.dataCollection}
                onChange={(e) => handleInputChange('dataCollection', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </SettingRow>

          <SettingRow label="Analytics" description="Enable analytics for improving performance">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.analytics}
                onChange={(e) => handleInputChange('analytics', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </SettingRow>

          <SettingRow label="Conversation History" description="Save conversation history locally">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.conversationHistory}
                onChange={(e) => handleInputChange('conversationHistory', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </SettingRow>

          <SettingRow label="Encrypt Data" description="Encrypt stored data and communications">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.encryptData}
                onChange={(e) => handleInputChange('encryptData', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </SettingRow>
        </SettingSection>

        {/* Sync Settings */}
        <SettingSection title="Device Sync" icon={RefreshCw}>
          <SettingRow label="Cross-Device Sync" description="Sync data across your devices">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.syncEnabled}
                onChange={(e) => handleInputChange('syncEnabled', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </SettingRow>

          <SettingRow label="Sync Server" description="Your BUDDY Home Hub endpoint">
            <input
              type="url"
              value={settings.syncEndpoint}
              onChange={(e) => handleInputChange('syncEndpoint', e.target.value)}
              placeholder="http://192.168.1.100:8080"
              className="form-control"
              disabled={!settings.syncEnabled}
            />
          </SettingRow>

          <SettingRow label="Sync Interval" description="How often to sync (in seconds)">
            <input
              type="number"
              min="60"
              max="3600"
              value={settings.syncInterval}
              onChange={(e) => handleInputChange('syncInterval', parseInt(e.target.value))}
              className="form-control"
              disabled={!settings.syncEnabled}
            />
          </SettingRow>
        </SettingSection>

        {/* Notifications */}
        <SettingSection title="Notifications" icon={Bell}>
          <SettingRow label="Enable Notifications" description="Show system notifications">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.notifications}
                onChange={(e) => handleInputChange('notifications', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </SettingRow>

          <SettingRow label="Sound Alerts" description="Play sounds for notifications">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.soundAlerts}
                onChange={(e) => handleInputChange('soundAlerts', e.target.checked)}
                disabled={!settings.notifications}
              />
              <span className="toggle-slider"></span>
            </label>
          </SettingRow>

          <SettingRow label="Quiet Hours" description="Disable notifications during specific hours">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.quietHours}
                onChange={(e) => handleInputChange('quietHours', e.target.checked)}
                disabled={!settings.notifications}
              />
              <span className="toggle-slider"></span>
            </label>
          </SettingRow>

          {settings.quietHours && (
            <>
              <SettingRow label="Quiet Hours Start" description="When to start quiet hours">
                <input
                  type="time"
                  value={settings.quietStart}
                  onChange={(e) => handleInputChange('quietStart', e.target.value)}
                  className="form-control"
                />
              </SettingRow>

              <SettingRow label="Quiet Hours End" description="When to end quiet hours">
                <input
                  type="time"
                  value={settings.quietEnd}
                  onChange={(e) => handleInputChange('quietEnd', e.target.value)}
                  className="form-control"
                />
              </SettingRow>
            </>
          )}
        </SettingSection>

        {/* Advanced Settings */}
        <SettingSection title="Advanced" icon={Database}>
          <SettingRow label="Debug Mode" description="Enable detailed logging and debug features">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.debugMode}
                onChange={(e) => handleInputChange('debugMode', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </SettingRow>

          <SettingRow label="Log Level" description="How much detail to include in logs">
            <select
              value={settings.logLevel}
              onChange={(e) => handleInputChange('logLevel', e.target.value)}
              className="form-select"
            >
              {logLevels.map(level => (
                <option key={level.value} value={level.value}>{level.label}</option>
              ))}
            </select>
          </SettingRow>

          <SettingRow label="Max Concurrent Skills" description="Maximum skills that can run simultaneously">
            <input
              type="number"
              min="1"
              max="20"
              value={settings.maxConcurrentSkills}
              onChange={(e) => handleInputChange('maxConcurrentSkills', parseInt(e.target.value))}
              className="form-control"
            />
          </SettingRow>

          <SettingRow label="Response Timeout" description="Maximum time to wait for skill responses (seconds)">
            <input
              type="number"
              min="5"
              max="120"
              value={settings.responseTimeout}
              onChange={(e) => handleInputChange('responseTimeout', parseInt(e.target.value))}
              className="form-control"
            />
          </SettingRow>
        </SettingSection>
      </div>
    </div>
  );
};

export default SettingsPanel;
