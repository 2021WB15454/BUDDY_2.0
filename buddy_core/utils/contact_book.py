"""
📇 BUDDY 2.0 Enhanced Contact Book System
Smart contact management with fuzzy matching and groups
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import re
from difflib import SequenceMatcher

class Contact:
    """Enhanced contact with multiple email addresses and metadata"""
    
    def __init__(self, name: str, primary_email: str, **kwargs):
        self.name = name
        self.primary_email = primary_email
        self.emails = kwargs.get('emails', [primary_email])
        self.phone = kwargs.get('phone')
        self.company = kwargs.get('company')
        self.title = kwargs.get('title')
        self.groups = kwargs.get('groups', [])
        self.notes = kwargs.get('notes', '')
        self.created = kwargs.get('created', datetime.now().isoformat())
        self.last_contacted = kwargs.get('last_contacted')
        self.contact_frequency = kwargs.get('contact_frequency', 0)
        self.metadata = kwargs.get('metadata', {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert contact to dictionary"""
        return {
            'name': self.name,
            'primary_email': self.primary_email,
            'emails': self.emails,
            'phone': self.phone,
            'company': self.company,
            'title': self.title,
            'groups': self.groups,
            'notes': self.notes,
            'created': self.created,
            'last_contacted': self.last_contacted,
            'contact_frequency': self.contact_frequency,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Contact':
        """Create contact from dictionary"""
        return cls(
            name=data['name'],
            primary_email=data['primary_email'],
            **{k: v for k, v in data.items() if k not in ['name', 'primary_email']}
        )

class ContactBook:
    """Advanced contact management system"""
    
    def __init__(self, contacts_file: str = "contacts.json"):
        self.contacts_file = contacts_file
        self.contacts: Dict[str, Contact] = {}
        self.groups: Dict[str, List[str]] = {}
        self._load_contacts()
    
    def _load_contacts(self):
        """Load contacts from file"""
        if os.path.exists(self.contacts_file):
            try:
                with open(self.contacts_file, 'r') as f:
                    data = json.load(f)
                    
                # Load contacts
                for contact_id, contact_data in data.get('contacts', {}).items():
                    self.contacts[contact_id] = Contact.from_dict(contact_data)
                
                # Load groups
                self.groups = data.get('groups', {})
                
            except Exception as e:
                print(f"Error loading contacts: {e}")
                self._create_sample_contacts()
        else:
            self._create_sample_contacts()
    
    def _create_sample_contacts(self):
        """Create sample contacts for demonstration"""
        sample_contacts = [
            {
                'name': 'Alice Johnson',
                'primary_email': 'alice.johnson@company.com',
                'emails': ['alice.johnson@company.com', 'alice@personal.com'],
                'company': 'Tech Corp',
                'title': 'Product Manager',
                'groups': ['work', 'team']
            },
            {
                'name': 'Bob Smith',
                'primary_email': 'bob.smith@devteam.com',
                'emails': ['bob.smith@devteam.com'],
                'company': 'DevTeam Inc',
                'title': 'Senior Developer',
                'groups': ['work', 'developers']
            },
            {
                'name': 'Sarah Wilson',
                'primary_email': 'sarah.wilson@marketing.com',
                'emails': ['sarah.wilson@marketing.com', 's.wilson@company.com'],
                'company': 'Marketing Pro',
                'title': 'Marketing Director',
                'groups': ['work', 'marketing']
            }
        ]
        
        for contact_data in sample_contacts:
            contact = Contact(**contact_data)
            contact_id = self._generate_contact_id(contact.name)
            self.contacts[contact_id] = contact
        
        # Create sample groups
        self.groups = {
            'work': [id for id, contact in self.contacts.items() if 'work' in contact.groups],
            'team': [id for id, contact in self.contacts.items() if 'team' in contact.groups],
            'developers': [id for id, contact in self.contacts.items() if 'developers' in contact.groups],
            'marketing': [id for id, contact in self.contacts.items() if 'marketing' in contact.groups]
        }
        
        self.save_contacts()
    
    def _generate_contact_id(self, name: str) -> str:
        """Generate a unique contact ID"""
        base_id = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
        counter = 1
        contact_id = base_id
        
        while contact_id in self.contacts:
            contact_id = f"{base_id}_{counter}"
            counter += 1
        
        return contact_id
    
    def save_contacts(self):
        """Save contacts to file"""
        try:
            data = {
                'contacts': {id: contact.to_dict() for id, contact in self.contacts.items()},
                'groups': self.groups,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.contacts_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving contacts: {e}")
    
    def add_contact(self, name: str, email: str, **kwargs) -> str:
        """Add a new contact"""
        contact_id = self._generate_contact_id(name)
        contact = Contact(name, email, **kwargs)
        self.contacts[contact_id] = contact
        
        # Add to groups if specified
        for group in contact.groups:
            if group not in self.groups:
                self.groups[group] = []
            if contact_id not in self.groups[group]:
                self.groups[group].append(contact_id)
        
        self.save_contacts()
        return contact_id
    
    def find_contact(self, query: str) -> Optional[Contact]:
        """Find contact using fuzzy matching"""
        if not query:
            return None
        
        query_lower = query.lower()
        best_match = None
        best_score = 0
        
        for contact in self.contacts.values():
            # Check exact email match first
            for email in contact.emails:
                if email.lower() == query_lower:
                    return contact
            
            # Check name similarity
            name_score = SequenceMatcher(None, contact.name.lower(), query_lower).ratio()
            if name_score > best_score and name_score > 0.6:
                best_score = name_score
                best_match = contact
            
            # Check partial name matches
            name_parts = contact.name.lower().split()
            for part in name_parts:
                if part.startswith(query_lower) and len(query_lower) >= 2:
                    return contact
        
        return best_match
    
    def find_contacts_by_group(self, group: str) -> List[Contact]:
        """Find all contacts in a group"""
        if group not in self.groups:
            return []
        
        return [self.contacts[contact_id] for contact_id in self.groups[group] 
                if contact_id in self.contacts]
    
    def search_contacts(self, query: str) -> List[Contact]:
        """Search contacts by name, email, or company"""
        query_lower = query.lower()
        results = []
        
        for contact in self.contacts.values():
            # Search in name
            if query_lower in contact.name.lower():
                results.append(contact)
                continue
            
            # Search in emails
            if any(query_lower in email.lower() for email in contact.emails):
                results.append(contact)
                continue
            
            # Search in company
            if contact.company and query_lower in contact.company.lower():
                results.append(contact)
                continue
        
        return results
    
    def get_contact_suggestions(self, partial_input: str) -> List[str]:
        """Get contact suggestions for autocomplete"""
        if len(partial_input) < 2:
            return []
        
        suggestions = []
        partial_lower = partial_input.lower()
        
        for contact in self.contacts.values():
            # Name suggestions
            if contact.name.lower().startswith(partial_lower):
                suggestions.append(contact.name)
            
            # Email suggestions
            for email in contact.emails:
                if email.lower().startswith(partial_lower):
                    suggestions.append(email)
        
        return sorted(set(suggestions))[:10]  # Limit to 10 suggestions
    
    def update_contact_activity(self, email: str):
        """Update contact activity when email is sent"""
        for contact in self.contacts.values():
            if email.lower() in [e.lower() for e in contact.emails]:
                contact.last_contacted = datetime.now().isoformat()
                contact.contact_frequency += 1
                self.save_contacts()
                break
    
    def get_frequently_contacted(self, limit: int = 10) -> List[Contact]:
        """Get most frequently contacted people"""
        contacts_with_frequency = [
            (contact, contact.contact_frequency) 
            for contact in self.contacts.values() 
            if contact.contact_frequency > 0
        ]
        
        contacts_with_frequency.sort(key=lambda x: x[1], reverse=True)
        return [contact for contact, _ in contacts_with_frequency[:limit]]
    
    def list_groups(self) -> List[str]:
        """List all available groups"""
        return list(self.groups.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get contact book statistics"""
        total_contacts = len(self.contacts)
        total_groups = len(self.groups)
        
        contacts_with_companies = sum(1 for c in self.contacts.values() if c.company)
        contacts_with_phones = sum(1 for c in self.contacts.values() if c.phone)
        
        return {
            'total_contacts': total_contacts,
            'total_groups': total_groups,
            'contacts_with_companies': contacts_with_companies,
            'contacts_with_phones': contacts_with_phones,
            'most_contacted': [c.name for c in self.get_frequently_contacted(3)]
        }
