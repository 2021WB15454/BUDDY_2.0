import React from 'react';
import { 
  Wifi, 
  WifiOff, 
  Activity, 
  Cpu, 
  HardDrive, 
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle
} from 'lucide-react';

const StatusBar = ({ 
  connectionStatus = 'disconnected',
  systemStats = {},
  voiceStatus = 'disabled',
  lastActivity = null,
  activeSkills = 0,
  errors = []
}) => {
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  const formatMemory = (bytes) => {
    if (!bytes) return '0 MB';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  const getConnectionIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return <Wifi size={14} className="text-success" />;
      case 'connecting':
        return <Wifi size={14} className="text-warning" />;
      default:
        return <WifiOff size={14} className="text-danger" />;
    }
  };

  const getConnectionLabel = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'Connected';
      case 'connecting':
        return 'Connecting...';
      default:
        return 'Disconnected';
    }
  };

  const getVoiceIcon = () => {
    switch (voiceStatus) {
      case 'listening':
        return <Mic size={14} className="text-primary" />;
      case 'speaking':
        return <Volume2 size={14} className="text-info" />;
      case 'enabled':
        return <Mic size={14} className="text-success" />;
      case 'muted':
        return <MicOff size={14} className="text-warning" />;
      default:
        return <VolumeX size={14} className="text-muted" />;
    }
  };

  const getVoiceLabel = () => {
    switch (voiceStatus) {
      case 'listening':
        return 'Listening';
      case 'speaking':
        return 'Speaking';
      case 'enabled':
        return 'Voice Ready';
      case 'muted':
        return 'Muted';
      default:
        return 'Voice Disabled';
    }
  };

  const getHealthIcon = () => {
    if (errors.length > 0) {
      return <XCircle size={14} className="text-danger" />;
    }
    if (connectionStatus === 'connected' && voiceStatus !== 'disabled') {
      return <CheckCircle size={14} className="text-success" />;
    }
    return <AlertTriangle size={14} className="text-warning" />;
  };

  const getHealthLabel = () => {
    if (errors.length > 0) {
      return `${errors.length} Error${errors.length > 1 ? 's' : ''}`;
    }
    if (connectionStatus === 'connected' && voiceStatus !== 'disabled') {
      return 'All Systems Operational';
    }
    return 'Limited Functionality';
  };

  return (
    <div className="status-bar">
      {/* Connection Status */}
      <div className="status-item" title={`Backend ${getConnectionLabel()}`}>
        {getConnectionIcon()}
        <span className="status-label">{getConnectionLabel()}</span>
      </div>

      {/* Voice Status */}
      <div className="status-item" title={getVoiceLabel()}>
        {getVoiceIcon()}
        <span className="status-label">{getVoiceLabel()}</span>
      </div>

      {/* System Health */}
      <div className="status-item" title={getHealthLabel()}>
        {getHealthIcon()}
        <span className="status-label">
          {errors.length > 0 ? `${errors.length} Error${errors.length > 1 ? 's' : ''}` : 'Healthy'}
        </span>
      </div>

      {/* Active Skills */}
      <div className="status-item" title={`${activeSkills} active skill${activeSkills !== 1 ? 's' : ''}`}>
        <Activity size={14} />
        <span className="status-label">{activeSkills} Skills</span>
      </div>

      {/* System Stats */}
      {systemStats.cpu && (
        <div className="status-item" title={`CPU Usage: ${systemStats.cpu.toFixed(1)}%`}>
          <Cpu size={14} />
          <span className="status-label">{systemStats.cpu.toFixed(1)}%</span>
        </div>
      )}

      {systemStats.memory && (
        <div className="status-item" title={`Memory Usage: ${formatMemory(systemStats.memory.used)} / ${formatMemory(systemStats.memory.total)}`}>
          <HardDrive size={14} />
          <span className="status-label">{formatMemory(systemStats.memory.used)}</span>
        </div>
      )}

      {/* Last Activity */}
      <div className="status-item" title={`Last Activity: ${formatTimestamp(lastActivity)}`}>
        <Clock size={14} />
        <span className="status-label">{formatTimestamp(lastActivity)}</span>
      </div>

      {/* Error Details (if any) */}
      {errors.length > 0 && (
        <div className="status-errors">
          <div className="error-dropdown">
            <button className="error-toggle" title="View errors">
              <AlertTriangle size={14} />
              {errors.length}
            </button>
            <div className="error-list">
              {errors.slice(0, 5).map((error, index) => (
                <div key={index} className="error-item">
                  <div className="error-message">{error.message}</div>
                  <div className="error-time">{formatTimestamp(error.timestamp)}</div>
                </div>
              ))}
              {errors.length > 5 && (
                <div className="error-item">
                  <div className="error-message">...and {errors.length - 5} more</div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StatusBar;
