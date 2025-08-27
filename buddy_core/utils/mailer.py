"""
BUDDY Core Mailer System
Production-ready email handling with multiple providers
"""
import smtplib
import aiosmtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.message import EmailMessage
import os
from typing import Dict, Any, Optional
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    logger.info("⚠️  SendGrid not available. Install with: pip install sendgrid")

class AsyncMailer:
    """SMTP mailer using asyncio/aiosmtplib for production email sending."""
    
    def __init__(self, smtp_server="smtp.gmail.com", port=587, username=None, password=None):
        self.smtp_server = smtp_server
        self.port = port
        self.username = username
        self.password = password
        self.provider = "SMTP"
        
    async def send_mail(self, to_email: str, subject: str, body: str, from_email: Optional[str] = None) -> Dict[str, Any]:
        """Send email via SMTP with asyncio support."""
        try:
            msg = MIMEText(body, "plain")
            msg["Subject"] = subject
            msg["From"] = from_email or self.username
            msg["To"] = to_email

            # Use basic SMTP instead of aiosmtplib for compatibility
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._send_smtp_sync, msg)
            
            return {
                "status": "sent",
                "provider": "SMTP",
                "to": to_email,
                "subject": subject,
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"SMTP send error: {e}")
            return {
                "status": "failed",
                "provider": "SMTP",
                "to": to_email,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "success": False
            }
    
    def _send_smtp_sync(self, msg):
        """Synchronous SMTP sending for thread execution."""
        server = smtplib.SMTP(self.smtp_server, self.port)
        server.starttls()
        if self.username and self.password:
            server.login(self.username, self.password)
        server.send_message(msg)
        server.quit()
        return True
        
    # Legacy method for backward compatibility
    async def send_email(self, from_address: str, to_address: str, 
                        subject: str, body: str, html_body: str = None) -> Dict:
        """Legacy send_email method for backward compatibility"""
        return await self.send_mail(to_address, subject, body, from_address)


class MockMailer:
    """Mock mailer for testing and development"""
    
    def __init__(self):
        self.sent_emails = []
        self.provider = "Mock"
        
    async def send_mail(self, to_email: str, subject: str, body: str, from_email: Optional[str] = None) -> Dict[str, Any]:
        """Mock email sending for development and testing."""
        email_data = {
            "to": to_email,
            "from": from_email or "buddy@assistant.ai",
            "subject": subject,
            "body": body,
            "timestamp": datetime.now().isoformat()
        }
        
        self.sent_emails.append(email_data)
        
        print(f"📧 [MOCK EMAIL SENT]")
        print(f"   To: {to_email}")
        print(f"   From: {from_email or 'buddy@assistant.ai'}")
        print(f"   Subject: {subject}")
        print(f"   Body: {body[:100]}{'...' if len(body) > 100 else ''}")
        print(f"   Timestamp: {email_data['timestamp']}")
        
        return {
            "status": "mocked",
            "provider": "Mock",
            "to": to_email,
            "subject": subject,
            "timestamp": email_data['timestamp'],
            "success": True,
            "mock_data": email_data
        }
    
    async def send_email(self, from_address: str, to_address: str, 
                        subject: str, body: str, html_body: str = None) -> Dict:
        """Legacy send_email method for backward compatibility"""
        return await self.send_mail(to_address, subject, body, from_address)
    
    def get_sent_emails(self) -> list:
        """Get list of sent emails for testing"""
        return self.sent_emails
    
    def clear_sent_emails(self):
        """Clear sent email history"""
        self.sent_emails.clear()


class SendGridMailer:
    """SendGrid email sender (optional)"""
    
    def __init__(self, api_key: str, from_email: str):
        self.api_key = api_key
        self.from_email = from_email
        
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail
            self.sg = sendgrid.SendGridAPIClient(api_key=api_key)
            self.Mail = Mail
            self.available = True
        except ImportError:
            logger.warning("SendGrid not available - install sendgrid package")
            self.available = False
    
    async def send_mail(self, to_email: str, subject: str, body: str, from_email: Optional[str] = None) -> Dict[str, Any]:
        """Send email via SendGrid API with standard interface"""
        result = await self.send_email(from_email or self.from_email, to_email, subject, body)
        # Add success field for compatibility
        result["success"] = result.get("sendgrid_status", 0) == 202
        return result
    
    async def send_email(self, from_address: str, to_address: str, 
                        subject: str, body: str, html_body: str = None) -> Dict:
        """Send email via SendGrid API"""
        
        if not self.available:
            raise Exception("SendGrid not available - install sendgrid package")
        
        try:
            message = self.Mail(
                from_email=from_address or self.from_email,
                to_emails=to_address,
                subject=subject,
                plain_text_content=body,
                html_content=html_body
            )
            
            # Send in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.sg.send,
                message
            )
            
            return {
                "status": "sent",
                "id": response.headers.get('X-Message-Id', f"sg-{int(__import__('time').time())}"),
                "to": to_address,
                "subject": subject,
                "sendgrid_status": response.status_code
            }
            
        except Exception as e:
            logger.error(f"SendGrid send error: {e}")
            raise Exception(f"SendGrid error: {str(e)}")


def create_mailer(provider: str = "mock", **kwargs):
    """
    Factory function to create appropriate mailer instance.
    
    Args:
        provider: "smtp", "sendgrid", or "mock" (default)
        **kwargs: Provider-specific configuration
        
    Returns:
        Mailer instance
    """
    if provider.lower() == "smtp":
        return AsyncMailer(
            smtp_server=kwargs.get('smtp_server', 'smtp.gmail.com'),
            port=kwargs.get('port', 587),
            username=kwargs.get('username'),
            password=kwargs.get('password')
        )
    elif provider.lower() == "sendgrid":
        return SendGridMailer(
            api_key=kwargs.get('api_key'),
            from_email=kwargs.get('from_email', 'buddy@assistant.ai')
        )
    else:
        return MockMailer()


class EmailComposer:
    """Helper class for composing emails with templates and parsing."""
    
    @staticmethod
    def parse_email_intent(user_input: str) -> Dict[str, Any]:
        """
        Parse user input for email components.
        This is a simple implementation - could be enhanced with NLP.
        """
        # Simple parsing logic
        input_lower = user_input.lower()
        
        # Extract recipient patterns
        recipient = None
        if "to " in input_lower:
            parts = user_input.split("to ", 1)
            if len(parts) > 1:
                recipient_part = parts[1].split()[0]
                if "@" in recipient_part:
                    recipient = recipient_part
                else:
                    recipient = f"{recipient_part}@example.com"  # Default domain
        
        # Extract subject patterns
        subject = "Message from BUDDY"
        if "subject:" in input_lower:
            parts = user_input.split("subject:", 1)
            if len(parts) > 1:
                subject = parts[1].strip()
        
        # Body is the remaining content
        body = user_input
        
        return {
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "parsed_successfully": recipient is not None
        }
    
    @staticmethod
    def create_template_email(template_name: str, **kwargs) -> Dict[str, str]:
        """Create email from predefined templates."""
        templates = {
            "meeting_reminder": {
                "subject": "Meeting Reminder - {meeting_title}",
                "body": "Hi {recipient_name},\n\nThis is a reminder about our meeting: {meeting_title}\nTime: {meeting_time}\nLocation: {meeting_location}\n\nBest regards,\nBUDDY Assistant"
            },
            "task_assignment": {
                "subject": "Task Assignment - {task_title}",
                "body": "Hi {recipient_name},\n\nYou have been assigned a new task: {task_title}\nDescription: {task_description}\nDue Date: {due_date}\n\nBest regards,\nBUDDY Assistant"
            },
            "general": {
                "subject": "{subject}",
                "body": "{body}"
            }
        }
        
        template = templates.get(template_name, templates["general"])
        
        return {
            "subject": template["subject"].format(**kwargs),
            "body": template["body"].format(**kwargs)
        }


class BUDDYEmailHandler:
    """Production-ready email handling system for BUDDY with advanced NLP parsing."""
    
    def __init__(self, provider: str = "mock", **mailer_kwargs):
        self.mailer = create_mailer(provider, **mailer_kwargs)
        self.composer = EmailComposer()
        self.provider = provider
        
    async def handle_email_request(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle complete email request from user input with advanced parsing.
        
        Examples:
        - "send a mail" → Ask for recipient
        - "send mail to john@company.com" → Parse recipient and send
        - "email Alice: meeting tomorrow" → Parse recipient and content
        - "send john@test.com subject: Project Update The project is on track" → Full parsing
        
        Args:
            user_input: User's email request
            context: Additional context (user preferences, contacts, etc.)
            
        Returns:
            Response with email status and details
        """
        context = context or {}
        
        # Advanced parsing of email components
        parsed = self._advanced_email_parsing(user_input)
        
        # Get recipient from context if not parsed
        recipient = parsed["recipient"] or context.get("default_email", "demo@example.com")
        
        # Use parsed or intelligent defaults
        subject = parsed["subject"] or "Message from BUDDY Assistant"
        body = parsed["body"] or user_input
        
        # If no recipient found, ask for it
        if not parsed["recipient"] and not context.get("default_email"):
            return {
                "response": "📧 I'd love to help you send an email! Who should I send it to? Please provide the recipient's email address or contact name.",
                "email_result": {"status": "needs_recipient", "success": False},
                "parsed_input": parsed,
                "success": False
            }
        
        try:
            # Send the email using the mailer
            result = await self.mailer.send_mail(
                to_email=recipient,
                subject=subject,
                body=body,
                from_email=context.get("user_email", "buddy@assistant.ai")
            )
            
            # Create intelligent response for user
            if result.get("success", True):  # Default to True for backward compatibility
                response = f"📧 Email sent successfully!"
                response += f"\n   To: {recipient}"
                response += f"\n   Subject: {subject}"
                response += f"\n   Provider: {result.get('provider', 'Unknown')}"
                
                if self.provider == "mock":
                    response += "\n\n🔧 Development Mode: Email was mocked for testing."
                    response += f"\n📝 Content preview: {body[:100]}{'...' if len(body) > 100 else ''}"
            else:
                response = f"❌ Failed to send email to {recipient}"
                response += f"\nError: {result.get('error', 'Unknown error')}"
                
            return {
                "response": response,
                "email_result": result,
                "parsed_input": parsed,
                "success": result.get("success", True)
            }
            
        except Exception as e:
            error_response = f"❌ Email system error: {str(e)}"
            return {
                "response": error_response,
                "email_result": {"status": "error", "error": str(e), "success": False},
                "parsed_input": parsed,
                "success": False
            }
    
    def _advanced_email_parsing(self, user_input: str) -> Dict[str, Any]:
        """
        Advanced email parsing with better natural language understanding.
        
        Patterns supported:
        - "send mail to john@example.com"
        - "email Alice about meeting"
        - "send john@test.com subject: Update The project is ready"
        - "compose email to team@company.com: Project status update"
        """
        import re
        
        result = {
            "recipient": None,
            "subject": None,
            "body": user_input,
            "parsed_successfully": False
        }
        
        # Clean input
        text = user_input.strip()
        text_lower = text.lower()
        
        # Pattern 1: Extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            result["recipient"] = emails[0]  # Use first email found
            result["parsed_successfully"] = True
        
        # Pattern 2: "to [name/email]" patterns
        to_patterns = [
            r'(?:send|email|mail).*?to\s+([^\s:]+@[^\s:]+)',  # "send to email@domain.com"
            r'(?:send|email|mail).*?to\s+([A-Za-z]+)',        # "send to Alice"
            r'email\s+([A-Za-z]+)',                           # "email John"
        ]
        
        for pattern in to_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                potential_recipient = match.group(1)
                if '@' in potential_recipient:
                    result["recipient"] = potential_recipient
                else:
                    # Convert name to email (simple heuristic)
                    result["recipient"] = f"{potential_recipient.lower()}@example.com"
                result["parsed_successfully"] = True
                break
        
        # Pattern 3: Subject extraction
        subject_patterns = [
            r'subject:\s*([^:\n]+)',                    # "subject: Meeting Tomorrow"
            r'(?:send|email|mail).*?:\s*([^:\n]+)',     # "send john@test.com: Update"
            r'about\s+([^:\n]+)',                       # "email Alice about project"
        ]
        
        for pattern in subject_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["subject"] = match.group(1).strip()
                break
        
        # Pattern 4: Body extraction (remaining text after removing parsed parts)
        body = text
        
        # Remove "send mail to" type prefixes
        prefixes_to_remove = [
            r'^(?:send|email|mail)\s+(?:a\s+)?(?:mail|email)?\s+to\s+[^\s:]+\s*:?\s*',
            r'^(?:send|email|mail)\s+[^\s:]+\s*:?\s*',
            r'^(?:compose|write)\s+(?:an?\s+)?(?:email|mail)\s*(?:to\s+[^\s:]+)?\s*:?\s*'
        ]
        
        for prefix_pattern in prefixes_to_remove:
            body = re.sub(prefix_pattern, '', body, flags=re.IGNORECASE).strip()
        
        # Remove subject if it was extracted
        if result["subject"]:
            body = re.sub(f'subject:\\s*{re.escape(result["subject"])}\\s*', '', body, flags=re.IGNORECASE).strip()
        
        # If body is empty or just the recipient, use original input
        if not body or body == result["recipient"]:
            body = user_input
        
        result["body"] = body
        
        return result


# Export main classes and functions
__all__ = [
    'AsyncMailer', 'MockMailer', 'SendGridMailer', 'create_mailer',
    'EmailComposer', 'BUDDYEmailHandler'
]
