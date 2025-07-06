
from langchain_community.tools.gmail.utils import build_resource_service, get_gmail_credentials

from base64 import urlsafe_b64decode


credentials = get_gmail_credentials(
                                    token_file= "token.json",
                                    scopes=["https://mail.google.com/"],
                                    client_secrets_file= "credentials.json"
                                    )

api_resource = build_resource_service(credentials)


def move_to_spam(message_id: str):
    """
    Adds the SPAM label and removes INBOX from the given message.
    """
    api_resource.users().messages().modify(
        userId='me',
        id=message_id,
        body={
            'addLabelIds':   ['SPAM'],
            'removeLabelIds':['INBOX']
        }
    ).execute()


