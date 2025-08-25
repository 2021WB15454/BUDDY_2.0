/**
 * BUDDY 2.0 - Firebase Messaging Service Worker
 * Handles background push notifications
 */

// Import Firebase scripts
importScripts('https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.7.1/firebase-messaging-compat.js');

// Firebase configuration
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
firebase.initializeApp(firebaseConfig);

// Initialize Firebase Messaging
const messaging = firebase.messaging();

/**
 * Handle background messages
 */
messaging.onBackgroundMessage((payload) => {
  console.log('Received background message:', payload);

  const { notification, data } = payload;
  
  // Customize notification
  const notificationTitle = notification?.title || 'BUDDY AI';
  const notificationOptions = {
    body: notification?.body || 'You have a new message from BUDDY',
    icon: '/icons/buddy-icon-192.png',
    badge: '/icons/buddy-badge.png',
    tag: data?.type || 'buddy-notification',
    data: data,
    requireInteraction: data?.priority === 'high',
    actions: getNotificationActions(data?.type),
    timestamp: Date.now()
  };

  // Show notification
  self.registration.showNotification(notificationTitle, notificationOptions);
});

/**
 * Handle notification click
 */
self.addEventListener('notificationclick', (event) => {
  console.log('Notification clicked:', event);
  
  const { action, notification } = event;
  const data = notification.data;
  
  event.notification.close();
  
  // Handle notification actions
  if (action) {
    handleNotificationAction(action, data);
  } else {
    // Default click behavior - open app
    event.waitUntil(
      clients.matchAll({ type: 'window', includeUncontrolled: true })
        .then((clientList) => {
          // Focus existing window or open new one
          if (clientList.length > 0) {
            const client = clientList[0];
            client.focus();
            
            // Send message to focused window
            client.postMessage({
              type: 'notification_click',
              data: data
            });
          } else {
            // Open new window
            const url = data?.click_action || '/';
            clients.openWindow(url);
          }
        })
    );
  }
});

/**
 * Handle notification actions
 */
function handleNotificationAction(action, data) {
  switch (action) {
    case 'snooze':
      // Snooze reminder for 5 minutes
      fetch('/api/v1/reminders/snooze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reminder_id: data?.reminder_id,
          snooze_minutes: 5
        })
      });
      break;
      
    case 'complete':
      // Mark reminder as complete
      fetch('/api/v1/reminders/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reminder_id: data?.reminder_id
        })
      });
      break;
      
    case 'accept':
      // Accept suggestion
      fetch('/api/v1/suggestions/accept', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          suggestion_id: data?.suggestion_id
        })
      });
      break;
      
    case 'dismiss':
      // Dismiss suggestion
      fetch('/api/v1/suggestions/dismiss', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          suggestion_id: data?.suggestion_id
        })
      });
      break;
  }
}

/**
 * Get notification actions based on type
 */
function getNotificationActions(type) {
  switch (type) {
    case 'reminder':
      return [
        { action: 'snooze', title: '⏰ Snooze 5min', icon: '/icons/snooze.png' },
        { action: 'complete', title: '✅ Mark Done', icon: '/icons/complete.png' }
      ];
    case 'suggestion':
      return [
        { action: 'accept', title: '👍 Accept', icon: '/icons/accept.png' },
        { action: 'dismiss', title: '👎 Dismiss', icon: '/icons/dismiss.png' }
      ];
    case 'sync_update':
      return [
        { action: 'view', title: '👀 View Update', icon: '/icons/view.png' }
      ];
    default:
      return [];
  }
}

/**
 * Handle push subscription changes
 */
self.addEventListener('pushsubscriptionchange', (event) => {
  console.log('Push subscription changed:', event);
  
  // Resubscribe to push notifications
  event.waitUntil(
    self.registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array('BD9JGBvmYzR2GYE6CB6lYFkzHV9D0hhLVce2Swy4E48vglT01dG5a7FO9XnBSgHgrjn8c5_ZkM553tn9zqjg8y0')
    }).then((subscription) => {
      // Send new subscription to server
      return fetch('/api/v1/push/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(subscription)
      });
    })
  );
});

/**
 * Utility function to convert VAPID key
 */
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}
