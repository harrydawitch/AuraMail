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
        
        
    def process_commands(self, command: Dict):
        """Process incoming commands from frontend"""
        try:
            command_type = command.get("type")
            command_data = command.get("data", {})
            
            print(f"\nProcessing command: {command_type} - (process_commands)")
    
            self._handle_resume_workflow(command_data)

        except Exception as e:
            print(f"\nError processing command: {e} - (process_commands)")
    
    
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
    
        elif not event_results.get("first_write") and not event_results.get("send_decision"):
            draft = event_results.get("draft_response")
            id = event_results.get("input_email")["id"]
            
            data = {
                "draft": draft,
                "id": id
            }
            self.send_events(type_event= "approval", data= data)
            
        elif event_results and (event_results.get("send_decision") == "rewrite"):
            draft = event_results.get("draft_response")
            id = event_results.get("input_email")["id"]
            
            data = {
                "draft": draft,
                "id": id
            }
            self.send_events(type_event= "rewrite", data= data)
            
        

    def _handle_resume_workflow(self, command_data: Dict):
        """Handle workflow resume command"""
        
        workflow_id = command_data.get("workflow_id")

        if not workflow_id:
            print("\nNo workflow_id provided in resume command - (_handle_resume_workflow)")
            return
        
        if not self.workflow_manager:
            print("\nWorkflowManager not available - (_handle_resume_workflow)")
            return
        
        if not self.processor:
            print("\nEmailProcessor not available - (_handle_resume_workflow)")
            return
                        
        # Resume workflow through processor
        self.processor.workflow_processor.process_email(
            workflow_id=workflow_id,
            resume_inputs=command_data,
            resume=True,
            wf_manager=self.workflow_manager,
            communicator=self
        )
            

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
                
        except Exception as e:
            print(f"\nError processing frontend event: {e}")
    
    def _handle_new_email(self, data):
        """Handle new email received"""

        id = data.get("id")
        snippet = data.get("snippet")
        body = data.get("body")
        subject = data.get("subject")
        sender = data.get("sender")
        time = data.get("time")
        workflow_id = data.get("workflow_id")
        
        if self.gui:
            from src.email_service import EmailService, EmailData
            print(f"\nNew email received: {snippet} - (_handle_new_email")
            
            EmailService.add_new_email(email= EmailData(subject, sender, body, time, id= id, workflow_id= workflow_id))
            if self.gui.current_category == "home":
                self.gui.load_emails("home")
    
    def _handle_notify_decision(self, data):
        """Handle email classified as notify"""
        if self.gui:
            from src.email_service import EmailService
            summary = data.get("summary") 
            email_id = data.get("id")
                        
            print(f"\nEmail `{email_id}` classified as notify with summary - (_handle_notify_decision)")
            email = EmailService.get_email("home", email_id)
            email.summary = summary
            email.category = "notify"
            
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
                
    def _handle_rewrite(self, data):
        if self.gui:
            from src.email_service import EmailService
            draft = data.get("draft")
            email_id = data.get("id")
            
            print(f"\nRewrite draft response. Waiting for human approval - (_handle_rewrite)")
            
            email = EmailService.get_email("human", email_id)
            EmailService.regenerate_draft_response(email, draft)
            
            if self.gui.current_category == "human":
                self.gui.load_emails("human")

                
    def has_pending_events(self):
        """Check if there are pending events without removing them"""
        return not self.events.empty()