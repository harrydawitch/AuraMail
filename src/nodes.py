
from src.states import SendEmailState, EmailResponseState, ClassifierOutputSchema, SummarizerOutputSchema, WriterOutputSchema

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

from typing import Union



class Nodes():

    def __init__(self, model: str):
        self.model= init_chat_model(model= model)
        self.gmail = GmailToolkit()
        
        
        
    def classifier(self, state: EmailResponseState): 
        
        llm = self.model.with_structured_output(ClassifierOutputSchema)
        
        author, to, subject, body, _ = parse_email(state["input_email"])
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
        
        print(f"Decision: {result.classification}")
        print(f"Reason: {result.reasoning}\n")
        
        return Command(goto= goto, update= update)
        
        
        
    def summarizer(self, state: EmailResponseState):
        
        print(f"\nSummarizing the email...")
        
        llm = self.model.with_structured_output(SummarizerOutputSchema)
        
        author, to, subject, body, id = parse_email(state["input_email"])
        email_content = format_email_markdown(subject, author, to, body, id)
        
        sys_msg = summary_system_prompt.format(summarizer_instructions= default_summarizer_instruction)
        user_msg = summary_user_prompt.format(content= email_content)
        
        message = [SystemMessage(content= sys_msg), HumanMessage(content= user_msg)]
        response = llm.invoke(message)
        
        print(f"Summary: {response.summary_content}")

        goto = "interrupts_handler"
        update= {
            "summary": response,
        } 
        
        print(f"Completed summarized the email\n")
        
        return Command(goto= goto, update= update)
        

    def interrupts_handler(self, state: EmailResponseState):
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


    def writer(self, state: Union[EmailResponseState, SendEmailState]):
        llm = self.model.with_structured_output(WriterOutputSchema)
        messages = [SystemMessage(content= writer_system_prompt.format(writer_instruction=default_writer_instruction))]\
                                                                +                                                      \
                                                        state["messages"]
        
        print(f"\nWriting response...")
        
        response = llm.invoke(messages)
        to, subject, body = response.gmail_schema.to, response.gmail_schema.subject, response.gmail_schema.message
        draft = format_send_email_markdown(subject, to, body)
        
        print(f"Finished writing response.")
        print(f"Response:")
        print(draft)
        
        return Command(
            goto = "send_response", 
            update = {
                    "first_write": False, 
                    "draft_response": draft,
                    "output_schema": response 
                }
            )
        
        
    def send_response(self, state: Union[EmailResponseState, SendEmailState]):
        request = interrupt(
            {
                "draft_response": state["draft_response"],
                "question": "Do you want to send this response?"
            }
        )
        
        if request["flag"] is True:
            
            # Check if output_schema exists and has the required structure
            if not state.get('output_schema') or not hasattr(state['output_schema'], 'gmail_schema'):
                print("Error: Missing or invalid output_schema in state")
                return Command(goto=END, update={"send_decision": "error"})
            
            to = state['output_schema'].gmail_schema.to
            subject = state['output_schema'].gmail_schema.subject
            message = state['output_schema'].gmail_schema.message
            
            goto = END
            update = {"send_decision": "response"}
            
            print(f"Sending response to: {to}")
            
            # Create properly formatted email message
            from src.utils import create_formatted_email
            formatted_message = create_formatted_email(to, subject, message)
            
            # Use the raw Gmail API instead of the LangChain tool
            try:
                # Get the Gmail service from the toolkit
                service = self.gmail.api_resource
                
                # Send the message
                result = service.users().messages().send(
                    userId='me',
                    body={'raw': formatted_message}
                ).execute()
                
                print(f"\nResponse sent successfully!")
                print(f"Message ID: {result['id']}")
                
            except Exception as e:
                print(f"Error sending email: {e}")
                # Fallback to original method if the above fails
                try:
                    tool = GmailSendMessage(api_resource= self.gmail.api_resource)
                    tool.invoke(
                        {
                            "to": to,
                            "subject": subject,
                            "message": message
                        }
                    )
                    print(f"Email sent successfully using fallback method!")
                except Exception as fallback_error:
                    print(f"Fallback method also failed: {fallback_error}")
                    return Command(goto=END, update={"send_decision": "error"})
            
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
            
            print(f"\n**REWRITE EMAIL**")
            
            return Command(
                goto= goto,
                update = {
                    "messages": state["messages"] + feedback,
                    "send_decision": "rewrite"
                }
            )
            