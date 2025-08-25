import React from 'react';
import { 
  MessageCircle, 
  Mic, 
  Settings, 
  Grid3X3,
  Wifi,
  WifiOff,
  Activity
} from 'lucide-react';

const Sidebar = ({ 
  currentView, 
  onViewChange, 
  connectionStatus = 'disconnected',
  voiceStatus = 'disabled',
  systemStats = {}
}) => {
  const menuItems = [
    {
      id: 'chat',
      label: 'Chat',
      icon: MessageCircle,
      available: true
    },
    {
      id: 'voice',
      label: 'Voice',
      icon: Mic,
      available: voiceStatus !== 'disabled'
    },
    {
      id: 'skills',
      label: 'Skills',
      icon: Grid3X3,
      available: true
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: Settings,
      available: true
    }
  ];

  const getConnectionStatus = () => {
    switch (connectionStatus) {
      case 'connected':
        return { text: 'Connected to BUDDY', className: 'connected' };
      case 'connecting':
        return { text: 'Connecting...', className: 'connecting' };
      default:
        return { text: 'Disconnected', className: 'disconnected' };
    }
  };

  const status = getConnectionStatus();

  return (
    <div className="sidebar">
      {/* Header */}
      <div className="sidebar-header">
        <h1>BUDDY</h1>
        <p>Your AI Assistant</p>
      </div>

      {/* Connection Status */}
      <div className={`connection-status ${status.className}`}>
        {connectionStatus === 'connected' ? <Wifi size={16} /> : <WifiOff size={16} />}
        <span>{status.text}</span>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <ul className="nav-list">
          {menuItems.map(item => {
            const Icon = item.icon;
            const isActive = currentView === item.id;
            const isDisabled = !item.available;

            return (
              <li key={item.id} className="nav-item">
                <button
                  className={`nav-link ${isActive ? 'active' : ''} ${isDisabled ? 'disabled' : ''}`}
                  onClick={() => item.available && onViewChange(item.id)}
                  disabled={isDisabled}
                >
                  <Icon size={20} />
                  <span>{item.label}</span>
                  {isDisabled && <span className="nav-badge">N/A</span>}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* System Stats */}
      {systemStats && Object.keys(systemStats).length > 0 && (
        <div className="sidebar-stats">
          <h4>System Status</h4>
          {systemStats.cpu && (
            <div className="stat-item">
              <Activity size={14} />
              <span>CPU: {systemStats.cpu.toFixed(1)}%</span>
            </div>
          )}
          {systemStats.memory && (
            <div className="stat-item">
              <Activity size={14} />
              <span>Memory: {(systemStats.memory.used / systemStats.memory.total * 100).toFixed(1)}%</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Sidebar;
