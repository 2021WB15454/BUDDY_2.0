"""
🎨 BUDDY 2.0 Enhanced Email Templates System
Smart templates with dynamic content generation
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import re

class EmailTemplateManager:
    """Advanced email template system with smart content generation"""
    
    def __init__(self, templates_file: str = "email_templates.json"):
        self.templates_file = templates_file
        self.templates = self._load_templates()
        
    def _load_templates(self) -> Dict[str, Any]:
        """Load email templates from file or create defaults"""
        if os.path.exists(self.templates_file):
            try:
                with open(self.templates_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading templates: {e}")
        
        # Default templates
        return {
            "meeting_reminder": {
                "subject": "📅 Reminder: {meeting_title}",
                "body": """Hi {recipient_name},

This is a friendly reminder about our upcoming meeting:

📅 **{meeting_title}**
🕐 Time: {meeting_time}
📍 Location: {meeting_location}
🎯 Agenda: {meeting_agenda}

Looking forward to seeing you there!

Best regards,
{sender_name}""",
                "variables": ["meeting_title", "meeting_time", "meeting_location", "meeting_agenda", "recipient_name", "sender_name"]
            },
            "project_update": {
                "subject": "📊 Project Update: {project_name}",
                "body": """Hi {recipient_name},

Here's the latest update on {project_name}:

✅ **Completed:**
{completed_tasks}

🚧 **In Progress:**
{in_progress_tasks}

🎯 **Next Steps:**
{next_steps}

📈 **Overall Status:** {project_status}

Let me know if you have any questions!

Best,
{sender_name}""",
                "variables": ["project_name", "completed_tasks", "in_progress_tasks", "next_steps", "project_status", "recipient_name", "sender_name"]
            },
            "follow_up": {
                "subject": "🔄 Following up on {topic}",
                "body": """Hi {recipient_name},

I wanted to follow up on our conversation about {topic}.

{follow_up_content}

Please let me know your thoughts when you have a chance.

Best regards,
{sender_name}""",
                "variables": ["topic", "follow_up_content", "recipient_name", "sender_name"]
            },
            "status_report": {
                "subject": "📋 {report_type} Status Report - {date}",
                "body": """Hi {recipient_name},

Here's the {report_type} status report for {date}:

📊 **Key Metrics:**
{key_metrics}

🎯 **Achievements:**
{achievements}

⚠️ **Issues/Concerns:**
{issues}

📅 **Upcoming Priorities:**
{priorities}

Full details are attached.

Best,
{sender_name}""",
                "variables": ["report_type", "date", "key_metrics", "achievements", "issues", "priorities", "recipient_name", "sender_name"]
            },
            "thank_you": {
                "subject": "🙏 Thank you - {reason}",
                "body": """Hi {recipient_name},

I wanted to take a moment to thank you for {reason}.

{thank_you_message}

Your {contribution} really made a difference!

With gratitude,
{sender_name}""",
                "variables": ["reason", "thank_you_message", "contribution", "recipient_name", "sender_name"]
            }
        }
    
    def save_templates(self):
        """Save templates to file"""
        try:
            with open(self.templates_file, 'w') as f:
                json.dump(self.templates, f, indent=2)
        except Exception as e:
            print(f"Error saving templates: {e}")
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific template"""
        return self.templates.get(template_name)
    
    def list_templates(self) -> List[str]:
        """List all available templates"""
        return list(self.templates.keys())
    
    def render_template(self, template_name: str, variables: Dict[str, str]) -> Dict[str, str]:
        """Render a template with provided variables"""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        # Add default variables
        default_vars = {
            "date": datetime.now().strftime("%B %d, %Y"),
            "time": datetime.now().strftime("%I:%M %p"),
            "sender_name": variables.get("sender_name", "BUDDY Assistant")
        }
        
        # Merge variables
        all_vars = {**default_vars, **variables}
        
        # Render subject and body
        subject = template["subject"].format(**all_vars)
        body = template["body"].format(**all_vars)
        
        return {
            "subject": subject,
            "body": body,
            "template_used": template_name
        }
    
    def create_custom_template(self, name: str, subject: str, body: str, variables: List[str]):
        """Create a new custom template"""
        self.templates[name] = {
            "subject": subject,
            "body": body,
            "variables": variables,
            "created": datetime.now().isoformat(),
            "custom": True
        }
        self.save_templates()
    
    def smart_template_suggestion(self, message: str) -> Optional[str]:
        """Suggest template based on message content"""
        message_lower = message.lower()
        
        # Template matching patterns
        patterns = {
            "meeting_reminder": ["meeting", "reminder", "appointment", "schedule"],
            "project_update": ["project", "update", "progress", "status"],
            "follow_up": ["follow up", "following up", "check in"],
            "status_report": ["report", "status", "weekly", "monthly"],
            "thank_you": ["thank", "thanks", "grateful", "appreciation"]
        }
        
        for template_name, keywords in patterns.items():
            if any(keyword in message_lower for keyword in keywords):
                return template_name
        
        return None

class EmailContentEnhancer:
    """AI-powered email content enhancement"""
    
    @staticmethod
    def enhance_subject(subject: str) -> str:
        """Enhance email subject with emojis and structure"""
        if not subject:
            return "📧 Message from BUDDY"
        
        # Add appropriate emoji based on content
        subject_lower = subject.lower()
        
        if any(word in subject_lower for word in ["urgent", "asap", "immediate"]):
            return f"🚨 {subject}"
        elif any(word in subject_lower for word in ["meeting", "appointment"]):
            return f"📅 {subject}"
        elif any(word in subject_lower for word in ["update", "progress"]):
            return f"📊 {subject}"
        elif any(word in subject_lower for word in ["question", "help"]):
            return f"❓ {subject}"
        elif any(word in subject_lower for word in ["thank", "thanks"]):
            return f"🙏 {subject}"
        else:
            return f"📧 {subject}"
    
    @staticmethod
    def format_email_body(body: str, recipient_name: Optional[str] = None) -> str:
        """Format and enhance email body"""
        if not body:
            return "Hello,\n\nI hope this message finds you well.\n\nBest regards,\nBUDDY Assistant"
        
        # Add greeting if not present
        if not any(greeting in body.lower()[:50] for greeting in ["hi", "hello", "dear", "hey"]):
            greeting = f"Hi {recipient_name}," if recipient_name else "Hello,"
            body = f"{greeting}\n\n{body}"
        
        # Add closing if not present
        if not any(closing in body.lower()[-100:] for closing in ["best", "regards", "sincerely", "thanks"]):
            body = f"{body}\n\nBest regards,\nBUDDY Assistant"
        
        return body
    
    @staticmethod
    def extract_action_items(body: str) -> List[str]:
        """Extract action items from email body"""
        action_patterns = [
            r"(?:action item|todo|task):\s*(.+)",
            r"(?:please|could you|can you)\s+(.+?)(?:\.|$)",
            r"(?:need to|should|must)\s+(.+?)(?:\.|$)"
        ]
        
        action_items = []
        for pattern in action_patterns:
            matches = re.finditer(pattern, body, re.IGNORECASE)
            action_items.extend([match.group(1).strip() for match in matches])
        
        return action_items[:5]  # Limit to 5 items
