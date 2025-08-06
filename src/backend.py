import os
import time
import uuid
import json
import threading
from datetime import datetime
from typing import List, Dict, Optional, Set
from src.connect import Communicator, BackendCommunicator
from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.search import GmailSearch


class EmailSearcher:
    def __init__(self):
        gmail = GmailToolkit()
        self.search_tool = GmailSearch(api_resource= gmail.api_resource) 
        
    def _get_time(self, format: str) -> str:
        return datetime.now().strftime(format)
            

    def fetch_email(self) -> List[Dict]:
        print(f"\n**Fetch emails**")
        return self.search_tool.invoke(f"after:{self._get_time(format='%Y/%m/%d')}")

class EmailState:
    """Manages the state of processed emails and threads"""
    
    def __init__(self):
        self.current_email_ids: Set[str] = set()
        self.processed_threads: Set[str] = set()
        self.last_check: Optional[str] = None
        self.is_first_run: bool = True
    
    
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
        
        print(f"  Final result: {result} (new_id: {is_new_id}, new_thread: {is_new_thread}, not_from_me: {is_not_from_me})")
        
        return result
    
    def _should_reset_daily_state(self) -> bool:
        """Check if we should reset state for new day"""
        
        if not self.last_check:
            return False
        
        last_check_time = datetime.strptime(self.last_check, "%Y/%m/%d %H:%M:%S")
        midnight = datetime.now().replace(hour=0, minute=0, second=0)
        
        return last_check_time < midnight
    
    def _reset_daily_state(self) -> None:
        """Reset state for new day"""
        
        self.current_email_ids.clear()
        self.processed_threads.clear()
        
    def handle_daily_reset(self) -> None:
        """Handle daily state reset if needed"""
        
        if self._should_reset_daily_state():
            print("New day detected. Resetting daily state...")
            self._reset_daily_state()
    

    def handle_first_run(self, search_results: List[Dict]) -> None:
        """Handle initial run to collect existing emails"""
        
        if search_results:
            self.current_email_ids = {email["id"] for email in search_results}    
            
            print(f"\n**First run**\nCollecting existing emails\nExisting email ids: {len(self.current_email_ids)} emails")
            print(f"Email IDs collected: {list(self.current_email_ids)}")
            
        self.is_first_run = False

    
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
    
    def initialize_inputs(self, email_input: dict):
        with self.lock:
            inputs = {
                "input_email": email_input,
                "messages": [],
                "decision": "",
                "interrupt_decision": "",
                "send_decision": "",
                "summary": "",
                "draft_response": "",
                "first_write": True,
                "output_schema": {},
            }
            
            return  inputs
        
    def initialize_config(self, workflow_id: str):
        
        with self.lock:
            return {"configurable": {"thread_id": workflow_id}}

class WorkflowProcessor:
    def process_email(self, 
                email: Dict = {}, 
                workflow_id: str = "",
                model: str = "",
                db_path: str = None, 
                wf_manager: WorkflowManager = None, 
                communicator: BackendCommunicator = None, 
                resume: bool = False, 
                resume_inputs: Dict = None) -> None:
        """Process email in a separate thread"""
        
        if not resume:
            print(f"Processing email: {email["snippet"]}")    

            self._start_execution(
                self._process,
                email, model, db_path, wf_manager, communicator
            )
            

        else:
            print(f"Resuming workflow: {workflow_id}")
            self._start_execution(
                self._resume,
                workflow_id, model, db_path, resume_inputs, wf_manager, communicator
            )
    
    def _process(self, email: Dict, model, db_path, wf_manager, communicator):
        
        workflow_id = email["workflow_id"]
        inputs = wf_manager.initialize_inputs(email)
        thread_config = wf_manager.initialize_config(workflow_id)
        
        wf_manager.add_workflow(workflow_id, thread_config, inputs)
        
        try:
            from src.workflow import Workflow
            wf = Workflow(model, db_path).get_workflow
            result = wf.invoke(inputs, config= thread_config)
            self._sendback(result, workflow_id, communicator, wf_manager)
                        
        except Exception as e:
            print(f"Error processing email in WorkflowProcessor -> process():\n{workflow_id}:\n   {e}")
            wf_manager.remove_workflow(workflow_id)
        
        
    def _resume(self, workflow_id: str, model: str, db_path: str, resume_inputs: Dict, wf_manager, communicator):
        
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
            from src.workflow import Workflow
            
            command = Command(resume=resume_inputs)
            workflow_instance  = Workflow(model, db_path)
            wf = workflow_instance.get_workflow
            
            # Verify checkpointer is initialized
            if workflow_instance.checkpointer is None:
                print(f"ERROR: Checkpointer failed to initialize for {workflow_id}")
                wf_manager.remove_workflow(workflow_id)
                return        
    
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
    def __init__(self, workflow_processor: WorkflowProcessor, communicator: BackendCommunicator, model: str, db_path: str):
        self.workflow_processor = workflow_processor
        self.communicator = communicator 
        self.model = model
        self.db_path = db_path

    def process_new_emails(self, search_results: List[Dict], state: EmailState, wf_manager: WorkflowManager, communicator: BackendCommunicator) -> None:
        """Process new emails from search results"""
        
        new_emails_count = 0
        
        print(f"\n=== Processing {len(search_results)} emails === - (process_new_emails)")
        
        for i, email_dict in enumerate(search_results):
            email_id = email_dict["id"]
            thread_id = email_dict["threadId"]
            sender = email_dict.get("sender", "Unknown sender")
            
            if state.is_new_email(email_id, thread_id, sender):
                print(f"✓ NEW EMAIL DETECTED - Processing...")
                
                # Assign workflow id
                email_dict = self._preprocess_new_email(email_dict)
                
                # add this email to current emails and threads state
                state.add_email(email_id, thread_id)
                communicator.send_events(type_event= "new_email", data= email_dict)
                

                self.workflow_processor.process_email(
                    email=email_dict, 
                    wf_manager=wf_manager, 
                    communicator=communicator,
                    db_path= self.db_path,
                    model= self.model
                )
                
                new_emails_count += 1
            else:
                print(f"✗ Email already processed or from self - Skipping")
        
        if new_emails_count == 0:
            print("\n=== No new emails found. Waiting for next run! ===")
        else:
            print(f"\n=== Processed {new_emails_count} new emails ===")
        
    def _preprocess_new_email(self, email: Dict) -> Dict:
        """Assigning workflow id to each email"""
        wf_id = str(uuid.uuid4())
        email["workflow_id"] = wf_id
        email["time"] = datetime.now().strftime("%d/%m/%Y - %H:%M")
        
        return email
    
    
class EmailManager:
    def __init__(self, model: str, communicator: Communicator, check_interval: int, db_path: str):
        self.model = model
        self.db_path = db_path
        self.check_interval = check_interval
        
        self.searcher = EmailSearcher()
        self.state = EmailState()
        self.workflow_manager = WorkflowManager()
        self.communicator = BackendCommunicator(
            communicator.events, 
            communicator.commands
        )
        
        self.processor = EmailProcessor(
            WorkflowProcessor(), 
            self.communicator,
            model= self.model,
            db_path= self.db_path
        )
        
        self.communicator.set_dependencies(self.processor, self.workflow_manager)
        
        self.commands_thread = threading.Thread(
            target= self.communicator.poll_commands, 
            args= (self.communicator.process_commands,), 
            daemon= True
        ).start()
        
        
        
    def run(self) -> None: 
        """Main monitoring loop"""
        
        print("\nStarting email monitoring...")
        
        while True:
            try:
                # Search for today's emails
                search_results = self.searcher.fetch_email()
                print(f"Number of emails in search results: {len(search_results)}")
                
                # Handle daily reset
                self.state.handle_daily_reset()
                
                # Process new emails
                self.processor.process_new_emails(
                    search_results,
                    state= self.state,
                    wf_manager= self.workflow_manager,
                    communicator= self.communicator
                )
                
                # Wait before next check
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                print("\nMonitoring stopped by user.")
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(self.check_interval)