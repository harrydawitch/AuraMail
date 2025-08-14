from queue import Queue
import time
from typing import Any, Dict

class Communicator:
    def __init__(self):
        self.events = Queue()
        self.commands = Queue()
        
    def send_events(self, type_event: str, data: Any) -> None:
        events = {"type": type_event, "data": data}
        self.events.put(events)
    
    def send_commands(self, type_command: str, data: Any) -> None:
        commands = {"type": type_command, "data": data}
        self.commands.put(commands)    
        
    def poll_events(self, callback_func, max_events_per_poll=5):
        events_processed = 0
        
        try:
            # Process multiple events per poll cycle to prevent backlog
            while not self.events.empty() and events_processed < max_events_per_poll:
                event = self.events.get_nowait()  # Non-blocking get
                callback_func(event)
                events_processed += 1
                
            if events_processed > 0:
                print(f"\nProcessed {events_processed} events - (poll_events)")
                
        except Exception as e:
            print(f"\nError processing events: {e} - (poll_events)")
    
    def poll_commands(self, callback_func):
        print(f"**START POLL COMMANDS** - (poll_commands)")
        time.sleep(0.05)

        while True:
            try:
                command = self.commands.get()   # This blocks until something is available
                callback_func(command)
            except Exception as e:
                print(f"\nError processing command: {e} - (poll_commands)")
                time.sleep(1)
        
    
    
class BackendCommunicator(Communicator):
    
    def __init__(self, events: Queue, commands: Queue, processor=None, workflow_manager=None):
        self.events = events
        self.commands = commands
        self.processor = processor 
        self.workflow_manager = workflow_manager
        
    def set_dependencies(self, processor, workflow_manager):
        """Set processor and workflow manager after initialization"""
        self.processor = processor
        self.workflow_manager = workflow_manager

    def process_events(self, event_results: Dict):
        
        if "new_email" in event_results:
            email = event_results.get("new_email")
            self.send_events(type_event= "new_email", data= email)            
        
        elif (event_results.get("decision", "") == "notify") and (event_results.get("first_write")):
            summary = event_results.get("summary")
            id = event_results.get("input_email")["id"]
            
            data = {
                "summary": summary.summary_content,
                "id": id
            }
            self.send_events(type_event= "notify", data= data)

        elif (event_results.get("decision", "") == "ignore") and (event_results.get("first_write")):
            id = event_results.get("input_email")["id"]
            summary = event_results.get("summary", "")

            
            data = {
                "summary": summary,
                "id": id
            }
            self.send_events(type_event= "spam", data= data)
    
        elif not event_results.get("first_write") and not event_results.get("send_decision") and event_results.get("input_email"):
            draft = event_results.get("draft_response")
            id = event_results.get("input_email")["id"]
            
            data = {
                "draft": draft,
                "id": id
            }
            self.send_events(type_event= "approval", data= data)
            
        elif event_results and (event_results.get("send_decision") == "rewrite") and event_results.get("input_email"):
            draft = event_results.get("draft_response")       
            id = event_results.get("input_email")["id"]
            data = {
                "draft": draft,
                "id": id
            }
                
            self.send_events(type_event= "rewrite", data= data)

        # Handle initial send email draft (first write)
        elif not event_results.get("first_write") and not event_results.get("send_decision") and not event_results.get("input_email"):
            draft = event_results.get("draft_response")
            data = {"draft": draft}
            self.send_events(type_event="send_email_draft", data=data)
        
        # Handle send email rewrite
        elif event_results.get("send_decision") == "rewrite" and not event_results.get("input_email"):
            print(f"\n\n\n{event_results.keys()}\n\n\n")
            draft = event_results.get("draft_response")
            data = {"draft": draft}
            self.send_events(type_event="send_email_rewrite", data=data)

            
    def process_commands(self, command: Dict):
        """Process incoming commands from frontend"""
        try:
            command_type = command.get("type")
            command_data = command.get("data", {})
            
            print(f"\nProcessing command: {command_type} - (process_commands)")

            if command_type == "generate_email":
                self._handle_generate_email(command_data)
            
            elif command_type in ["approve_draft", "reject_draft", "send_email"]:
                # Handle send email workflow commands
                self._handle_send_email_workflow(command_type, command_data)
            
            else:
                # Handle regular email response workflow
                self._handle_resume_workflow(command_data)

        except Exception as e:
            print(f"\nError processing command: {e} - (process_commands)")

    def _handle_send_email_workflow(self, command_type: str, command_data: Dict):
        """Handle send email workflow commands"""
        try:
            # Import here to avoid circular imports
            from src.workflow import SendEmailWorkflow
            
            workflow_id = command_data.get("workflow_id")
            if not workflow_id:
                print("\nNo workflow_id provided for send email command")
                return
            
            # Add missing attributes that nodes.py might need
            if not hasattr(self, 'model'):
                self.model = "gpt-4o-mini"  # Default model
            if not hasattr(self, 'db_path'):
                self.db_path = "db/workflows.db"  # Default db path
                
            workflow_instance = SendEmailWorkflow(self.model, self.db_path)
            wf = workflow_instance.get_workflow
            
            # Map command types to resume inputs
            if command_type == "approve_draft":
                resume_inputs = {"flag": True}
            elif command_type == "reject_draft":
                resume_inputs = {
                    "flag": False, 
                    "feedback": command_data.get("feedback", "")
                }
            elif command_type == "send_email":
                resume_inputs = {"flag": True}
            
            self.processor.workflow_processor.process_email(
                workflow_id=workflow_id,
                wf=wf,
                resume_inputs=resume_inputs,
                wf_manager=self.workflow_manager,
                communicator=self,
                resume=True
            )
            
        except Exception as e:
            print(f"Error in _handle_send_email_workflow: {e}")
            import traceback
            traceback.print_exc()
        
    def _handle_generate_email(self, command_data: Dict):
        from src.prompts import send_email_writer_prompt
        from langchain_core.messages import HumanMessage
        
        from_email = command_data.get("from_email")
        to_email = command_data.get("to_email")
        users_intent = command_data.get("users_intent")
        workflow_id = command_data.get("workflow_id")
        
        messages = HumanMessage(content=send_email_writer_prompt.format(
            from_user=from_email, 
            to_user=to_email, 
            users_intent=users_intent
        ))
        inputs = {"messages": [messages]}
        
        if not self.workflow_manager or not self.processor:
            print("\nWorkflowManager or EmailProcessor not available")
            return
        
        self.processor.process_generate_email(
            inputs=inputs,
            workflow_id=workflow_id
        )

    def _handle_resume_workflow(self, command_data: Dict):
        """Handle workflow resume command"""
        try:
            from src.workflow import EmailResponseWorkflow
            
            # Add missing attributes
            if not hasattr(self, 'model'):
                self.model = "gpt-4o-mini"
            if not hasattr(self, 'db_path'):
                self.db_path = "db/workflows.db" 
                
            workflow_instance = EmailResponseWorkflow(self.model, self.db_path)
            wf = workflow_instance.get_workflow
            workflow_id = command_data.get("workflow_id")

            if not workflow_id:
                print("\nNo workflow_id provided in resume command")
                return
            
            if not self.workflow_manager:
                print("\nWorkflowManager not available")
                return
            
            if not self.processor:
                print("\nEmailProcessor not available")
                return
            
            # Resume workflow through processor
            self.processor.workflow_processor.process_email(
                workflow_id= workflow_id,
                wf= wf,
                resume_inputs=command_data,
                wf_manager=self.workflow_manager,
                communicator=self,
                resume=True
            )
            
        except Exception as e:
            print(f"Error in _handle_resume_workflow: {e}")
            import traceback
            traceback.print_exc()
            

class FrontendCommunicator(Communicator):
    def __init__(self, events: Queue, commands: Queue):
        self.events = events
        self.commands = commands
        self.gui = None 
        
    def set_gui(self, gui):
        """Set the GUI reference for updating the interface"""
        self.gui = gui
    
    def process_events(self, event: Dict):
        """Process events from backend and update GUI"""
        try:
            event_type = event.get("type")
            event_data = event.get("data", {})
            
            print(f"\nFrontend processing event: {event_type} - (process_events)")
            
            if event_type == "new_email":
                self._handle_new_email(event_data)
                
            elif event_type == "notify":
                self._handle_notify_decision(event_data)
                
            elif event_type == "spam":
                self._handle_spam_email(event_data)
                
            elif event_type == "approval":
                self._handle_draft_ready(event_data)
            
            elif event_type == "rewrite":
                self._handle_rewrite(event_data)

            elif event_type in ["send_email_draft", "send_email_rewrite"]:
                self._handle_send_email_draft(event_data)
                
        except Exception as e:
            print(f"\nError processing frontend event: {e}")

    def _handle_send_email_draft(self, data):
        """Handle draft generated for send email"""
        if self.gui and hasattr(self.gui, 'send_email_view'):
            draft = data.get("draft")
            self.gui.handle_draft_generated(draft_content=draft)
    
    def _handle_new_email(self, data):
        """Handle new email received"""

        id = data.get("id")
        thread = data.get("threadId")
        snippet = data.get("snippet")
        body = data.get("body")
        subject = data.get("subject")
        sender = data.get("sender")
        time = data.get("time")
        workflow_id = data.get("workflow_id")
        
        if self.gui:
            from src.email_service import EmailService, EmailData
            print(f"\nNew email received: {snippet} - (_handle_new_email")
            
            EmailService.add_new_email(email= EmailData(subject, thread, sender, body, time, id= id, workflow_id= workflow_id))
            if self.gui.current_category == "home":
                self.gui.load_emails("home")
    
    def _handle_notify_decision(self, data):
        """Handle email classified as notify"""
        if self.gui:
            from src.utils import Notification
            from src.email_service import EmailService
            
            notification = Notification()

            summary = data.get("summary") 
            email_id = data.get("id")

            print(f"\nEmail `{email_id}` classified as notify with summary - (_handle_notify_decision)")
            
            email = EmailService.get_email("home", email_id)
            email.summary = summary
            email.category = "notify"
            sender = email.sender
            
            notification.new_notify_email(sender, summary)
            
            EmailService.add_to_notify(email)
            
            # Refresh notify view if currently viewing it
            if self.gui.current_category == "notify":
                self.gui.load_emails("notify")
                
    def _handle_spam_email(self, data):
        """Handle email classified as spam"""
        if self.gui:

            from src.email_service import EmailService
            email_id = data.get("id")
            print(f"\nEmail {email_id} classified as spam - (_handle_spam_email)")

            
            email = EmailService.get_email("home", email_id)
            email.category = "ignore"
            EmailService.add_to_ignore(email)
            
            if self.gui.current_category == "ignore":
                self.gui.load_emails("ignore")
                

    def _handle_draft_ready(self, data):
        """Handle draft response ready for approval"""
        if self.gui:
            try:
                from src.email_service import EmailService
                
                draft = data.get("draft")
                email_id = data.get("id")
                
                print(f"\nDraft ready for approval {email_id} - (_handle_draft_ready)")
                
                email = EmailService.get_email("home", email_id)
                email.draft_response = draft
                
                EmailService.notify_to_pending(email)
                
                # Refresh pending view if currently viewing it
                if self.gui.current_category == "human":
                    self.gui.load_emails("human")
            
            except Exception:
                draft = data.get("draft")
                self.gui.handle_draft_generated(draft_content= draft)
                
    def _handle_rewrite(self, data):
        if self.gui:
            from src.email_service import EmailService
            draft = data.get("draft")
            email_id = data.get("id")
            
            print(f"\nRewrite draft response. Waiting for human approval - (_handle_rewrite)")
            
            email = EmailService.get_email("human", email_id)
            EmailService.regenerate_draft_response(email, draft)
            
            self.gui.email_detail._show_draft_response(draft)
                
    def has_pending_events(self):
        """Check if there are pending events without removing them"""
        return not self.events.empty()