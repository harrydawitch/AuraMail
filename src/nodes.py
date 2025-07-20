import os
import time

from datetime import datetime

from src.states import State, ClassifierOutputSchema, SummarizerOutputSchema, WriterOutputSchema

from src.prompts import classifier_system_prompt, default_rules, classifier_user_prompt
from src.prompts import summary_system_prompt, summary_user_prompt, default_summarizer_instruction
from src.prompts import writer_system_prompt, default_writer_instruction, writer_user_prompt

from src.utils import parse_email, format_email_markdown, format_send_email_markdown

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import END
from langgraph.types import Command, interrupt

from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.send_message import GmailSendMessage
from langchain_google_community.gmail.search import GmailSearch



class Nodes():

    def __init__(self, model: str):
        self.model= init_chat_model(model= model)
        self.gmail = GmailToolkit()
        
        
    def classifier(self, state: State): 
        
        llm = self.model.with_structured_output(ClassifierOutputSchema)
        
        author, to, subject, body, id = parse_email(state["input_email"])
        system_msg = classifier_system_prompt.format(
            rules= default_rules
        )
        
        body_message = classifier_user_prompt.format(
            author= author, to= to, subject= subject, body= body
        )
        
        message = [SystemMessage(content= system_msg), HumanMessage(content= body_message)]
        result = llm.invoke(message)
            
        if result.classification == "notify":
            
            print(f"\nClassify this email: **NOTIFY**")
            goto = "summarizer"
            update = {"decision": result.classification}
            
        elif result.classification == "ignore":

            print(f"\nClassify this email: **IGNORE**")
            goto = END
            update = {"decision": result.classification}
            
        else:
            raise ValueError(f"Invalid classification: {result.classification}")
        
        print(f"\nDecision: {result.classification}")
        print(f"Reason: {result.reasoning}\n")
        
        return Command(goto= goto, update= update)
        
        
        
    def summarizer(self, state: State):
        
        print(f"\nSummarizing the email...")
        
        llm = self.model.with_structured_output(SummarizerOutputSchema)
        
        author, to, subject, body, id = parse_email(state["input_email"])
        email_content = format_email_markdown(subject, author, to, body, id)
        
        sys_msg = summary_system_prompt.format(summarizer_instructions= default_summarizer_instruction)
        user_msg = summary_user_prompt.format(content= email_content)
        
        message = [SystemMessage(content= sys_msg), HumanMessage(content= user_msg)]
        response = llm.invoke(message)
        
        print(f"Summary: {response}")

        goto = "interrupts_handler"
        update= {
            "summary": response,
        } 
        
        print(f"\nCompleted summarized the email")
        
        return Command(goto= goto, update= update)
        

    def interrupts_handler(self, state: State):
        author, to, subject, email_thread, id = parse_email(state["input_email"])
        email = format_email_markdown(subject, author, to, email_thread, id)

        
        request = interrupt({
            "question": "Do you want to response to this email?",
            "show_email": email,
            "show_summary": state["summary"]
        })
    
        
        if request.get("flag") is True:
            goto = "writer"
            update = {
                "interrupt_decision": "response",
                "messages": HumanMessage(
                                    content = writer_user_prompt.format(
                                        recipients = author,
                                        email_content = email,
                                        summary_version = state["summary"],
                                        users_intent = request.get("feedback", ""),
                                )
                ),
            }
        elif request.get("flag") is False:
            goto = END
            update = {
                "interrupt_decision": "ignore",
            }
        else:
            raise ValueError(f"Invalid argument: {request["type"]}")
        
        return Command(goto= goto, update= update)


    def writer(self, state: State):
        llm = self.model.with_structured_output(WriterOutputSchema)
        messages = [SystemMessage(content= writer_system_prompt.format(writer_instruction=default_writer_instruction))]\
                                                                +                                                      \
                                                        state["messages"]
        
        
        response = llm.invoke(messages)
        to, subject, body = response.gmail_schema.to, response.gmail_schema.subject, response.gmail_schema.message
        draft = format_send_email_markdown(subject, to, body)
        
        return Command(
            goto = "send_response", 
            update = {
                    "first_write": False, 
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
        
        if request["flag"] is True:
                        
            to = state['output_schema'].gmail_schema.to
            subject = state['output_schema'].gmail_schema.subject
            message = state['output_schema'].gmail_schema.message
            
            goto = END
            update = {"send_decision": "response"}
            
            print(f"Sending response to: {to}")
            
            tool.invoke(
                {
                    "to": to,
                    "subject": subject,
                    "message": message
                }
            )
            
            print(f"\nResponse sent:\n\nTo: {to}\nSubject: {subject}\nBody: {message}")
            return Command(goto= goto, update= update)
        
        elif request["flag"] is False:
            
            goto = "writer"            
            previous_response = AIMessage(
                content= state["draft_response"]
            )
            feedback_msg = HumanMessage(
                content=(
                    "The previous draft wasn't quite right and align to my intented. \
                     Take a look of the feedback below:\n "
                    f"{request.get('feedback', '<no feedback given>')}\n"
                    "Please rewrite the reply accordingly."
                )  
            )
            
            feedback = [previous_response, feedback_msg]
            
            return Command(
                goto= goto,
                update = {
                    "messages": state["messages"] + feedback,
                    "send_decision": "rewrite"
                }
            )
            