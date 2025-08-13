import os
import re
import base64

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

from pathlib import Path
from typing import List, Optional
from plyer import notification

from dotenv import load_dotenv
load_dotenv()

class Notification:
    def __init__(self, app_name: str = "SmartEmailBot", app_icon: str = None, timeout: int = 10):
        self.app_name = app_name
        self.timeout = timeout
        self.display_name = os.environ.get("EMAIL_DISPLAY_NAME")
        
        # Handle app_icon path properly
        if app_icon is None:
            # Try to find the icon file
            assets_path = get_assets_path()
            possible_icons = [
                assets_path / "icon.ico",
                assets_path / "icon.png", 
                assets_path / "app_icon.ico",
                assets_path / "app_icon.png"
            ]
            
            self.app_icon = None  # Default to no icon
            for icon_path in possible_icons:
                if icon_path.exists():
                    self.app_icon = str(icon_path.absolute())
                    print(f"Using icon: {self.app_icon}")
                    break
            
            if self.app_icon is None:
                print("Warning: No icon file found for notifications")
        else:
            # Use provided path, but make it absolute if it's relative
            icon_path = Path(app_icon)
            if icon_path.is_absolute():
                self.app_icon = str(icon_path) if icon_path.exists() else None
            else:
                # Relative path - resolve it properly
                assets_path = get_assets_path()
                full_path = assets_path / icon_path
                self.app_icon = str(full_path.absolute()) if full_path.exists() else None
    
    def startup(self, notify_count: int, pending_count: int):
        """Send startup notification"""
        if notify_count == 0 and pending_count == 0:
            return  # Don't notify if no emails
            
        title = f"Welcome back {self.display_name}"
        message = f"You have {notify_count if notify_count else 0} notify email(s) and {pending_count if pending_count else 0} pending email(s)"
        #print(message)
        self._send_notification(title, message)  
    
    def new_notify_email(self, sender: str, content: str):
        """Send new email notification"""
        title = "New notify email!" + " - " + get_sender_name(sender)
        self._send_notification(title, content)

    
    def _send_notification(self, title: str, message: str, timeout: Optional[int] = None):
        """Internal method to send notifications with error handling"""
        try:
            notification.notify(
                title=title,
                message=message,
                app_name=self.app_name,
                app_icon=self.app_icon,  # This will now be None or a valid absolute path
                timeout=timeout or self.timeout,
                toast=False,
            )
        except Exception as e:
            print(f"Failed to send notification: {e}")
             
def _convert_to_html(text_body):
    """
    Convert plain text to HTML with proper formatting
    """
    # Split into paragraphs and add HTML formatting
    paragraphs = text_body.split('\n\n')
    html_paragraphs = []
    
    for paragraph in paragraphs:
        if paragraph.strip():  # Skip empty paragraphs
            # Replace single newlines within paragraphs with <br>
            formatted_paragraph = paragraph.replace('\n', '<br>')
            html_paragraphs.append(f'<p>{formatted_paragraph}</p>')
    
    html_body = f"""
    <html>
        <head></head>
        <body>
            {''.join(html_paragraphs)}
        </body>
    </html>
    """
    
    return html_body

def get_display_name():
    """
    Get the display name for emails from environment variable
    Default to 'AI Assistant' if not set
    """
    return os.environ.get("EMAIL_DISPLAY_NAME", "AI Assistant")

def create_formatted_email(to_email, subject, body):
    """
    Create a properly formatted email message with both HTML and plain text parts
    """
    # Create message container
    msg = MIMEMultipart('alternative')
    msg['To'] = to_email
    msg['Subject'] = subject
    
    # Get display name and email address
    display_name = get_display_name()
    my_email = os.environ.get("MY_EMAIL", "me")
    
    # Format the 'From' field with display name
    msg['From'] = formataddr((display_name, my_email))
    
    # Create plain text version (keep line breaks)
    text_body = body.replace('\\n', '\n')  # Convert literal \n to actual newlines
    
    # Create HTML version with proper formatting
    html_body = _convert_to_html(text_body)
    
    # Create MIMEText objects
    part1 = MIMEText(text_body, 'plain', 'utf-8')
    part2 = MIMEText(html_body, 'html', 'utf-8')
    
    # Attach parts
    msg.attach(part1)
    msg.attach(part2)
    
    # Encode the message
    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
    return raw_message

def format_email_body(email_body: str) -> str:
    """
    Convert \\n sequences to actual newlines and ensure proper email formatting
    """
    # Replace literal \n with actual newlines
    formatted_body = email_body.replace('\\n', '\n')
    
    # Additional formatting improvements
    formatted_body = formatted_body.replace('\n\n\n', '\n\n')  # Remove excessive line breaks
    
    return formatted_body

def parse_email(email_input: dict):
    author = email_input["sender"]
    to = os.environ["MY_EMAIL"]
    subject = email_input["subject"]
    body = email_input["body"]
    id = email_input["id"]

    return (author, to, subject, body, id)
    
    
def format_email_markdown(subject, author, to, email_thread, email_id=None):
    """Format email details into a nicely formatted markdown string for display
    
    Args:
        subject: Email subject
        author: Email sender
        to: Email recipient
        email_thread: Email content
        email_id: Optional email ID (for Gmail API)
    """
    id_section = f"\n**ID**: {email_id}" if email_id else ""
    
    return f"""
**Subject**: {subject}
**From**: {author}
**To**: {to}{id_section}

{email_thread}

---
"""
            
def format_send_email_markdown(subject, to, message):
    """Format email details into a nicely formatted markdown string for display
    
    Args:
        subject: Email subject
        to: Email recipient
        mesage: Email content
    """
    
    return f"""
Subject: {subject}
To: {to}\n\n

{message}

---
            """
            
def get_sender_name(sender):
    pattern = r'^"?(.*?)"?\s*<'
    name = re.match(pattern, sender).group(1).strip('.')
        
    return name

def get_assets_path():
    """Get the absolute path to the assets directory"""
    current_file = Path(__file__)
    # Assuming utils.py is in src/ and assets is in src/ui/assets/
    assets_path = current_file.parent / "ui" / "assets"
    
    # If that doesn't exist, try other common locations
    if not assets_path.exists():
        # Try parent directory structure
        assets_path = current_file.parent.parent / "src" / "ui" / "assets"
    
    if not assets_path.exists():
        # Try relative to project root
        assets_path = current_file.parent.parent / "assets"
    
    return assets_path