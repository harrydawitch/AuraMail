import os
import uuid



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
            **Subject**: {subject}
            **To**: {to}\n\n

            {message}

            ---
            """