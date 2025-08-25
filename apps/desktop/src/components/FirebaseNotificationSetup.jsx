/**
 * BUDDY 2.0 - Firebase Notification Setup Component
 * Handles push notification permissions and setup
 */

import React, { useState, useEffect } from 'react';
import { buddyMessaging } from '../firebase';

const FirebaseNotificationSetup = ({ onTokenReceived }) => {
  const [permissionStatus, setPermissionStatus] = useState('default');
  const [token, setToken] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Check current permission status
    if ('Notification' in window) {
      setPermissionStatus(Notification.permission);
    }
  }, []);

  const requestNotificationPermission = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await buddyMessaging.requestPermission();
      
      if (result.success) {
        setPermissionStatus('granted');
        setToken(result.token);
        
        // Notify parent component
        if (onTokenReceived) {
          onTokenReceived(result.token);
        }
      } else {
        setPermissionStatus(result.permission);
        if (result.error) {
          setError(result.error);
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusIcon = () => {
    switch (permissionStatus) {
      case 'granted':
        return '✅';
      case 'denied':
        return '❌';
      default:
        return '🔔';
    }
  };

  const getStatusText = () => {
    switch (permissionStatus) {
      case 'granted':
        return 'Notifications enabled';
      case 'denied':
        return 'Notifications blocked';
      default:
        return 'Notifications not configured';
    }
  };

  const getStatusColor = () => {
    switch (permissionStatus) {
      case 'granted':
        return '#4CAF50';
      case 'denied':
        return '#f44336';
      default:
        return '#ff9800';
    }
  };

  if (permissionStatus === 'granted' && token) {
    return (
      <div className="firebase-notification-status">
        <div style={{ color: getStatusColor(), marginBottom: '8px' }}>
          {getStatusIcon()} {getStatusText()}
        </div>
        <div className="token-info">
          <small>
            Device registered for push notifications
            <br />
            Token: {token.substring(0, 20)}...
          </small>
        </div>
      </div>
    );
  }

  return (
    <div className="firebase-notification-setup">
      <div className="notification-status" style={{ color: getStatusColor(), marginBottom: '16px' }}>
        {getStatusIcon()} {getStatusText()}
      </div>
      
      {permissionStatus !== 'granted' && (
        <div className="notification-prompt">
          <p>Enable push notifications to receive:</p>
          <ul style={{ textAlign: 'left', margin: '8px 0' }}>
            <li>Cross-device sync updates</li>
            <li>Smart reminders</li>
            <li>AI suggestions</li>
            <li>Important alerts</li>
          </ul>
          
          <button
            onClick={requestNotificationPermission}
            disabled={isLoading || permissionStatus === 'denied'}
            className="enable-notifications-btn"
            style={{
              padding: '12px 24px',
              backgroundColor: '#4A90E2',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: permissionStatus === 'denied' ? 'not-allowed' : 'pointer',
              opacity: permissionStatus === 'denied' ? 0.5 : 1
            }}
          >
            {isLoading ? '🔄 Setting up...' : '🔔 Enable Notifications'}
          </button>
          
          {permissionStatus === 'denied' && (
            <p style={{ fontSize: '12px', color: '#666', marginTop: '8px' }}>
              Notifications are blocked. Please enable them in your browser settings.
            </p>
          )}
        </div>
      )}
      
      {error && (
        <div className="error-message" style={{ color: '#f44336', marginTop: '8px' }}>
          Error: {error}
        </div>
      )}
    </div>
  );
};

export default FirebaseNotificationSetup;
