from typing import List
import os
class EmailData:
    """Data class for email information"""
    def __init__(self, subject: str, thread: str, sender: str, body: str, 
                 time: str, category: str = None, id: str = None,  
                 workflow_id: str = None, summary: str = None, draft_response: str = None):
        
        self.subject = subject
        self.thread = thread
        self.sender = sender
        self.body = body
        self.time = time
        self.category = category
        self.id = id
        self.workflow_id = workflow_id
        self.summary = summary
        self.draft_response = draft_response  
    
    def get_snippet(self, max_length: int = 40) -> str:
        """Get truncated body text for preview"""
        if len(self.body) <= max_length:
            return self.body
        return self.body[:max_length] + "..."


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
        
        with open(filename, "w") as f:
            json.dump(
                {
                    category: [email.__dict__ for email in EmailService.emails[category]]
                    for category in EmailService.emails
                },
                f,
                indent=4
            )
                
    @staticmethod
    def load_from_file(filename="db/emails.json"):
        import json
        
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    data = json.load(f)
                    for category, emails_list in data.items():
                        EmailService.emails[category] = [
                            EmailData(**email_dict) for email_dict in emails_list
                        ]
            except FileNotFoundError:
                print("No saved email data found.")
        else:
            emails = {}
            with open(filename, "w", encoding= "utf-8") as f:
                json.dump(emails, f, indent= 4)
            
            print("--Succesfully create json file for storing emails-- (load_from_file)")
            
    @staticmethod
    def load_emails_by_category(category: str) -> List[EmailData]:
        """Load emails for a specific category"""
        return EmailService.emails.get(category, EmailService.emails["home"])
    
    @staticmethod
    def add_new_email(email: EmailData):
        EmailService.emails["home"].append(email)
        
    @staticmethod
    def add_to_ignore(email: EmailData):
        """Add email to ignore"""
        
        if email in EmailService.emails["home"]:
            EmailService.emails["ignore"].append(email)
            
    @staticmethod
    def add_to_notify(email: EmailData):
        """Add email to ignore"""
        
        if email in EmailService.emails["home"]:
            EmailService.emails["notify"].append(email)
    
    @staticmethod
    def notify_to_ignore(email: EmailData):
        """Move email from notify to ignore category"""
        # Remove from notify
        if email in EmailService.emails["notify"]:
            EmailService.emails["notify"].remove(email)
        
        # Add to ignore if not already there
        if email not in EmailService.emails["ignore"]:
            EmailService.emails["ignore"].append(email)
        
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
        pending_email =EmailData(
                                  email.subject, email.thread, email.sender, email.body, 
                                  email.time, email.category, email.id, 
                                  email.workflow_id, email.summary, email.draft_response
        )

        # Add to pending
        EmailService.emails["human"].append(pending_email)
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