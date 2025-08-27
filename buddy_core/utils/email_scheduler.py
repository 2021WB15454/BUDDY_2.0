"""
⏰ BUDDY 2.0 Enhanced Email Scheduler
Smart email scheduling with recurring patterns and time zone support
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncio
from dataclasses import dataclass
from enum import Enum
import threading
import time

class ScheduleFrequency(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

@dataclass
class ScheduledEmail:
    id: str
    recipient: str
    subject: str
    body: str
    scheduled_time: datetime
    frequency: ScheduleFrequency
    template_name: Optional[str] = None
    template_vars: Optional[Dict[str, str]] = None
    timezone: str = "UTC"
    max_occurrences: Optional[int] = None
    current_occurrence: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None  # Allow None
    last_sent: Optional[datetime] = None
    next_send: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.next_send is None:
            self.next_send = self.scheduled_time

class EmailScheduler:
    """Advanced email scheduling system"""
    
    def __init__(self, schedules_file: str = "email_schedules.json"):
        self.schedules_file = schedules_file
        self.scheduled_emails: Dict[str, ScheduledEmail] = {}
        self.is_running = False
        self.scheduler_thread = None
        self._load_schedules()
    
    def _load_schedules(self):
        """Load scheduled emails from file"""
        if os.path.exists(self.schedules_file):
            try:
                with open(self.schedules_file, 'r') as f:
                    data = json.load(f)
                    
                for email_id, email_data in data.get('scheduled_emails', {}).items():
                    # Convert datetime strings back to datetime objects
                    email_data['scheduled_time'] = datetime.fromisoformat(email_data['scheduled_time'])
                    email_data['created_at'] = datetime.fromisoformat(email_data['created_at'])
                    
                    if email_data.get('last_sent'):
                        email_data['last_sent'] = datetime.fromisoformat(email_data['last_sent'])
                    if email_data.get('next_send'):
                        email_data['next_send'] = datetime.fromisoformat(email_data['next_send'])
                    
                    email_data['frequency'] = ScheduleFrequency(email_data['frequency'])
                    
                    self.scheduled_emails[email_id] = ScheduledEmail(**email_data)
                    
            except Exception as e:
                print(f"Error loading schedules: {e}")
    
    def _save_schedules(self):
        """Save scheduled emails to file"""
        try:
            data = {
                'scheduled_emails': {},
                'last_updated': datetime.now().isoformat()
            }
            
            for email_id, scheduled_email in self.scheduled_emails.items():
                email_dict = {
                    'id': scheduled_email.id,
                    'recipient': scheduled_email.recipient,
                    'subject': scheduled_email.subject,
                    'body': scheduled_email.body,
                    'scheduled_time': scheduled_email.scheduled_time.isoformat(),
                    'frequency': scheduled_email.frequency.value,
                    'template_name': scheduled_email.template_name,
                    'template_vars': scheduled_email.template_vars,
                    'timezone': scheduled_email.timezone,
                    'max_occurrences': scheduled_email.max_occurrences,
                    'current_occurrence': scheduled_email.current_occurrence,
                    'is_active': scheduled_email.is_active,
                    'created_at': scheduled_email.created_at.isoformat(),
                    'last_sent': scheduled_email.last_sent.isoformat() if scheduled_email.last_sent else None,
                    'next_send': scheduled_email.next_send.isoformat() if scheduled_email.next_send else None
                }
                data['scheduled_emails'][email_id] = email_dict
            
            with open(self.schedules_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving schedules: {e}")
    
    def schedule_email(self, 
                      recipient: str, 
                      subject: str, 
                      body: str, 
                      scheduled_time: datetime,
                      frequency: ScheduleFrequency = ScheduleFrequency.ONCE,
                      **kwargs) -> str:
        """Schedule an email for future delivery"""
        
        email_id = f"schedule_{int(time.time())}_{len(self.scheduled_emails)}"
        
        scheduled_email = ScheduledEmail(
            id=email_id,
            recipient=recipient,
            subject=subject,
            body=body,
            scheduled_time=scheduled_time,
            frequency=frequency,
            **kwargs
        )
        
        self.scheduled_emails[email_id] = scheduled_email
        self._save_schedules()
        
        # Start scheduler if not running
        if not self.is_running:
            self.start_scheduler()
        
        return email_id
    
    def cancel_scheduled_email(self, email_id: str) -> bool:
        """Cancel a scheduled email"""
        if email_id in self.scheduled_emails:
            self.scheduled_emails[email_id].is_active = False
            self._save_schedules()
            return True
        return False
    
    def get_scheduled_emails(self, active_only: bool = True) -> List[ScheduledEmail]:
        """Get all scheduled emails"""
        emails = list(self.scheduled_emails.values())
        if active_only:
            emails = [email for email in emails if email.is_active]
        return sorted(emails, key=lambda x: x.next_send or x.scheduled_time)
    
    def get_upcoming_emails(self, hours: int = 24) -> List[ScheduledEmail]:
        """Get emails scheduled for the next X hours"""
        cutoff_time = datetime.now() + timedelta(hours=hours)
        upcoming = []
        
        for email in self.scheduled_emails.values():
            if (email.is_active and 
                email.next_send and 
                email.next_send <= cutoff_time):
                upcoming.append(email)
        
        return sorted(upcoming, key=lambda x: x.next_send)
    
    def _calculate_next_send_time(self, scheduled_email: ScheduledEmail) -> Optional[datetime]:
        """Calculate next send time for recurring emails"""
        if scheduled_email.frequency == ScheduleFrequency.ONCE:
            return None
        
        if not scheduled_email.last_sent:
            return scheduled_email.scheduled_time
        
        last_sent = scheduled_email.last_sent
        
        if scheduled_email.frequency == ScheduleFrequency.DAILY:
            return last_sent + timedelta(days=1)
        elif scheduled_email.frequency == ScheduleFrequency.WEEKLY:
            return last_sent + timedelta(weeks=1)
        elif scheduled_email.frequency == ScheduleFrequency.MONTHLY:
            # Approximate monthly (30 days)
            return last_sent + timedelta(days=30)
        elif scheduled_email.frequency == ScheduleFrequency.YEARLY:
            return last_sent + timedelta(days=365)
        
        return None
    
    def start_scheduler(self):
        """Start the email scheduler"""
        if self.is_running:
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        print("📅 Email scheduler started")
    
    def stop_scheduler(self):
        """Stop the email scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        print("📅 Email scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                self._check_and_send_emails()
                time.sleep(60)  # Check every minute
            except Exception as e:
                print(f"Scheduler error: {e}")
                time.sleep(60)
    
    def _check_and_send_emails(self):
        """Check for emails that need to be sent"""
        now = datetime.now()
        emails_to_send = []
        
        for email in self.scheduled_emails.values():
            if (email.is_active and 
                email.next_send and 
                email.next_send <= now):
                emails_to_send.append(email)
        
        for email in emails_to_send:
            self._send_scheduled_email(email)
    
    def _send_scheduled_email(self, scheduled_email: ScheduledEmail):
        """Send a scheduled email"""
        try:
            # This would integrate with the actual email sender
            print(f"📧 Sending scheduled email to {scheduled_email.recipient}")
            print(f"   Subject: {scheduled_email.subject}")
            
            # Update email tracking
            scheduled_email.last_sent = datetime.now()
            scheduled_email.current_occurrence += 1
            
            # Calculate next send time
            if scheduled_email.frequency != ScheduleFrequency.ONCE:
                next_send = self._calculate_next_send_time(scheduled_email)
                
                # Check if we've reached max occurrences
                if (scheduled_email.max_occurrences and 
                    scheduled_email.current_occurrence >= scheduled_email.max_occurrences):
                    scheduled_email.is_active = False
                    scheduled_email.next_send = None
                else:
                    scheduled_email.next_send = next_send
            else:
                # One-time email, deactivate
                scheduled_email.is_active = False
                scheduled_email.next_send = None
            
            self._save_schedules()
            
        except Exception as e:
            print(f"Error sending scheduled email {scheduled_email.id}: {e}")
    
    def parse_schedule_time(self, time_str: str) -> Optional[datetime]:
        """Parse natural language time strings"""
        time_str = time_str.lower().strip()
        now = datetime.now()
        
        # Today/Tomorrow patterns
        if "today" in time_str:
            base_date = now.date()
        elif "tomorrow" in time_str:
            base_date = (now + timedelta(days=1)).date()
        elif "next week" in time_str:
            base_date = (now + timedelta(weeks=1)).date()
        else:
            base_date = now.date()
        
        # Time patterns
        import re
        time_patterns = [
            r"(\d{1,2}):(\d{2})\s*(am|pm)?",
            r"(\d{1,2})\s*(am|pm)",
            r"at\s*(\d{1,2}):(\d{2})",
            r"at\s*(\d{1,2})\s*(am|pm)"
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, time_str)
            if match:
                groups = match.groups()
                hour = int(groups[0])
                minute = int(groups[1]) if len(groups) > 1 and groups[1] else 0
                
                # Handle AM/PM
                if len(groups) > 2 and groups[-1]:
                    if groups[-1] == 'pm' and hour != 12:
                        hour += 12
                    elif groups[-1] == 'am' and hour == 12:
                        hour = 0
                
                return datetime.combine(base_date, datetime.min.time().replace(hour=hour, minute=minute))
        
        # Default to current time + 1 hour
        return now + timedelta(hours=1)
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        active_emails = [e for e in self.scheduled_emails.values() if e.is_active]
        
        return {
            'total_scheduled': len(self.scheduled_emails),
            'active_schedules': len(active_emails),
            'upcoming_24h': len(self.get_upcoming_emails(24)),
            'recurring_schedules': len([e for e in active_emails if e.frequency != ScheduleFrequency.ONCE]),
            'is_running': self.is_running
        }
