def parse_email(email_input: dict):
    author = email_input["sender"]
    to = "longhero911@gmail.com"
    subject = email_input["subject"]
    body = email_input["body"]

    return (author, to, subject, body)
    
def format_email_markdown(subject, to, email_thread, email_id=None):
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
**To**: {to}{id_section}

{email_thread}

---
"""