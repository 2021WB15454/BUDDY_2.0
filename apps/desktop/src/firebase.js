/**
 * BUDDY 2.0 - Firebase Configuration
 * Web Push Notifications & Analytics Setup
 */

import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getMessaging, getToken, onMessage } from "firebase/messaging";

// Firebase configuration from environment
const firebaseConfig = {
  apiKey: "AIzaSyACJo5Tfp6yPpxoqVeBfAWv2UgkutiaUsQ",
  authDomain: "buddyai-42493.firebaseapp.com",
  projectId: "buddyai-42493",
  storageBucket: "buddyai-42493.firebasestorage.app",
  messagingSenderId: "335644247986",
  appId: "1:335644247986:web:2dcd64638403fbe03186ab",
  measurementId: "G-SGXDLPERH1"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Analytics (optional)
let analytics = null;
try {
  if (typeof window !== 'undefined') {
    analytics = getAnalytics(app);
  }
} catch (error) {
  console.warn('Firebase Analytics not available:', error);
}

// Initialize Messaging for push notifications
let messaging = null;
try {
  if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
    messaging = getMessaging(app);
  }
} catch (error) {
  console.warn('Firebase Messaging not available:', error);
}

/**
 * BUDDY Firebase Messaging Service
 */
class BuddyFirebaseMessaging {
  constructor() {
    this.messaging = messaging;
    this.currentToken = null;
    this.vapidKey = process.env.REACT_APP_FIREBASE_VAPID_KEY || 'BLfh5LhXnR1nBBdXFA4JCQji4Hy3N44euJQM0F-97r6oodTMNVBcr8e5WFGS2EiP7rphZxTnyzXv3FZmmBACsQk';
  }

  /**
   * Request permission and get FCM token
   */
  async requestPermission() {
    if (!this.messaging) {
      throw new Error('Firebase Messaging not available');
    }

    try {
      console.log('Requesting notification permission...');
      const permission = await Notification.requestPermission();
      
      if (permission === 'granted') {
        console.log('Notification permission granted.');
        const token = await this.getToken();
        return { success: true, token, permission };
      } else {
        console.log('Unable to get permission to notify.');
        return { success: false, permission };
      }
    } catch (error) {
      console.error('An error occurred while retrieving token:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Get FCM registration token
   */
  async getToken() {
    if (!this.messaging) {
      throw new Error('Firebase Messaging not available');
    }

    try {
      const token = await getToken(this.messaging, {
        vapidKey: this.vapidKey
      });
      
      if (token) {
        console.log('FCM registration token:', token);
        this.currentToken = token;
        
        // Send token to BUDDY backend
        await this.sendTokenToServer(token);
        return token;
      } else {
        console.log('No registration token available.');
        return null;
      }
    } catch (error) {
      console.error('Error getting FCM token:', error);
      throw error;
    }
  }

  /**
   * Send token to BUDDY backend for storage
   */
  async sendTokenToServer(token) {
    try {
      const response = await fetch('/api/v1/auth/register-device-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('buddy_access_token')}`
        },
        body: JSON.stringify({
          token: token,
          platform: 'web',
          device_type: 'desktop',
          user_agent: navigator.userAgent
        })
      });

      if (response.ok) {
        console.log('Device token registered with BUDDY backend');
      } else {
        console.error('Failed to register device token:', await response.text());
      }
    } catch (error) {
      console.error('Error sending token to server:', error);
    }
  }

  /**
   * Set up foreground message handler
   */
  setupForegroundMessageHandler() {
    if (!this.messaging) {
      return;
    }

    onMessage(this.messaging, (payload) => {
      console.log('Message received in foreground:', payload);
      
      const { notification, data } = payload;
      
      // Show notification to user
      this.showNotification(notification, data);
      
      // Handle BUDDY-specific notification types
      this.handleBuddyNotification(data);
    });
  }

  /**
   * Show notification to user
   */
  showNotification(notification, data) {
    const { title, body, icon } = notification;
    
    // Create system notification
    if (Notification.permission === 'granted') {
      const notificationOptions = {
        body: body,
        icon: icon || '/favicon.ico',
        badge: '/icons/buddy-badge.png',
        tag: data?.type || 'buddy-notification',
        data: data,
        requireInteraction: data?.priority === 'high',
        actions: this.getNotificationActions(data?.type)
      };

      const systemNotification = new Notification(title, notificationOptions);
      
      systemNotification.onclick = () => {
        this.handleNotificationClick(data);
        systemNotification.close();
      };
    }
    
    // Also show in-app notification
    this.showInAppNotification(notification, data);
  }

  /**
   * Handle BUDDY-specific notification types
   */
  handleBuddyNotification(data) {
    if (!data) return;

    switch (data.type) {
      case 'sync_update':
        this.handleSyncUpdate(data);
        break;
      case 'reminder':
        this.handleReminder(data);
        break;
      case 'suggestion':
        this.handleSuggestion(data);
        break;
      default:
        console.log('Unknown notification type:', data.type);
    }
  }

  /**
   * Handle sync update notifications
   */
  handleSyncUpdate(data) {
    console.log('Handling sync update:', data);
    
    // Trigger sync in BUDDY app
    if (window.buddyApp && window.buddyApp.sync) {
      window.buddyApp.sync.handleRemoteUpdate(data);
    }
  }

  /**
   * Handle reminder notifications
   */
  handleReminder(data) {
    console.log('Handling reminder:', data);
    
    // Show reminder in BUDDY UI
    if (window.buddyApp && window.buddyApp.reminders) {
      window.buddyApp.reminders.showReminder(data);
    }
  }

  /**
   * Handle suggestion notifications
   */
  handleSuggestion(data) {
    console.log('Handling suggestion:', data);
    
    // Show suggestion in BUDDY UI
    if (window.buddyApp && window.buddyApp.suggestions) {
      window.buddyApp.suggestions.showSuggestion(data);
    }
  }

  /**
   * Get notification actions based on type
   */
  getNotificationActions(type) {
    switch (type) {
      case 'reminder':
        return [
          { action: 'snooze', title: 'Snooze 5min' },
          { action: 'complete', title: 'Mark Done' }
        ];
      case 'suggestion':
        return [
          { action: 'accept', title: 'Accept' },
          { action: 'dismiss', title: 'Dismiss' }
        ];
      default:
        return [];
    }
  }

  /**
   * Handle notification click
   */
  handleNotificationClick(data) {
    // Focus the window
    window.focus();
    
    // Navigate to relevant section based on notification type
    if (data?.click_action) {
      // Handle custom BUDDY URLs
      if (data.click_action.startsWith('buddy://')) {
        this.handleBuddyUrl(data.click_action);
      } else {
        window.location.href = data.click_action;
      }
    }
  }

  /**
   * Handle BUDDY custom URLs
   */
  handleBuddyUrl(url) {
    const [, resource, id] = url.replace('buddy://', '').split('/');
    
    switch (resource) {
      case 'conversation':
        if (window.buddyApp && window.buddyApp.router) {
          window.buddyApp.router.navigate(`/conversation/${id}`);
        }
        break;
      case 'reminder':
        if (window.buddyApp && window.buddyApp.router) {
          window.buddyApp.router.navigate(`/reminders/${id}`);
        }
        break;
      case 'suggestions':
        if (window.buddyApp && window.buddyApp.router) {
          window.buddyApp.router.navigate('/suggestions');
        }
        break;
    }
  }

  /**
   * Show in-app notification
   */
  showInAppNotification(notification, data) {
    // Create in-app notification element
    const notificationEl = document.createElement('div');
    notificationEl.className = 'buddy-notification';
    notificationEl.innerHTML = `
      <div class="buddy-notification-content">
        <h4>${notification.title}</h4>
        <p>${notification.body}</p>
        <div class="buddy-notification-actions">
          <button class="dismiss">Dismiss</button>
        </div>
      </div>
    `;

    // Add to notification container
    const container = document.getElementById('buddy-notifications') || document.body;
    container.appendChild(notificationEl);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      notificationEl.remove();
    }, 5000);

    // Handle dismiss
    notificationEl.querySelector('.dismiss').onclick = () => {
      notificationEl.remove();
    };
  }
}

// Create global instance
const buddyMessaging = new BuddyFirebaseMessaging();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    buddyMessaging.setupForegroundMessageHandler();
  });
} else {
  buddyMessaging.setupForegroundMessageHandler();
}

export { app, analytics, messaging, buddyMessaging };
export default firebaseConfig;
