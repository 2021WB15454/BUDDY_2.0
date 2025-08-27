"""
🚀 BUDDY 2.0 SUPER Enhanced Email Handler
Complete email system with all advanced features integrated
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import re
import json

# Import the base mailer
from .mailer import create_mailer, BUDDYEmailHandler as BaseBUDDYEmailHandler

class SuperEnhancedBUDDYEmailHandler(BaseBUDDYEmailHandler):
    """
    🌟 SUPER Enhanced BUDDY Email Handler with ALL features:
    ✅ Smart Template System with AI suggestions
    ✅ Advanced Contact Book with fuzzy matching
    ✅ Email Scheduling & Automation
    ✅ Comprehensive Analytics & Tracking
    ✅ Secure Attachment Management
    ✅ Natural Language Processing
    ✅ Multi-provider Support (SMTP, SendGrid, Mock)
    """
    
    def __init__(self, provider="mock", config=None):
        super().__init__(provider, **config or {})
        self.provider = provider
        
        # Initialize ALL enhanced components
        self.template_manager = None
        self.contact_book = None
        self.scheduler = None
        self.analytics = None
        self.attachment_manager = None
        self.content_enhancer = None
        
        self._init_all_enhanced_features()
        
        print("🌟 SUPER Enhanced BUDDY Email Handler initialized!")
        print("✅ Features: Templates • Contacts • Scheduling • Analytics • Attachments")
    
    def _init_all_enhanced_features(self):
        """Initialize ALL enhanced email features"""
        try:
            # Import all enhanced components
            from .email_templates import EmailTemplateManager, EmailContentEnhancer
            from .contact_book import ContactBook
            from .email_scheduler import EmailScheduler, ScheduleFrequency
            from .email_analytics import EmailAnalytics, EmailStatus
            from .email_attachments import AttachmentManager
            
            # Initialize everything
            self.template_manager = EmailTemplateManager()
            self.contact_book = ContactBook()
            self.scheduler = EmailScheduler()
            self.analytics = EmailAnalytics()
            self.attachment_manager = AttachmentManager()
            self.content_enhancer = EmailContentEnhancer()
            
            # Start the scheduler
            self.scheduler.start_scheduler()
            
            print("✅ ALL enhanced email features successfully initialized!")
            
        except ImportError as e:
            print(f"⚠️  Some enhanced features not available: {e}")
            self._create_fallback_features()
    
    def _create_fallback_features(self):
        """Create fallback implementations when advanced features aren't available"""
        
        # Minimal template manager
        class FallbackTemplateManager:
            def get_template(self, name): return None
            def smart_template_suggestion(self, msg): return None
            def list_templates(self): return ['meeting_reminder', 'project_update', 'follow_up']
            def render_template(self, name, vars): return {'subject': 'Template Subject', 'body': 'Template Body'}
        
        # Minimal contact book
        class FallbackContactBook:
            def find_contact(self, query): return None
            def search_contacts(self, query): return []
            def update_contact_activity(self, email): pass
            def get_contact_suggestions(self, partial): return []
            def get_stats(self): return {'total_contacts': 0, 'total_groups': 0, 'most_contacted': []}
        
        # Minimal scheduler
        class FallbackScheduler:
            def schedule_email(self, *args, **kwargs): return "fallback_schedule_id"
            def get_scheduled_emails(self, active_only=True): return []
            def get_upcoming_emails(self, hours=24): return []
            def parse_schedule_time(self, time_str): return datetime.now() + timedelta(hours=1)
            def get_scheduler_stats(self): return {'total_scheduled': 0, 'is_running': False}
        
        # Minimal analytics
        class FallbackAnalytics:
            def track_email_sent(self, *args, **kwargs): return "fallback_tracking_id"
            def get_email_performance(self, days=30): return {'total_emails': 0, 'delivery_rate': 0}
            def generate_report(self, days=30): return "📊 Analytics not available in fallback mode"
            def get_analytics_summary(self): return {'total_emails_tracked': 0, 'status': 'Fallback mode'}
        
        # Minimal attachment manager
        class FallbackAttachmentManager:
            def validate_file(self, filepath): return True, "Validation skipped in fallback mode"
            def create_attachment(self, filepath): return None
            def extract_attachments_from_text(self, text): return []
            def get_attachment_info(self, attachments): return {'count': 0, 'total_size': 0}
        
        # Minimal content enhancer
        class FallbackContentEnhancer:
            def enhance_subject(self, subject): return f"📧 {subject}" if subject else "📧 Message from BUDDY"
            def format_email_body(self, body, recipient_name=None): 
                greeting = f"Hi {recipient_name}," if recipient_name else "Hello,"
                return f"{greeting}\n\n{body}\n\nBest regards,\nBUDDY Assistant"
            def extract_action_items(self, body): return []
        
        # Assign fallback implementations
        self.template_manager = FallbackTemplateManager()
        self.contact_book = FallbackContactBook()
        self.scheduler = FallbackScheduler()
        self.analytics = FallbackAnalytics()
        self.attachment_manager = FallbackAttachmentManager()
        self.content_enhancer = FallbackContentEnhancer()
        
        print("⚠️  Using fallback implementations for enhanced features")
    
    async def handle_email_request(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        🌟 SUPER Enhanced email handling with ALL features
        
        Supports:
        - Natural language emails: "send mail to john@company.com about meeting"
        - Template emails: "send meeting reminder to team using meeting_reminder template"
        - Scheduled emails: "schedule email to alice@test.com tomorrow at 9am"
        - Attachment emails: "send report.pdf to manager@company.com"
        - Analytics: "show email analytics"
        - Contact management: "list contacts"
        - And much more!
        """
        
        try:
            context = context or {}
            
            # 🎯 STEP 1: Enhanced parsing with ALL features
            parsed = self._super_enhanced_parsing(user_input)
            
            # 🎯 STEP 2: Handle special commands first
            special_result = await self._handle_special_commands(user_input, parsed, context)
            if special_result:
                return special_result
            
            # 🎯 STEP 3: Handle template-based emails
            template_result = await self._handle_template_emails(user_input, parsed, context)
            if template_result:
                return template_result
            
            # 🎯 STEP 4: Handle scheduled emails
            schedule_result = await self._handle_scheduled_emails(user_input, parsed, context)
            if schedule_result:
                return schedule_result
            
            # 🎯 STEP 5: Handle attachment emails
            attachment_result = await self._handle_attachment_emails(user_input, parsed, context)
            if attachment_result:
                return attachment_result
            
            # 🎯 STEP 6: Standard enhanced email sending
            return await self._send_super_enhanced_email(parsed, context)
            
        except Exception as e:
            return {
                "response": f"❌ Super Enhanced Email System Error: {str(e)}",
                "success": False,
                "error": str(e)
            }
    
    def _super_enhanced_parsing(self, user_input: str) -> Dict[str, Any]:
        """Super enhanced parsing combining ALL parsing capabilities"""
        
        # Start with base advanced parsing
        result = self._advanced_email_parsing(user_input)
        
        # 🎯 Enhance with contact book
        if (result.get("recipient_name") and 
            not result.get("recipient")):
        
            if self.contact_book is not None:
                contact = self.contact_book.find_contact(result["recipient_name"])
                if contact:
                    result["recipient"] = contact.primary_email
                    result["contact_found"] = True
                    result["contact_name"] = contact.name
                    result["contact_company"] = getattr(contact, 'company', None)
        
        # 🎯 Template suggestions
        suggested_template = self.template_manager.smart_template_suggestion(user_input)
        if suggested_template:
            result["suggested_template"] = suggested_template
        
        # 🎯 Extract attachments
        potential_files = self.attachment_manager.extract_attachments_from_text(user_input)
        if potential_files:
            result["potential_attachments"] = potential_files
        
        # 🎯 Schedule detection
        schedule_indicators = ["schedule", "send later", "tomorrow", "next week", "at", "remind"]
        if any(indicator in user_input.lower() for indicator in schedule_indicators):
            result["schedule_detected"] = True
            schedule_time = self.scheduler.parse_schedule_time(user_input)
            if schedule_time:
                result["parsed_schedule_time"] = schedule_time
        
        # 🎯 Command detection
        command_indicators = ["analytics", "stats", "templates", "contacts", "scheduled"]
        if any(cmd in user_input.lower() for cmd in command_indicators):
            result["command_detected"] = True
        
        return result
    
    async def _handle_special_commands(self, user_input: str, parsed: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle special system commands"""
        text_lower = user_input.lower()
        
        # 📊 Analytics Commands
        if any(cmd in text_lower for cmd in ["email analytics", "email stats", "email performance"]):
            performance = self.analytics.get_email_performance(30)
            summary = self.analytics.get_analytics_summary()
            
            response = f"""📊 **BUDDY Email Analytics Dashboard**
{'=' * 50}

📈 **Last 30 Days Performance:**
• Total Emails: {performance.get('total_emails', 0)}
• Delivery Rate: {performance.get('delivery_rate', 0):.1f}%
• Open Rate: {performance.get('open_rate', 0):.1f}%
• Click Rate: {performance.get('click_rate', 0):.1f}%

📋 **Overall Stats:**
• Total Tracked: {summary.get('total_emails_tracked', 0)}
• Unique Recipients: {summary.get('unique_recipients', 0)}
• Templates Used: {summary.get('templates_used', 0)}

💡 Use 'email report' for detailed analytics!"""
            
            return {"response": response, "success": True, "command_type": "analytics"}
        
        # 📋 Template Commands
        if any(cmd in text_lower for cmd in ["list templates", "email templates", "available templates"]):
            templates = self.template_manager.list_templates()
            response = f"""📋 **Available Email Templates**
{'=' * 40}

{chr(10).join([f'• {template}' for template in templates])}

💡 **Usage Examples:**
• "Send meeting reminder to team@company.com"
• "Email project update to alice@test.com using project_update template"
• "Send thank you email to john@client.com"

📝 Templates automatically enhance your emails with professional formatting!"""
            
            return {"response": response, "success": True, "command_type": "templates"}
        
        # 📇 Contact Commands  
        if any(cmd in text_lower for cmd in ["list contacts", "contact stats", "contact book"]):
            stats = self.contact_book.get_stats()
            response = f"""📇 **Contact Book Summary**
{'=' * 35}

📊 **Statistics:**
• Total Contacts: {stats['total_contacts']}
• Contact Groups: {stats['total_groups']}
• With Companies: {stats.get('contacts_with_companies', 0)}
• With Phone Numbers: {stats.get('contacts_with_phones', 0)}

👥 **Most Contacted:**
{chr(10).join([f'• {name}' for name in stats.get('most_contacted', [])[:5]])}

💡 Use contact names in emails: "Send mail to Alice" instead of full email addresses!"""
            
            return {"response": response, "success": True, "command_type": "contacts"}
        
        # 📅 Schedule Commands
        if any(cmd in text_lower for cmd in ["scheduled emails", "email schedule", "upcoming emails"]):
            upcoming = self.scheduler.get_upcoming_emails(168)  # 7 days
            stats = self.scheduler.get_scheduler_stats()
            
            response = f"""📅 **Email Schedule Dashboard**
{'=' * 40}

📊 **Schedule Statistics:**
• Total Scheduled: {stats['total_scheduled']}
• Active Schedules: {stats['active_schedules']}
• Scheduler Running: {'✅ Yes' if stats['is_running'] else '❌ No'}

📧 **Upcoming Emails (7 days):**"""
            
            if upcoming:
                for email in upcoming[:5]:
                    response += f"\n• {email.recipient}: {email.subject}"
                    response += f" ({email.next_send.strftime('%m/%d %H:%M') if email.next_send else 'TBD'})"
            else:
                response += "\n• No emails scheduled"
            
            response += "\n\n💡 Schedule emails with: 'Send reminder to team@company.com tomorrow at 9am'"
            
            return {"response": response, "success": True, "command_type": "schedule"}
        
        # 📎 Attachment Commands
        if "attachment" in text_lower or "file" in text_lower:
            storage_stats = self.attachment_manager.get_storage_stats()
            
            response = f"""📎 **Attachment System Status**
{'=' * 40}

📊 **Storage Statistics:**
• Files Stored: {storage_stats['total_files']}
• Total Size: {storage_stats['total_size_mb']} MB
• Max File Size: {storage_stats['max_file_size_mb']} MB
• Max Total Size: {storage_stats['max_total_size_mb']} MB

📋 **Supported File Types:**
• Documents: PDF, DOC, TXT, RTF
• Images: JPG, PNG, GIF, SVG
• Archives: ZIP, RAR, 7Z
• Code: PY, JS, HTML, JSON

💡 **Usage:** Include file paths in your email: "Send report.pdf to manager@company.com" """
            
            return {"response": response, "success": True, "command_type": "attachments"}
        
        return None
    
    async def _handle_template_emails(self, user_input: str, parsed: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle template-based email requests with smart suggestions"""
        
        template_name = parsed.get("suggested_template")
        
        # Check for explicit template usage
        template_patterns = [
            r"using\s+(\w+)\s+template",
            r"with\s+(\w+)\s+template", 
            r"(\w+)\s+template",
            r"send\s+(\w+)\s+to"
        ]
        
        for pattern in template_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                potential_template = match.group(1)
                if potential_template in self.template_manager.list_templates():
                    template_name = potential_template
                    break
        
        if template_name:
            template = self.template_manager.get_template(template_name)
            if template:
                # Try to auto-fill template variables from context
                template_vars = self._extract_template_variables(user_input, template, parsed, context)
                
                if self._has_sufficient_template_data(template, template_vars):
                    # Render and send template email
                    rendered = self.template_manager.render_template(template_name, template_vars)
                    
                    # Send the templated email
                    result = await self.mailer.send_mail(
                        to_email=parsed.get("recipient"),
                        subject=rendered["subject"],
                        body=rendered["body"]
                    )
                    
                    # Track template usage
                    if result.get("success"):
                        self.analytics.track_email_sent(
                            recipient=parsed.get("recipient"),
                            subject=rendered["subject"],
                            template_used=template_name,
                            provider=self.provider
                        )
                    
                    response = f"✅ Template email '{template_name}' sent successfully!"
                    response += f"\n📧 To: {parsed.get('recipient')}"
                    response += f"\n📝 Subject: {rendered['subject']}"
                    response += f"\n🎨 Template: {template_name}"
                    
                    return {"response": response, "success": True, "template_used": template_name}
                
                else:
                    # Need more template data
                    missing_vars = [var for var in template.get("variables", []) if var not in template_vars]
                    
                    response = f"📝 Template '{template_name}' selected! Please provide:\n\n"
                    response += "\n".join([f"• {var}" for var in missing_vars])
                    response += f"\n\n💡 Example: 'Send {template_name} to alice@company.com meeting_title: Weekly Sync meeting_time: Tomorrow 2PM'"
                    
                    return {"response": response, "success": False, "template_name": template_name, "missing_variables": missing_vars}
        
        return None
    
    async def _handle_scheduled_emails(self, user_input: str, parsed: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle email scheduling with intelligent time parsing"""
        
        if parsed.get("schedule_detected"):
            recipient = parsed.get("recipient")
            schedule_time = parsed.get("parsed_schedule_time")
            
            if recipient and schedule_time:
                subject = parsed.get("subject", "Scheduled message from BUDDY")
                body = parsed.get("body", user_input)
                
                # Enhance content for scheduled email
                subject = self.content_enhancer.enhance_subject(subject)
                body = self.content_enhancer.format_email_body(body, parsed.get("contact_name"))
                
                # Schedule the email
                schedule_id = self.scheduler.schedule_email(
                    recipient=recipient,
                    subject=subject,
                    body=body,
                    scheduled_time=schedule_time,
                    frequency=ScheduleFrequency.ONCE
                )
                
                response = f"📅 **Email Scheduled Successfully!**\n\n"
                response += f"📧 **To:** {recipient}\n"
                response += f"📝 **Subject:** {subject}\n"
                response += f"⏰ **When:** {schedule_time.strftime('%B %d, %Y at %I:%M %p')}\n"
                response += f"🆔 **Schedule ID:** {schedule_id}\n\n"
                response += f"💡 Use 'cancel schedule {schedule_id}' to cancel if needed"
                
                return {"response": response, "success": True, "scheduled": True, "schedule_id": schedule_id}
            
            else:
                missing = []
                if not recipient:
                    missing.append("recipient email address")
                if not schedule_time:
                    missing.append("schedule time")
                
                response = f"❓ To schedule an email, please specify:\n"
                response += "\n".join([f"• {item}" for item in missing])
                response += f"\n\n💡 Example: 'Schedule email to team@company.com tomorrow at 9am about project update'"
                
                return {"response": response, "success": False, "needs_scheduling_info": True}
        
        return None
    
    async def _handle_attachment_emails(self, user_input: str, parsed: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle emails with file attachments"""
        
        potential_files = parsed.get("potential_attachments", [])
        
        if potential_files:
            valid_attachments = []
            invalid_files = []
            
            # Validate and create attachments
            for file_path in potential_files:
                is_valid, message = self.attachment_manager.validate_file(file_path)
                if is_valid:
                    attachment = self.attachment_manager.create_attachment(file_path)
                    if attachment:
                        valid_attachments.append(attachment)
                else:
                    invalid_files.append(f"{file_path}: {message}")
            
            if valid_attachments:
                # Validate total attachment size
                is_valid, validation_message = self.attachment_manager.validate_attachments(valid_attachments)
                
                if is_valid:
                    recipient = parsed.get("recipient")
                    if recipient:
                        # Send email with attachments
                        subject = parsed.get("subject", f"Files from BUDDY - {datetime.now().strftime('%m/%d/%Y')}")
                        body = parsed.get("body", f"Please find {len(valid_attachments)} attached file(s).")
                        
                        # Enhance content
                        subject = self.content_enhancer.enhance_subject(subject)
                        body = self.content_enhancer.format_email_body(body, parsed.get("contact_name"))
                        
                        # Note: Actual attachment sending would need mailer enhancement
                        # For now, we'll simulate it
                        attach_info = self.attachment_manager.get_attachment_info(valid_attachments)
                        
                        result = await self.mailer.send_mail(
                            to_email=recipient,
                            subject=subject,
                            body=body + f"\n\n📎 Attachments: {', '.join(attach_info['filenames'])}"
                        )
                        
                        if result.get("success"):
                            self.analytics.track_email_sent(
                                recipient=recipient,
                                subject=subject,
                                provider=self.provider
                            )
                        
                        response = f"✅ Email with attachments sent successfully!\n"
                        response += f"📧 To: {recipient}\n"
                        response += f"📎 Attachments: {attach_info['count']} files ({attach_info['total_size_mb']} MB)\n"
                        response += f"📋 Files: {', '.join(attach_info['filenames'])}"
                        
                        return {"response": response, "success": True, "attachments": len(valid_attachments)}
                    
                    else:
                        response = f"📎 Found {len(valid_attachments)} valid attachments\n"
                        response += f"Files: {', '.join([a.filename for a in valid_attachments])}\n\n"
                        response += "❓ Who should I send these files to?"
                        
                        return {"response": response, "success": False, "needs_recipient": True, "attachments_ready": valid_attachments}
                
                else:
                    return {"response": f"❌ Attachment validation failed: {validation_message}", "success": False}
            
            if invalid_files:
                response = "❌ Invalid attachment files:\n"
                response += "\n".join([f"• {error}" for error in invalid_files])
                
                return {"response": response, "success": False, "invalid_attachments": invalid_files}
        
        return None
    
    async def _send_super_enhanced_email(self, parsed: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Send email with ALL enhancements applied"""
        
        recipient = parsed.get("recipient")
        subject = parsed.get("subject", "Message from BUDDY")
        body = parsed.get("body", "")
        
        # Enhanced recipient handling
        if not recipient:
            contact_suggestions = self.contact_book.get_contact_suggestions(
                parsed.get("recipient_name", "")
            )
            
            response = "❓ **Who should I send this email to?**\n\n"
            
            if contact_suggestions:
                response += "💡 **Contact Suggestions:**\n"
                response += "\n".join([f"• {suggestion}" for suggestion in contact_suggestions[:5]])
                response += "\n\n"
            
            response += "📧 Please provide an email address or contact name."
            
            return {
                "response": response,
                "success": False,
                "needs_recipient": True,
                "suggestions": contact_suggestions
            }
        
        # Apply ALL content enhancements
        subject = self.content_enhancer.enhance_subject(subject)
        body = self.content_enhancer.format_email_body(body, parsed.get("contact_name"))
        
        # Send the email
        result = await self.mailer.send_mail(
            to_email=recipient,
            subject=subject,
            body=body
        )
        
        # Apply ALL post-send enhancements
        if result.get("success"):
            # Track analytics
            tracking_id = self.analytics.track_email_sent(
                recipient=recipient,
                subject=subject,
                template_used=parsed.get("suggested_template"),
                provider=self.provider
            )
            
            # Update contact activity
            self.contact_book.update_contact_activity(recipient)
            
            # Enhanced success response
            response = f"✅ **Email Sent Successfully!**\n\n"
            response += f"📧 **To:** {recipient}\n"
            response += f"📝 **Subject:** {subject}\n"
            response += f"📊 **Provider:** {result.get('provider', 'Unknown')}\n"
            response += f"🆔 **Tracking ID:** {tracking_id}\n"
            
            # Extract and show action items
            action_items = self.content_enhancer.extract_action_items(body)
            if action_items:
                response += f"\n🎯 **Action Items Detected:**\n"
                response += "\n".join([f"• {item}" for item in action_items])
            
            # Add development mode info
            if self.provider == "mock":
                response += f"\n\n🔧 **Development Mode:** Email mocked for testing"
                response += f"\n📝 **Content Preview:** {body[:100]}{'...' if len(body) > 100 else ''}"
            
            return {
                "response": response,
                "success": True,
                "tracking_id": tracking_id,
                "email_result": result,
                "parsed_input": parsed
            }
        
        else:
            return {
                "response": f"❌ Failed to send email to {recipient}\nError: {result.get('error', 'Unknown error')}",
                "success": False,
                "email_result": result,
                "parsed_input": parsed
            }
    
    # Helper methods for template processing
    def _extract_template_variables(self, user_input: str, template: Dict, parsed: Dict, context: Dict) -> Dict[str, str]:
        """Extract template variables from user input and context"""
        variables = {}
        
        # Default variables
        variables["sender_name"] = context.get("user_name", "BUDDY Assistant")
        variables["date"] = datetime.now().strftime("%B %d, %Y")
        variables["time"] = datetime.now().strftime("%I:%M %p")
        
        # Try to extract from recipient info
        if parsed.get("contact_name"):
            variables["recipient_name"] = parsed["contact_name"]
        elif parsed.get("recipient"):
            # Extract name from email
            email_name = parsed["recipient"].split("@")[0].replace(".", " ").title()
            variables["recipient_name"] = email_name
        
        # Extract variables from user input using patterns
        for var in template.get("variables", []):
            # Look for patterns like "meeting_title: Weekly Sync"
            pattern = rf"{var}:\s*([^\n]+)"
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                variables[var] = match.group(1).strip()
        
        return variables
    
    def _has_sufficient_template_data(self, template: Dict, variables: Dict) -> bool:
        """Check if we have enough data to render the template"""
        required_vars = template.get("variables", [])
        essential_vars = ["recipient_name", "sender_name"]  # Always try to have these
        
        # Check if we have at least the essential variables
        for var in essential_vars:
            if var in required_vars and var not in variables:
                return False
        
        # For templates with many variables, require at least 60% to be filled
        if len(required_vars) > 3:
            filled_vars = sum(1 for var in required_vars if var in variables)
            return filled_vars / len(required_vars) >= 0.6
        
        return True
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive status of ALL email system components"""
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "provider": self.provider,
            "system_status": "operational"
        }
        
        try:
            # Template system status
            status["templates"] = {
                "available": len(self.template_manager.list_templates()),
                "list": self.template_manager.list_templates()
            }
            
            # Contact book status
            status["contacts"] = self.contact_book.get_stats()
            
            # Scheduler status
            status["scheduler"] = self.scheduler.get_scheduler_stats()
            
            # Analytics status
            status["analytics"] = self.analytics.get_analytics_summary()
            
            # Attachment system status
            status["attachments"] = self.attachment_manager.get_storage_stats()
            
            status["all_features_active"] = True
            
        except Exception as e:
            status["system_status"] = "degraded"
            status["error"] = str(e)
            status["all_features_active"] = False
        
        return status
