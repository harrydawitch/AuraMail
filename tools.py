from langchain_core.tools import tool
from langchain_google_community.gmail.send_message import GmailSendMessage
from langchain_google_community.gmail import GmailToolKit

@tool("send_gmail")
def send_email():
    pass