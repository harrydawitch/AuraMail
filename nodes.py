from states import State, ClassifierOutputSchema, SummarizerOutputSchema, WriterOutputSchema

from prompts import triage_system_prompt, default_triage_instructions, triage_user_prompt
from prompts import summary_system_prompt, summary_user_prompt
from prompts import writer_system_prompt

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.types import Command, interrupt
from langgraph.graph import END

from langchain_google_community.gmail.send_message import GmailSendMessage
from langchain_google_community import GmailToolkit


from utils import parse_email, format_email_markdown


class Nodes:
    """
    Nodes is a workflow class for processing and responding to emails using an LLM-powered agent.
    This class encapsulates the logic for classifying, summarizing, handling user interrupts, drafting, and sending email responses.
    It leverages a language model for structured outputs at each step and integrates with Gmail APIs for email operations.
    Attributes:
        model (str): The initialized chat model used for LLM operations.
        gmail (GmailToolkit): Toolkit for interacting with Gmail API.
    Methods:
        __init__(model: str):
            Initializes the Nodes instance with a specified LLM model and Gmail toolkit.
        classifer(state: State) -> Command:
            Classifies the input email as "notify" or "ignore" using the LLM and returns the next command.
        summarizer(state: State) -> Command:
            Summarizes the email body using the LLM and prepares the summary for the next step.
        interrupts_handler(state: State) -> Command:
            Handles user interaction to decide whether to respond to the email, based on user feedback.
        writer(state: State) -> Command:
            Drafts an email response using the LLM, based on the current conversation state.
        send_response(state: State) -> Command:
            Sends the drafted email response via Gmail, or collects feedback for further editing if not approved.
    Raises:
        ValueError: If an invalid classification or argument is encountered during workflow steps.
    """
    def __init__(self, model: str):
        self.model= init_chat_model(model= model)
        self.gmail = GmailToolkit()


    def classifer(self, state: State):
        

        llm = self.model.with_structured_output(ClassifierOutputSchema)
        
        author, to, subject, body = parse_email(state["input_email"])
        system_msg = triage_system_prompt.format(
            background= "I'm Harry an AI Engineer",
            instruction= default_triage_instructions
        )
        
        body_message = triage_user_prompt.format(
            author= author, to= to, subject= subject, body= body
        )
        
        message = [SystemMessage(content= system_msg), HumanMessage(content= body_message)]
        result = llm.invoke(message)
            
        if result.classification == "notify":
            goto = "summarizer"
            update = {"decision": result.classification}
            
        elif result.classification == "ignore":
            goto = END
            update = {"decision": result.classification}
            
        else:
            raise ValueError(f"Invalid classification: {result.classification}")
        
        return Command(goto= goto, update= update)
        
        
        
    def summarizer(self, state: State):
        llm = self.model.with_structured_output(SummarizerOutputSchema)
        
        _, _, _, body = parse_email(state["input_email"])
        
        sys_msg = summary_system_prompt
        user_msg = summary_user_prompt.format(body= body)
        
        message = [SystemMessage(content= sys_msg), HumanMessage(content= user_msg)]
        response = llm.invoke(message)
        

        goto = "interrupts_handler"
        update= {
            "summary": response
        } 
        
        return Command(goto= goto, update= update)
        
        
    def interrupts_handler(self, state: State):
        subject, to, email_thread = parse_email(state["input_email"])
        email = format_email_markdown(subject, to, email_thread)
        request = interrupt({
            "question": "Do you want to response to this email?",
            "show_email": email
        })
        
        
        
        if request["type"] is True:
            goto = "writer"
            update = {
                "decision": "response",
                "messages": HumanMessage(
                                content=f"""Respond to the email:\n\n{email}\n\n{request["feedback"]}"""
                )
            }
        
        elif request["type"] is False:
            goto = END
            update = {
                "decision": "ignore"
            }
        else:
            raise ValueError(f"Invalid argument: {request["type"]}")
        
        return Command(goto= goto, update= update)


    def writer(self, state: State):
        llm = self.model.with_structured_output(WriterOutputSchema)
        
        if len(state["messages"]) < 2:
            messages = [SystemMessage(content= writer_system_prompt)] + state["messages"]
        
        else:
            messages = [SystemMessage(content= writer_system_prompt)] + state["messages"][-2:]
        
        
        response = llm.invoke(messages)
        to, subject, body = response.gmail_schema.to, response.gmail_schema.subject, response.gmail_schema.message
        draft = format_email_markdown(subject, to, body)
        
        return Command(
            goto = "send_response", 
            update = {
                    "draft_response": draft,
                    "output_schema": response 
                }
            )
        
        
    def send_response(self, state: State):
        tool = GmailSendMessage(api_resource= self.gmail.api_resource)
        
        request = interrupt(
            {
                "draft_response": state["draft_response"],
                "question": "Do you want to send this response?"
            }
        )
        
        if request["type"] is True:
                        
            to = state['output_schema'].gmail_schema.to
            subject = state['output_schema'].gmail_schema.subject
            message = state['output_schema'].gmail_schema.message
            
            print(f"Sending response to: {to}")
            
            tool.invoke(
                {
                    "to": to,
                    "subject": subject,
                    "message": message
                }
            )
            
            print(f"\nResponse sent:\n\nTo: {to}\nSubject: {subject}\nBody: {message}")
            return Command(goto= END)
        
        else:
            previous_response = AIMessage(
                content= state["draft_response"]
            )
            feedback_msg = HumanMessage(
                content=(
                    "The previous draft wasn’t quite right take a look of the feedback below:\n "
                    f"{request.get('feedback', '<no feedback given>')}\n"
                    "Please rewrite the reply accordingly."
                )
            )
            
            feedback = [previous_response, feedback_msg]
            
            return Command(
                goto= "writer",
                update = {"messages": state["messages"] + feedback}
            )
            