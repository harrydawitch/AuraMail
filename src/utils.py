import os
import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

def create_formatted_email(to_email, subject, body):
    """
    Create a properly formatted email message with both HTML and plain text parts
    """
    # Create message container
    msg = MIMEMultipart('alternative')
    msg['To'] = to_email
    msg['Subject'] = subject
    msg['From'] = 'me'
    
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