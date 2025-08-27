"""
📊 BUDDY 2.0 Enhanced Email Analytics & Tracking
Advanced email metrics, delivery tracking, and performance analysis
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

class EmailStatus(Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"
    SPAM = "spam"

@dataclass
class EmailEvent:
    timestamp: datetime
    event_type: EmailStatus
    details: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None

@dataclass
class EmailTrackingData:
    email_id: str
    recipient: str
    subject: str
    sent_at: datetime
    status: EmailStatus
    events: List[EmailEvent]
    template_used: Optional[str] = None
    campaign_id: Optional[str] = None
    open_count: int = 0
    click_count: int = 0
    size_bytes: int = 0
    provider: str = "unknown"
    device_type: str = "unknown"
    location: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'email_id': self.email_id,
            'recipient': self.recipient,
            'subject': self.subject,
            'sent_at': self.sent_at.isoformat(),
            'status': self.status.value,
            'events': [
                {
                    'timestamp': event.timestamp.isoformat(),
                    'event_type': event.event_type.value,
                    'details': event.details,
                    'user_agent': event.user_agent,
                    'ip_address': event.ip_address
                } for event in self.events
            ],
            'template_used': self.template_used,
            'campaign_id': self.campaign_id,
            'open_count': self.open_count,
            'click_count': self.click_count,
            'size_bytes': self.size_bytes,
            'provider': self.provider,
            'device_type': self.device_type,
            'location': self.location
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailTrackingData':
        events = []
        for event_data in data.get('events', []):
            events.append(EmailEvent(
                timestamp=datetime.fromisoformat(event_data['timestamp']),
                event_type=EmailStatus(event_data['event_type']),
                details=event_data.get('details'),
                user_agent=event_data.get('user_agent'),
                ip_address=event_data.get('ip_address')
            ))
        
        return cls(
            email_id=data['email_id'],
            recipient=data['recipient'],
            subject=data['subject'],
            sent_at=datetime.fromisoformat(data['sent_at']),
            status=EmailStatus(data['status']),
            events=events,
            template_used=data.get('template_used'),
            campaign_id=data.get('campaign_id'),
            open_count=data.get('open_count', 0),
            click_count=data.get('click_count', 0),
            size_bytes=data.get('size_bytes', 0),
            provider=data.get('provider', 'unknown'),
            device_type=data.get('device_type', 'unknown'),
            location=data.get('location')
        )

class EmailAnalytics:
    """Advanced email analytics and tracking system"""
    
    def __init__(self, analytics_file: str = "email_analytics.json"):
        self.analytics_file = analytics_file
        self.tracked_emails: Dict[str, EmailTrackingData] = {}
        self._load_analytics()
    
    def _load_analytics(self):
        """Load analytics data from file"""
        if os.path.exists(self.analytics_file):
            try:
                with open(self.analytics_file, 'r') as f:
                    data = json.load(f)
                    
                for email_id, email_data in data.get('tracked_emails', {}).items():
                    self.tracked_emails[email_id] = EmailTrackingData.from_dict(email_data)
                    
            except Exception as e:
                print(f"Error loading analytics: {e}")
    
    def _save_analytics(self):
        """Save analytics data to file"""
        try:
            data = {
                'tracked_emails': {
                    email_id: tracking_data.to_dict() 
                    for email_id, tracking_data in self.tracked_emails.items()
                },
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.analytics_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving analytics: {e}")
    
    def track_email_sent(self, 
                        recipient: str, 
                        subject: str, 
                        template_used: Optional[str] = None,
                        campaign_id: Optional[str] = None,
                        size_bytes: int = 0,
                        provider: str = "mock") -> str:
        """Track when an email is sent"""
        
        # Generate unique email ID
        email_id = self._generate_email_id(recipient, subject)
        
        tracking_data = EmailTrackingData(
            email_id=email_id,
            recipient=recipient,
            subject=subject,
            sent_at=datetime.now(),
            status=EmailStatus.SENT,
            events=[EmailEvent(datetime.now(), EmailStatus.SENT)],
            template_used=template_used,
            campaign_id=campaign_id,
            size_bytes=size_bytes,
            provider=provider
        )
        
        self.tracked_emails[email_id] = tracking_data
        self._save_analytics()
        
        return email_id
    
    def track_email_event(self, 
                         email_id: str, 
                         event_type: EmailStatus,
                         details: Optional[str] = None,
                         user_agent: Optional[str] = None,
                         ip_address: Optional[str] = None):
        """Track an email event (opened, clicked, etc.)"""
        
        if email_id not in self.tracked_emails:
            return False
        
        tracking_data = self.tracked_emails[email_id]
        
        # Add event
        event = EmailEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            details=details,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        tracking_data.events.append(event)
        tracking_data.status = event_type
        
        # Update counters
        if event_type == EmailStatus.OPENED:
            tracking_data.open_count += 1
        elif event_type == EmailStatus.CLICKED:
            tracking_data.click_count += 1
        
        # Extract device type from user agent
        if user_agent:
            tracking_data.device_type = self._extract_device_type(user_agent)
        
        self._save_analytics()
        return True
    
    def _generate_email_id(self, recipient: str, subject: str) -> str:
        """Generate unique email ID"""
        timestamp = datetime.now().isoformat()
        content = f"{recipient}_{subject}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _extract_device_type(self, user_agent: str) -> str:
        """Extract device type from user agent"""
        user_agent_lower = user_agent.lower()
        
        if any(mobile in user_agent_lower for mobile in ['mobile', 'android', 'iphone']):
            return 'mobile'
        elif any(tablet in user_agent_lower for tablet in ['ipad', 'tablet']):
            return 'tablet'
        else:
            return 'desktop'
    
    def get_email_performance(self, days: int = 30) -> Dict[str, Any]:
        """Get email performance metrics for the last N days"""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_emails = [
            email for email in self.tracked_emails.values()
            if email.sent_at >= cutoff_date
        ]
        
        if not recent_emails:
            return {
                'total_emails': 0,
                'delivery_rate': 0,
                'open_rate': 0,
                'click_rate': 0,
                'bounce_rate': 0
            }
        
        total_emails = len(recent_emails)
        delivered_emails = len([e for e in recent_emails if e.status not in [EmailStatus.BOUNCED, EmailStatus.FAILED]])
        opened_emails = len([e for e in recent_emails if e.open_count > 0])
        clicked_emails = len([e for e in recent_emails if e.click_count > 0])
        bounced_emails = len([e for e in recent_emails if e.status == EmailStatus.BOUNCED])
        
        return {
            'total_emails': total_emails,
            'delivery_rate': (delivered_emails / total_emails) * 100 if total_emails > 0 else 0,
            'open_rate': (opened_emails / delivered_emails) * 100 if delivered_emails > 0 else 0,
            'click_rate': (clicked_emails / delivered_emails) * 100 if delivered_emails > 0 else 0,
            'bounce_rate': (bounced_emails / total_emails) * 100 if total_emails > 0 else 0,
            'avg_opens_per_email': sum(e.open_count for e in recent_emails) / total_emails if total_emails > 0 else 0,
            'avg_clicks_per_email': sum(e.click_count for e in recent_emails) / total_emails if total_emails > 0 else 0
        }
    
    def get_template_performance(self) -> Dict[str, Dict[str, float]]:
        """Get performance metrics by template"""
        template_stats = {}
        
        for email in self.tracked_emails.values():
            if not email.template_used:
                continue
            
            template = email.template_used
            if template not in template_stats:
                template_stats[template] = {
                    'total': 0.0,      # Use float consistently
                    'opened': 0.0,     # Use float consistently
                    'clicked': 0.0,    # Use float consistently
                    'bounced': 0.0     # Use float consistently
                }
            
            template_stats[template]['total'] += 1.0
            
            if email.open_count > 0:
                template_stats[template]['opened'] += 1.0
            if email.click_count > 0:
                template_stats[template]['clicked'] += 1.0
            if email.status == EmailStatus.BOUNCED:
                template_stats[template]['bounced'] += 1.0
        
        # Calculate rates
        for template, stats in template_stats.items():
            total = stats['total']
            if total > 0:
                stats['open_rate'] = (stats['opened'] / total) * 100.0
                stats['click_rate'] = (stats['clicked'] / total) * 100.0
                stats['bounce_rate'] = (stats['bounced'] / total) * 100.0
            else:
                stats['open_rate'] = 0.0
                stats['click_rate'] = 0.0
                stats['bounce_rate'] = 0.0
        
        return template_stats
    
    def get_recipient_engagement(self) -> List[Dict[str, Any]]:
        """Get recipient engagement statistics"""
        recipient_stats = {}
        
        for email in self.tracked_emails.values():
            recipient = email.recipient
            if recipient not in recipient_stats:
                recipient_stats[recipient] = {
                    'email_count': 0,
                    'total_opens': 0,
                    'total_clicks': 0,
                    'last_activity': None
                }
            
            stats = recipient_stats[recipient]
            stats['email_count'] += 1
            stats['total_opens'] += email.open_count
            stats['total_clicks'] += email.click_count
            
            # Update last activity
            if email.events:
                latest_event = max(email.events, key=lambda e: e.timestamp)
                if (not stats['last_activity'] or 
                    latest_event.timestamp > stats['last_activity']):
                    stats['last_activity'] = latest_event.timestamp
        
        # Convert to list and sort by engagement
        engagement_list = []
        for recipient, stats in recipient_stats.items():
            engagement_score = (stats['total_opens'] * 1 + stats['total_clicks'] * 2) / stats['email_count']
            engagement_list.append({
                'recipient': recipient,
                'engagement_score': round(engagement_score, 2),
                'email_count': stats['email_count'],
                'avg_opens': round(stats['total_opens'] / stats['email_count'], 2),
                'avg_clicks': round(stats['total_clicks'] / stats['email_count'], 2),
                'last_activity': stats['last_activity'].isoformat() if stats['last_activity'] else None
            })
        
        return sorted(engagement_list, key=lambda x: x['engagement_score'], reverse=True)
    
    def get_time_analysis(self) -> Dict[str, Any]:
        """Analyze best times to send emails"""
        hour_stats = {hour: {'sent': 0, 'opened': 0} for hour in range(24)}
        day_stats = {day: {'sent': 0, 'opened': 0} for day in range(7)}  # 0 = Monday
        
        for email in self.tracked_emails.values():
            # Hour analysis
            hour = email.sent_at.hour
            hour_stats[hour]['sent'] += 1
            if email.open_count > 0:
                hour_stats[hour]['opened'] += 1
            
            # Day analysis
            day = email.sent_at.weekday()
            day_stats[day]['sent'] += 1
            if email.open_count > 0:
                day_stats[day]['opened'] += 1
        
        # Calculate rates
        for hour_data in hour_stats.values():
            if hour_data['sent'] > 0:
                hour_data['open_rate'] = (hour_data['opened'] / hour_data['sent']) * 100
            else:
                hour_data['open_rate'] = 0
        
        for day_data in day_stats.values():
            if day_data['sent'] > 0:
                day_data['open_rate'] = (day_data['opened'] / day_data['sent']) * 100
            else:
                day_data['open_rate'] = 0
        
        # Find best times
        best_hour = max(hour_stats.items(), key=lambda x: x[1]['open_rate'])
        best_day = max(day_stats.items(), key=lambda x: x[1]['open_rate'])
        
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        return {
            'hourly_stats': hour_stats,
            'daily_stats': day_stats,
            'best_hour': {'hour': best_hour[0], 'open_rate': best_hour[1]['open_rate']},
            'best_day': {'day': day_names[best_day[0]], 'open_rate': best_day[1]['open_rate']}
        }
    
    def generate_report(self, days: int = 30) -> str:
        """Generate a comprehensive analytics report"""
        performance = self.get_email_performance(days)
        template_perf = self.get_template_performance()
        engagement = self.get_recipient_engagement()[:5]  # Top 5
        time_analysis = self.get_time_analysis()
        
        report = f"""
📊 **BUDDY Email Analytics Report - Last {days} Days**
{'=' * 60}

📈 **Overall Performance:**
• Total Emails Sent: {performance['total_emails']}
• Delivery Rate: {performance['delivery_rate']:.1f}%
• Open Rate: {performance['open_rate']:.1f}%
• Click Rate: {performance['click_rate']:.1f}%
• Bounce Rate: {performance['bounce_rate']:.1f}%

🎯 **Template Performance:**"""
        
        for template, stats in list(template_perf.items())[:3]:
            report += f"\n• {template}: {stats['open_rate']:.1f}% open rate ({stats['total']} emails)"
        
        report += f"""

👥 **Top Engaged Recipients:**"""
        
        for recipient_data in engagement:
            report += f"\n• {recipient_data['recipient']}: {recipient_data['engagement_score']} score"
        
        report += f"""

⏰ **Optimal Send Times:**
• Best Hour: {time_analysis['best_hour']['hour']}:00 ({time_analysis['best_hour']['open_rate']:.1f}% open rate)
• Best Day: {time_analysis['best_day']['day']} ({time_analysis['best_day']['open_rate']:.1f}% open rate)

💡 **Recommendations:**
• Focus on high-performing templates
• Engage with top recipients for feedback
• Schedule emails during optimal times
• Monitor bounce rates for list hygiene
"""
        
        return report
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get a summary of analytics data"""
        total_emails = len(self.tracked_emails)
        
        if total_emails == 0:
            return {'total_emails': 0, 'status': 'No data available'}
        
        status_counts = {}
        for email in self.tracked_emails.values():
            status = email.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        recent_performance = self.get_email_performance(7)  # Last 7 days
        
        return {
            'total_emails_tracked': total_emails,
            'status_breakdown': status_counts,
            'recent_performance': recent_performance,
            'templates_used': len(set(e.template_used for e in self.tracked_emails.values() if e.template_used)),
            'unique_recipients': len(set(e.recipient for e in self.tracked_emails.values()))
        }
