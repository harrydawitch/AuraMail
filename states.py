from pydantic import BaseModel, Field
from typing import Literal, TypedDict, Annotated

from langgraph.graph import add_messages
from langchain_core.messages import AnyMessage

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    input_email: dict
    decision: Literal["ignore", "notify"]
    
    summary: str
    draft_response: str
    user_feedback: str
    output_schema: dict
    
    
    
class ClassifierOutputSchema(BaseModel):
    classification: Literal["ignore", "notify"] = Field(
        description="""
                        The classification of an email: \
                        'ignore' for irrelevant emails,\
                        'notify' for important information that doesn't need a response. \
                    """
    )
    reasoning: str = Field(
        description= 
                    """
                        Step-by-step reasoning behind the classification
                    """
    )
    
class SummarizerOutputSchema(BaseModel):
    summary_content: str = Field(
        description="""
                        A concise summary of the main points, intent, and important details of the email.
                        This should capture the essential information in a clear and brief manner,
                        enabling quick understanding of the email's content without reading the full message.                    
                    """
    )
    
class GmailDraftSchema(BaseModel):
    to: str = Field(description="The recipient's email address for the reply")
    subject: str = Field(description="The subject line for the draft reply email")
    message: str = Field(description="The full body content of the draft reply email")

class WriterOutputSchema(BaseModel):
    gmail_schema: GmailDraftSchema = Field(
        description="A dictionary in JSON format containing the draft reply email details"
    )
