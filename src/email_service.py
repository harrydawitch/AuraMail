import email.header
from typing import List
import os
from datetime import datetime

class EmailData:
    """Data class for email information"""
    def __init__(self, subject: str, thread: str, sender: str, body: str, 
                 time: str, category: str = None, id: str = None,  
                 workflow_id: str = None, summary: str = None, draft_response: str = None):
        
        self.subject = self._decode_email_header(subject)
        self.thread = thread
        self.sender = self._decode_email_header(sender)
        self.body = body
        self.time = time
        self.category = category
        self.id = id
        self.workflow_id = workflow_id
        self.summary = summary
        self.draft_response = draft_response
        
        # Add timestamp for sorting (when email was processed by the system)
        self.timestamp = datetime.now()
    
    def _decode_email_header(self, header_value: str) -> str:
        """
        Decode MIME-encoded email headers (RFC 2047)
        Handles formats like: =?UTF-8?B?base64text?= or =?UTF-8?Q?quoted-printable?=
        """
        if not header_value:
            return ""
        
        try:
            # Use email.header.decode_header to properly decode MIME headers
            decoded_parts = email.header.decode_header(header_value)
            decoded_string = ""
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding)
                    else:
                        # Try UTF-8 first, then fallback to latin-1
                        try:
                            decoded_string += part.decode('utf-8')
                        except UnicodeDecodeError:
                            decoded_string += part.decode('latin-1', errors='ignore')
                else:
                    decoded_string += str(part)
            
            return decoded_string.strip()
            
        except Exception as e:
            print(f"Error decoding email header '{header_value}': {e}")
            # Return original if decoding fails
            return header_value

class EmailService:
    """Service class for handling email data operations"""
    
    emails = {
            "home": [],
            "notify": [],
            "ignore": [],
            "human": []
        }

    @staticmethod
    def save_to_file(filename="db/emails.json"):
        import json
        
        # Convert timestamps to strings for JSON serialization
        data_to_save = {}
        for category in EmailService.emails:
            data_to_save[category] = []
            for email in EmailService.emails[category]:
                email_dict = email.__dict__.copy()
                if hasattr(email, 'timestamp'):
                    email_dict['timestamp'] = email.timestamp.isoformat()
                data_to_save[category].append(email_dict)
        
        with open(filename, "w") as f:
            json.dump(data_to_save, f, indent=4)
                
    @staticmethod
    def load_from_file(filename="db/emails.json"):
        import json
        
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    data = json.load(f)
                    for category, emails_list in data.items():
                        EmailService.emails[category] = []
                        for email_dict in emails_list:
                            # Restore timestamp if it exists
                            if 'timestamp' in email_dict:
                                try:
                                    timestamp_str = email_dict.pop('timestamp')
                                    email = EmailData(**email_dict)
                                    email.timestamp = datetime.fromisoformat(timestamp_str)
                                except:
                                    email = EmailData(**email_dict)
                                    email.timestamp = datetime.now()
                            else:
                                email = EmailData(**email_dict)
                                email.timestamp = datetime.now()
                            
                            EmailService.emails[category].append(email)
                        
                        # Sort by timestamp after loading (latest first)
                        EmailService._sort_emails_by_timestamp(category)
                        
            except FileNotFoundError:
                print("No saved email data found.")
        else:
            emails = {}
            os.makedirs(os.path.dirname(filename), exist_ok= True)
            with open(filename, "w", encoding= "utf-8") as f:
                json.dump(emails, f, indent= 4)
            
            print("--Successfully create json file for storing emails-- (load_from_file)")

    @staticmethod
    def _sort_emails_by_timestamp(category: str):
        """Sort emails in a category by timestamp (latest first)"""
        EmailService.emails[category].sort(key=lambda email: email.timestamp, reverse=True)
            
    @staticmethod
    def load_emails_by_category(category: str) -> List[EmailData]:
        """Load emails for a specific category, sorted with latest first"""
        emails = EmailService.emails.get(category, EmailService.emails["home"])
        # Sort by timestamp, latest first
        return sorted(emails, key=lambda email: getattr(email, 'timestamp', datetime.min), reverse=True)
    
    @staticmethod
    def add_new_email(email: EmailData):
        # Insert at the beginning instead of append
        EmailService.emails["home"].insert(0, email)
        
    @staticmethod
    def add_to_ignore(email: EmailData):
        """Add email to ignore"""
        
        if email in EmailService.emails["home"]:
            # Insert at the beginning instead of append
            EmailService.emails["ignore"].insert(0, email)
            
    @staticmethod
    def add_to_notify(email: EmailData):
        """Add email to notify"""
        
        if email in EmailService.emails["home"]:
            # Insert at the beginning instead of append
            EmailService.emails["notify"].insert(0, email)
    
    @staticmethod
    def notify_to_ignore(email: EmailData):
        """Move email from notify to ignore category"""
        # Remove from notify
        if email in EmailService.emails["notify"]:
            EmailService.emails["notify"].remove(email)
        
        # Add to ignore at the beginning if not already there
        if email not in EmailService.emails["ignore"]:
            EmailService.emails["ignore"].insert(0, email)
        
        print(f"Email '{email.subject}' moved to ignore category")
    
    @staticmethod
    def remove_notify(email: EmailData):
        """Generate a draft response with user context"""

        # Remove from notify
        if email in EmailService.emails["notify"]:
            EmailService.emails["notify"].remove(email)
                
        print(f"Remove email from notify '{email.id}' - (remove_notify)")
        
    @staticmethod
    def notify_to_pending(email: EmailData):
        """Generate a draft response with user context"""
        
        # Create new email with draft response
        pending_email = EmailData(
            email.subject, email.thread, email.sender, email.body, 
            email.time, email.category, email.id, 
            email.workflow_id, email.summary, email.draft_response
        )

        # Add to pending at the beginning
        EmailService.emails["human"].insert(0, pending_email)
        print(f"Draft response generated for email '{email.subject}'")
    
    @staticmethod
    def approve_draft_response(email: EmailData):
        """Approve and send the draft response"""
        
        # Simulate sending email
        print(f"Email response approved and sent for '{email.subject}'")
        
        # Remove from pending
        if email in EmailService.emails["human"]:
            EmailService.emails["human"].remove(email)
        
        # In a real implementation, you would send the actual email here
    
    @staticmethod
    def regenerate_draft_response(email: EmailData, draft: str):
        """Regenerate draft response with user feedback"""
        
        # Update the draft response
        email.draft_response = draft
        
        print(f"Draft response regenerated for email '{email.subject}' with feedback")

    @staticmethod
    def get_email(category: str, id: str):
        for email in EmailService.emails[category]:
            try:
                if id == email.id:
                    return email
            except Exception as e:
                print(f"\n Email not found! EmailService -> get_email(): {e}")