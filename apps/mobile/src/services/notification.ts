export interface NotificationPayload { id: string; title: string; body: string; actions?: { id: string; title: string }[]; }

export async function scheduleLocalNotification(payload: NotificationPayload) {
  // Placeholder: use react-native-push-notification or Notifee
  console.log('schedule notification', payload);
}
