import os
import time
import uuid
import json
import threading
from typing import Set, Optional, List, Dict

from datetime import datetime
from email.utils import parsedate_to_datetime
from datetime import datetime

from src.connect import Communicator, BackendCommunicator

from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.search import GmailSearch



class EmailSearcher:
    def __init__(self, gmail_api: GmailToolkit):
        self.gmail = gmail_api
        self.search_tool = GmailSearch(api_resource= self.gmail.api_resource) 
        
    def _get_time(self, format: str) -> str:
        return datetime.now().strftime(format)
            
    def fetch_email(self, state) -> List[Dict]:
        last_shutdown_date = state.last_shutdown_date
        
        if last_shutdown_date and isinstance(last_shutdown_date, str):
            print(f"\n**Fetch emails**")
            return self.search_tool.invoke(f"label:inbox after:{last_shutdown_date}")
        else:
            return self.search_tool.invoke(f"label:inbox after:{self._get_time(format='%Y/%m/%d')}")

class EmailState:
    """Manages the state of processed emails and threads"""
    
    def __init__(self, state_file: str = "db/email_state.json"):
        self.current_email_ids: Set[str] = set()
        self.processed_threads: Set[str] = set()
        self.state_file = state_file
        self.last_check: Optional[str] = None
        self.is_first_run: bool = True
        self.last_shutdown_time: Optional[str] = None
        self.last_shutdown_date: Optional[str] = None
    
        self._load_state()

    def _load_state(self) -> None:
        """Load state from file"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.current_email_ids = set(data.get('current_email_ids', []))
                    self.processed_threads = set(data.get('processed_threads', []))
                    self.last_shutdown_time = data.get('last_shutdown_time')
                    self.last_shutdown_date = data.get('last_shutdown_date')
                    self.is_first_run = data.get('is_first_run', True)
                    self.last_check = data.get('last_check')
                    
                    print(f"Loaded state: {len(self.current_email_ids)} emails, last shutdown: {self.last_shutdown_time}")
            except Exception as e:
                print(f"Error loading state: {e}")
                self._create_empty_state_file()
        else:
            self._create_empty_state_file()
            
    def save_state(self) -> None:
        """Save current state to file"""
        try:
            state_data = {
                'current_email_ids': list(self.current_email_ids),
                'processed_threads': list(self.processed_threads),
                'last_shutdown_time': self.last_shutdown_time,
                'last_check': self.last_check,
                'last_shutdown_date': self.last_shutdown_date,
                'is_first_run': self.is_first_run,
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=4)
                
        except Exception as e:
            print(f"Error saving state: {e}")
            
    def _create_empty_state_file(self) -> None:
        """Create empty state file"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        self.save_state()
        print(f"Created new state file: {self.state_file}")
    
    def add_email(self, email_id: str, thread_id: str) -> None:
        """Add email and thread to processed sets"""
        self.current_email_ids.add(email_id)
        self.processed_threads.add(thread_id)
        self.last_check = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    
    def is_new_email(self, email_id: str, thread_id: str, sender: str) -> bool:
        """Check if email is new and should be processed"""
        my_email = os.environ.get("MY_EMAIL", "").strip().lower()
        sender_lower = sender.lower().strip()
        
        # Check conditions
        is_new_id = email_id not in self.current_email_ids
        is_new_thread = thread_id not in self.processed_threads
        is_not_from_me = my_email not in sender_lower if my_email else True
        
        result = is_new_id and is_new_thread and is_not_from_me
        
        print(f"Final result: {result} (new_id: {is_new_id}, new_thread: {is_new_thread}, not_from_me: {is_not_from_me})")
        
        return result
    
    
    def handle_first_run(self, search_results: List[Dict]) -> None:
        """Handle initial run to collect existing emails"""
        
        if search_results:
            self.current_email_ids = {email["id"] for email in search_results}    
            
            print(f"\n**First run**\nCollecting existing emails\nExisting email ids: {len(self.current_email_ids)} emails")
            print(f"Email IDs collected: {list(self.current_email_ids)}")
            
        self.is_first_run = False

    def record_shutdown(self) -> None:
        """Record when the system is shutting down"""
        self.last_shutdown_time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        self.last_shutdown_date = datetime.now().strftime("%Y/%m/%d")
        self.save_state()
        print(f"Recorded shutdown time: {self.last_shutdown_time}")
        
    
class WorkflowManager:
    """Manages active workflows and their states"""
    
    def __init__(self, db_path: str = "db/workflows.json"):
        self.active_workflows: Dict[str, Dict] = {}
        self.lock = threading.Lock()
        self.db_path = db_path
        self.load_workflows = self._load_workflows()

        
    def save_workflows(self):
        with open(self.db_path, "w") as json_file:
            json.dump(self.active_workflows, json_file, indent= 4)
    
    def _load_workflows(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, "r") as f:
                data = json.load(f)
                if data:
                    self.active_workflows = data
                else:
                    self.active_workflows = {}
        else:
            with open(self.db_path, 'w', encoding="utf-8") as f:
                json.dump(self.active_workflows, f, indent= 4)
            
            print(f"--Succesfully create json file for storing workflows-- - (load_workflows)")
        
    def add_workflow(self, workflow_id: str, config: Dict, inputs: Dict):
        """Add a new workflow to track"""
        with self.lock:
            self.active_workflows[workflow_id] = {
                'config': config,
                'inputs': inputs,
                'thread_id': workflow_id,
                'status': 'active'
            }
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict]:
        """Get workflow by ID"""
        with self.lock:
            return self.active_workflows.get(workflow_id)
    
    def remove_workflow(self, workflow_id: str):
        """Remove completed workflow"""
        with self.lock:
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
    
    def update_workflow_status(self, workflow_id: str, status: str):
        """Update workflow status"""
        with self.lock:
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]['status'] = status


    def initialize_inputs(self, email_input: dict = {}, send_email: bool = False):
            with self.lock:
                if send_email:
                    inputs = {
                        "messages": email_input.get("messages"),
                        "send_decision": "",
                        "draft_response": "",
                        "first_write": True,
                        "output_schema": {} 
                    }
                    
                else:
                    inputs = {
                        "input_email": email_input,
                        "messages": [],
                        "decision": "",
                        "interrupt_decision": "",
                        "send_decision": "",
                        "summary": " ",
                        "draft_response": "",
                        "first_write": True,
                        "output_schema": {} 
                    }
                    
                return inputs
        
    def initialize_config(self, workflow_id: str):
        
        with self.lock:
            return {"configurable": {"thread_id": workflow_id}}

class WorkflowProcessor:
    def process_email(self, 
                email: Dict = {}, 
                workflow_id: str = "",
                wf = None,
                wf_manager: WorkflowManager = None, 
                communicator: BackendCommunicator = None,
                resume: bool = False, 
                resume_inputs: Dict = None,
                send_email: bool = False) -> None:
        
        """Process email in a separate thread"""
        if send_email:
            print(f"Generating email...")    

            self._start_execution(
                self._generate_email,
                email, workflow_id, wf, wf_manager, communicator
            )
        
        elif not resume:
            # Only print snippet for regular emails, not send emails
            if "snippet" in email:
                print(f"Processing email: {email['snippet']}")
            else:
                print(f"Processing email workflow: {workflow_id}")

            self._start_execution(
                self._process,
                email, wf, wf_manager, communicator
            )

        else:
            print(f"Resuming workflow: {workflow_id}")
            self._start_execution(
                self._resume,
                workflow_id, wf, resume_inputs, wf_manager, communicator
            )

    def _generate_email(self, email: Dict, workflow_id: str, wf, wf_manager, communicator):
        
        inputs = wf_manager.initialize_inputs(email, send_email=True)
        thread_config = wf_manager.initialize_config(workflow_id)
        
        wf_manager.add_workflow(workflow_id, thread_config, inputs)
        
        try:
            result = wf.invoke(inputs, config=thread_config)
            
            # Check if workflow needs user interaction
            if self._should_sendback(result):
                self._sendback(result, workflow_id, communicator, wf_manager)
            else:
                # Email was sent successfully, cleanup
                print(f"Send email workflow {workflow_id} completed successfully")
                wf_manager.remove_workflow(workflow_id)
                            
        except Exception as e:
            print(f"Error in send email workflow {workflow_id}: {e}")
            import traceback
            traceback.print_exc()
            wf_manager.remove_workflow(workflow_id)

    def _process(self, email: Dict, wf, wf_manager, communicator):
        
        workflow_id = email["workflow_id"]
        inputs = wf_manager.initialize_inputs(email)
        thread_config = wf_manager.initialize_config(workflow_id)
        
        wf_manager.add_workflow(workflow_id, thread_config, inputs)
        
        try:
            result = wf.invoke(inputs, config= thread_config)
            self._sendback(result, workflow_id, communicator, wf_manager)
                        
        except Exception as e:
            print(f"Error processing email in WorkflowProcessor -> process():\n{workflow_id}:\n   {e}")
            wf_manager.remove_workflow(workflow_id)
        
        
    def _resume(self, workflow_id: str, wf, resume_inputs: Dict, wf_manager, communicator):
        
        # Get workflow data
        workflow_data = wf_manager.get_workflow(workflow_id)
        
        if not workflow_data:
            print(f"Workflow {workflow_id} not found")
            return

        if workflow_data['status'] != 'waiting':
            print(f"Workflow {workflow_id} is not waiting for input")
            return
        
        # Get thread config and current workflow instance
        thread_config = workflow_data.get("config")        
        if not thread_config:
            print(f"Missing config {workflow_id}")
            return
        
        if not resume_inputs:
            print(f"Not found commands from frontend for {workflow_id}")
            return
    
        try:
            from langgraph.types import Command
            
            command = Command(resume=resume_inputs)
            result = wf.invoke(command, config= thread_config)
            
            if self._should_sendback(result):
                self._sendback(result, workflow_id, communicator, wf_manager)
            
            else: # Workflow completed successfully
                print(f"Workflow {workflow_id} completed successfully")
                wf_manager.remove_workflow(workflow_id)
                       
            
        except Exception as e:
            print(f"ERROR: Full exception details:")
            print(f"  Exception type: {type(e)}")
            print(f"  Exception message: {str(e)}")
            import traceback
            traceback.print_exc()
            wf_manager.remove_workflow(workflow_id)
    
            
    def _start_execution(self, process_func, *args) -> None:
        """Start execution in separate thread"""
        threading.Thread(target=process_func, args=args).start()
                
    def _should_sendback(self, event_results: Dict) -> bool:
        return "__interrupt__" in event_results
    
    def _sendback(self, event_results: Dict, workflow_id: str, communicator, wf_manager) -> None:        
            communicator.process_events(event_results)
            wf_manager.update_workflow_status(workflow_id, status= "waiting")
   
    
class EmailProcessor:
    def __init__(self, workflow_processor: WorkflowProcessor, wf_manager: WorkflowManager, communicator: BackendCommunicator, state: EmailState, model: str, gmail_api: GmailToolkit, db_path: str):
        self.workflow_processor = workflow_processor
        self.wf_manager = wf_manager
        self.communicator = communicator
        self.state = state
        self.model = model
        self.gmail_api= gmail_api
        self.db_path = db_path
        
    def process_generate_email(self, inputs: Dict, workflow_id: str = None) -> None: 
        """Generate draft email for user to send email"""
        from src.workflow import SendEmailWorkflow

        if not workflow_id:
            workflow_id = str(uuid.uuid4())
            
        workflow_instance = SendEmailWorkflow(self.model, self.db_path)
        wf = workflow_instance.get_workflow      
        
        self.workflow_processor.process_email(
            email=inputs,
            workflow_id=workflow_id,
            wf=wf,
            wf_manager=self.wf_manager, 
            communicator=self.communicator,
            send_email=True
        )
        
        

    def process_new_emails(self, search_results: List[Dict]) -> None:
        """Process new emails from search results"""
        
        new_emails_count = 0
        
        print(f"\n=== Processing {len(search_results)} emails === - (process_new_emails)")
        
        for email_dict in search_results:
            email_id = email_dict["id"]
            thread_id = email_dict["threadId"]
            sender = email_dict.get("sender", "Unknown sender")
            
            if self.state.is_new_email(email_id, thread_id, sender):
                print(f"✓ NEW EMAIL DETECTED - Processing...")
                
                # Assign workflow id
                email_dict = self._preprocess_new_email(email_dict)
                
                # add this email to current emails and threads state
                self.state.add_email(email_id, thread_id)
                self.communicator.send_events(type_event= "new_email", data= email_dict)
                
                from src.workflow import EmailResponseWorkflow
                workflow_instance = EmailResponseWorkflow(self.model, self.db_path)
                wf = workflow_instance.get_workflow

                self.workflow_processor.process_email(
                    email=email_dict,
                    wf= wf,
                    wf_manager=self.wf_manager, 
                    communicator=self.communicator,
                )
                
                new_emails_count += 1
        
        if new_emails_count == 0:
            print("\n=== No new emails found. Waiting for next run! ===")
        else:
            print(f"\n=== Processed {new_emails_count} new emails ===")
        
    def _preprocess_new_email(self, email: Dict) -> Dict:
        """Assigning workflow id and sent time to email"""
        service = self.gmail_api.api_resource
        wf_id = str(uuid.uuid4())
        
        msg_id = email["id"]
        message_data = service.users().messages().get(
            userId="me",
            id=msg_id,
            format="full"
        ).execute()
        headers = message_data["payload"]["headers"]
        date_str = next(h["value"] for h in headers if h["name"].lower() == "date")
        
        sent_time = parsedate_to_datetime(date_str).strftime("%d/%m/%Y - %H:%M")
        
        email["time"] = sent_time
        email["workflow_id"] = wf_id
        
        return email
    
    
    
class EmailManager:
    def __init__(self, model: str, communicator: Communicator, gmail_api: GmailToolkit, check_interval: int, db_path: str):
        self.model = model
        self.db_path = db_path
        self.check_interval = check_interval
        
        self.state = EmailState()
        self.searcher = EmailSearcher(gmail_api)
        self.workflow_manager = WorkflowManager()
        self.communicator = BackendCommunicator(
            communicator.events, 
            communicator.commands
        )
        
        # Set model and db_path on communicator for workflow creation
        self.communicator.model = model
        self.communicator.db_path = db_path
        
        self.processor = EmailProcessor(
            workflow_processor= WorkflowProcessor(), 
            wf_manager= self.workflow_manager,
            communicator= self.communicator,
            state = self.state,
            model=self.model,
            gmail_api= gmail_api,
            db_path=self.db_path
        )
        
        self.communicator.set_dependencies(self.processor, self.workflow_manager)
        
    
    def run(self) -> None: 
        """Main monitoring loop with token refresh"""
        print("\n===Starting email monitoring===")
        
        # Check token at startup
        print("\n=== Checking Gmail token at startup ===")
        if not self._check_and_refresh_gmail_token():
            print("⚠️ Warning: Gmail token check failed at startup - may encounter API issues")

        else:
            print("✅ Gmail token validated successfully at startup")
        
        last_token_check = time.time()  # Set initial check time to now
        TOKEN_CHECK_INTERVAL = 3600  # 1 hour in seconds

        self.commands_thread = threading.Thread(
            target=self.communicator.poll_commands, 
            args=(self.communicator.process_commands,), 
            daemon=True
        ).start()

        try:
            while True:
                try:
                    current_time = time.time()
                    
                    # Check token every hour (after startup check)
                    if current_time - last_token_check > TOKEN_CHECK_INTERVAL:
                        print("\n=== Checking Gmail token status ===")
                        if self._check_and_refresh_gmail_token():
                            last_token_check = current_time
                        else:
                            print("⚠️ Gmail token check failed - continuing with existing connection")
                    
                    # Search for today's emails
                    search_results = self.searcher.fetch_email(self.state)
                    print(f"+++ FETCHED EMAILS +++")
                    print(f"Number of emails in search results: {len(search_results)}")
                                    
                    if self.state.is_first_run:
                        self.state.handle_first_run(search_results)
                    
                    # Process new emails
                    self.processor.process_new_emails(search_results)
                    
                    # Wait before next check
                    time.sleep(self.check_interval)
                    
                except KeyboardInterrupt:
                    print("\nMonitoring stopped by user.")
                    break
                except Exception as e:
                    print(f"Error in monitoring loop: {e}")
                    
                    # If it's a Gmail API error, try token refresh
                    if "gmail" in str(e).lower() or "auth" in str(e).lower():
                        print("Detected potential Gmail auth error - attempting token refresh...")
                        if self._check_and_refresh_gmail_token():
                            print("✅ Token refreshed, retrying in next cycle")
                            last_token_check = time.time()  # Update check time after refresh
                        else:
                            print("❌ Token refresh failed")
                    
                    time.sleep(self.check_interval)
                    
        finally:
            # Record shutdown time when exiting
            self.shutdown()     
    
    def shutdown(self):
        """Clean shutdown with state saving"""
        print("Recording shutdown time...")
        self.state.record_shutdown()
        

    def _check_and_refresh_gmail_token(self):
        """Check and refresh Gmail token, reinitialize searcher if needed"""
        try:
            from helper import refresh_gmail_token
            
            # Check if helper returns 3 values (enhanced version)
            result = refresh_gmail_token()
            if len(result) == 3:
                refresh_success, message, was_refreshed = result
            else:
                # Fallback for old version
                refresh_success, message = result
                was_refreshed = "refreshed" in message.lower()
            
            if refresh_success:
                print(f"Token check: {message}")
                
                # If token was refreshed, reinitialize searcher with new token
                if was_refreshed:
                    print("Token was refreshed - reinitializing Gmail searcher...")
                    try:
                        from langchain_google_community import GmailToolkit
                        new_gmail_tool = GmailToolkit()
                        self.searcher = EmailSearcher(new_gmail_tool)
                        print("✅ Gmail searcher reinitialized with fresh token")
                    except Exception as e:
                        print(f"Failed to reinitialize Gmail searcher after refresh: {e}")
                        return False
                
                return True
                
            else:
                print(f"Token issue: {message}")
                return False
                        
        except Exception as e:
            print(f"Error checking Gmail token: {e}")
            return False