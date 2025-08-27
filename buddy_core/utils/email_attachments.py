"""
📎 BUDDY 2.0 Enhanced Email Attachments System
Smart file handling, validation, and cloud storage integration
"""

import os
import mimetypes
import base64
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
import hashlib
from pathlib import Path
import json

@dataclass
class EmailAttachment:
    filename: str
    content: bytes
    content_type: str
    size_bytes: int
    encoding: str = "base64"
    content_id: Optional[str] = None  # For inline images
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'filename': self.filename,
            'content_base64': base64.b64encode(self.content).decode('utf-8'),
            'content_type': self.content_type,
            'size_bytes': self.size_bytes,
            'encoding': self.encoding,
            'content_id': self.content_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailAttachment':
        return cls(
            filename=data['filename'],
            content=base64.b64decode(data['content_base64']),
            content_type=data['content_type'],
            size_bytes=data['size_bytes'],
            encoding=data.get('encoding', 'base64'),
            content_id=data.get('content_id')
        )

class AttachmentManager:
    """Advanced email attachment management system"""
    
    # File size limits (in bytes)
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
    MAX_TOTAL_SIZE = 50 * 1024 * 1024  # 50MB total
    
    # Allowed file types
    ALLOWED_EXTENSIONS = {
        # Documents
        '.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt',
        # Spreadsheets
        '.xls', '.xlsx', '.csv', '.ods',
        # Presentations
        '.ppt', '.pptx', '.odp',
        # Images
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
        # Archives
        '.zip', '.rar', '.7z', '.tar', '.gz',
        # Code
        '.py', '.js', '.html', '.css', '.json', '.xml', '.yml', '.yaml',
        # Others
        '.log', '.md', '.ini', '.conf'
    }
    
    # Security risk extensions (blocked)
    BLOCKED_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs', '.js', 
        '.jar', '.app', '.deb', '.rpm', '.dmg', '.pkg', '.msi'
    }
    
    def __init__(self, storage_path: str = "attachments"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.attachment_registry = {}
        self._load_registry()
    
    def _load_registry(self):
        """Load attachment registry"""
        registry_file = self.storage_path / "registry.json"
        if registry_file.exists():
            try:
                with open(registry_file, 'r') as f:
                    self.attachment_registry = json.load(f)
            except Exception as e:
                print(f"Error loading attachment registry: {e}")
    
    def _save_registry(self):
        """Save attachment registry"""
        registry_file = self.storage_path / "registry.json"
        try:
            with open(registry_file, 'w') as f:
                json.dump(self.attachment_registry, f, indent=2)
        except Exception as e:
            print(f"Error saving attachment registry: {e}")
    
    def validate_file(self, filepath: str) -> Tuple[bool, str]:
        """Validate file for email attachment"""
        file_path = Path(filepath)
        
        # Check if file exists
        if not file_path.exists():
            return False, f"File not found: {filepath}"
        
        # Check file extension
        extension = file_path.suffix.lower()
        if extension in self.BLOCKED_EXTENSIONS:
            return False, f"File type blocked for security: {extension}"
        
        if extension not in self.ALLOWED_EXTENSIONS:
            return False, f"File type not allowed: {extension}"
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            return False, f"File too large: {file_size} bytes (max: {self.MAX_FILE_SIZE})"
        
        # Check if file is readable
        try:
            with open(file_path, 'rb') as f:
                f.read(1024)  # Try to read first 1KB
        except Exception as e:
            return False, f"Cannot read file: {e}"
        
        return True, "File validation passed"
    
    def create_attachment(self, filepath: str, content_id: Optional[str] = None) -> Optional[EmailAttachment]:
        """Create an email attachment from a file"""
        # Validate file
        is_valid, message = self.validate_file(filepath)
        if not is_valid:
            print(f"Attachment validation failed: {message}")
            return None
        
        file_path = Path(filepath)
        
        try:
            # Read file content
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(filepath)
            if not content_type:
                content_type = 'application/octet-stream'
            
            # Create attachment
            attachment = EmailAttachment(
                filename=file_path.name,
                content=content,
                content_type=content_type,
                size_bytes=len(content),
                content_id=content_id
            )
            
            # Store attachment reference
            attachment_hash = self._calculate_file_hash(content)
            self.attachment_registry[attachment_hash] = {
                'filename': file_path.name,
                'original_path': str(file_path),
                'content_type': content_type,
                'size_bytes': len(content),
                'created_at': file_path.stat().st_mtime,
                'content_id': content_id
            }
            self._save_registry()
            
            return attachment
            
        except Exception as e:
            print(f"Error creating attachment: {e}")
            return None
    
    def create_attachment_from_url(self, url: str, filename: Optional[str] = None) -> Optional[EmailAttachment]:
        """Create attachment by downloading from URL (placeholder for future implementation)"""
        # This would implement URL downloading
        print(f"URL attachment creation not yet implemented: {url}")
        return None
    
    def validate_attachments(self, attachments: List[EmailAttachment]) -> Tuple[bool, str]:
        """Validate a list of attachments"""
        if not attachments:
            return True, "No attachments to validate"
        
        total_size = sum(att.size_bytes for att in attachments)
        
        if total_size > self.MAX_TOTAL_SIZE:
            return False, f"Total attachment size too large: {total_size} bytes (max: {self.MAX_TOTAL_SIZE})"
        
        # Check individual files
        for attachment in attachments:
            if attachment.size_bytes > self.MAX_FILE_SIZE:
                return False, f"Attachment '{attachment.filename}' too large: {attachment.size_bytes} bytes"
            
            # Check filename for security
            if self._is_suspicious_filename(attachment.filename):
                return False, f"Suspicious filename detected: {attachment.filename}"
        
        return True, f"All {len(attachments)} attachments validated successfully"
    
    def _is_suspicious_filename(self, filename: str) -> bool:
        """Check for suspicious filename patterns"""
        suspicious_patterns = [
            '..', '/', '\\', '<', '>', ':', '"', '|', '?', '*',
            'con', 'prn', 'aux', 'nul'  # Windows reserved names
        ]
        
        filename_lower = filename.lower()
        return any(pattern in filename_lower for pattern in suspicious_patterns)
    
    def _calculate_file_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of file content"""
        return hashlib.sha256(content).hexdigest()[:16]
    
    def compress_images(self, attachments: List[EmailAttachment]) -> List[EmailAttachment]:
        """Compress image attachments to reduce size (placeholder)"""
        # This would implement image compression
        compressed = []
        
        for attachment in attachments:
            if attachment.content_type.startswith('image/'):
                # Placeholder: would implement actual image compression
                print(f"Image compression not yet implemented for {attachment.filename}")
                compressed.append(attachment)
            else:
                compressed.append(attachment)
        
        return compressed
    
    def scan_for_viruses(self, attachments: List[EmailAttachment]) -> Tuple[bool, List[str]]:
        """Virus scan attachments (placeholder for security integration)"""
        # This would integrate with antivirus APIs
        suspicious_files = []
        
        for attachment in attachments:
            # Simple heuristic checks
            if attachment.filename.endswith('.exe'):
                suspicious_files.append(attachment.filename)
            
            # Check for suspicious content patterns
            if b'virus' in attachment.content.lower() or b'malware' in attachment.content.lower():
                suspicious_files.append(attachment.filename)
        
        is_clean = len(suspicious_files) == 0
        return is_clean, suspicious_files
    
    def get_attachment_info(self, attachments: List[EmailAttachment]) -> Dict[str, Any]:
        """Get summary information about attachments"""
        if not attachments:
            return {'count': 0, 'total_size': 0}
        
        total_size = sum(att.size_bytes for att in attachments)
        
        file_types = {}
        for attachment in attachments:
            content_type = attachment.content_type
            file_types[content_type] = file_types.get(content_type, 0) + 1
        
        return {
            'count': len(attachments),
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'file_types': file_types,
            'largest_file': max(attachments, key=lambda x: x.size_bytes).filename if attachments else None,
            'filenames': [att.filename for att in attachments]
        }
    
    def create_inline_image(self, filepath: str, content_id: str) -> Optional[EmailAttachment]:
        """Create an inline image attachment"""
        attachment = self.create_attachment(filepath, content_id=content_id)
        
        if attachment and not attachment.content_type.startswith('image/'):
            print(f"Warning: File {filepath} is not an image but marked as inline")
        
        return attachment
    
    def extract_attachments_from_text(self, text: str) -> List[str]:
        """Extract file paths mentioned in text"""
        import re
        
        # Pattern to match file paths
        file_patterns = [
            r'"([^"]+\.[a-zA-Z0-9]+)"',  # Quoted paths
            r"'([^']+\.[a-zA-Z0-9]+)'",  # Single quoted paths
            r'(\S+\.[a-zA-Z0-9]+)',      # Unquoted paths
            r'attach\s+([^\s]+)',        # "attach filename"
            r'file:\s*([^\s]+)',         # "file: filename"
        ]
        
        file_paths = []
        for pattern in file_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            file_paths.extend(matches)
        
        # Filter for likely file paths
        valid_paths = []
        for path in file_paths:
            if Path(path).exists() or '/' in path or '\\' in path:
                valid_paths.append(path)
        
        return list(set(valid_paths))  # Remove duplicates
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get attachment storage statistics"""
        total_files = len(self.attachment_registry)
        total_size = sum(info['size_bytes'] for info in self.attachment_registry.values())
        
        # Get file type distribution
        type_distribution = {}
        for info in self.attachment_registry.values():
            content_type = info['content_type']
            type_distribution[content_type] = type_distribution.get(content_type, 0) + 1
        
        return {
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'type_distribution': type_distribution,
            'max_file_size_mb': round(self.MAX_FILE_SIZE / (1024 * 1024), 2),
            'max_total_size_mb': round(self.MAX_TOTAL_SIZE / (1024 * 1024), 2)
        }

class CloudAttachmentManager:
    """Cloud storage integration for large attachments (placeholder)"""
    
    def __init__(self, provider: str = "local"):
        self.provider = provider
        self.cloud_links = {}
    
    def upload_large_attachment(self, attachment: EmailAttachment) -> Optional[str]:
        """Upload large attachment to cloud and return download link"""
        # This would integrate with cloud storage providers
        print(f"Cloud upload not yet implemented for {attachment.filename}")
        return None
    
    def create_download_link(self, attachment: EmailAttachment, expires_hours: int = 24) -> str:
        """Create temporary download link for attachment"""
        # Placeholder implementation
        link_id = hashlib.md5(attachment.filename.encode()).hexdigest()[:8]
        download_link = f"https://buddy-attachments.cloud/download/{link_id}"
        
        # Store link info (would be in database in real implementation)
        self.cloud_links[link_id] = {
            'filename': attachment.filename,
            'expires_at': f"{expires_hours} hours from now",
            'size_bytes': attachment.size_bytes
        }
        
        return download_link
