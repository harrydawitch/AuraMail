import os
import time
import threading
from queue import Queue
import uuid

from datetime import datetime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from abc import ABC, abstractmethod

from src.workflow import Workflow

from langchain_google_community.gmail.search import GmailSearch
from langgraph.types import Command


class EmailProcessor(ABC):
    """Abstract base class for email processing"""
    
    @abstractmethod
    def process(self, email: dict, config: Dict, agent) -> None:
        """Process a single email"""
        pass

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
        my_email = os.environ.get("MY_EMAIL", "")
        return (
            email_id not in self.current_email_ids and
            thread_id not in self.processed_threads and
            my_email not in sender
        )
    
    
    def should_reset_daily_state(self) -> bool:
        """Check if we should reset state for new day"""
        if not self.last_check:
            return False
        
        last_check_time = datetime.strptime(self.last_check, "%Y/%m/%d %H:%M:%S")
        midnight = datetime.now().replace(hour=0, minute=0, second=0)
        return last_check_time < midnight
    
    def reset_daily_state(self) -> None:
        """Reset state for new day"""
        self.current_email_ids.clear()
        self.processed_threads.clear()
    
    def handle_first_run(self, search_results: List[Dict], events: Queue) -> None:
        """Handle initial run to collect existing emails"""
        if search_results:
                        
            self.current_email_ids = {email["id"] for email in search_results}
            for  email in search_results:
                email["workflow_id"] = str(uuid.uuid4())
                
                events.put(
                    {
                        "type": {"new_email": email}
                    }
                )
                time.sleep(0.05)
            
            print(f"**First run**\nCollecting existing emails\nExisting email ids: {len(self.current_email_ids)} emails")
            
        self.is_first_run = False
    


class EmailSearcher:
    """Handles email searching operations"""
    
    def __init__(self, search_tool):
        self.search_tool = search_tool
    
    def search_today_emails(self) -> List[Dict]:
        """Search for emails from today"""
        today = datetime.now().strftime("%Y/%m/%d")
        return self.search_tool(f"after:{today}")


class WorkflowManager:
    """Manages active workflows and their states"""
    
    def __init__(self):
        self.active_workflows: Dict[str, Dict] = {}
        self.lock = threading.Lock()
    
    def add_workflow(self, workflow_id: str, workflow_instance: Workflow, config: Dict, inputs: Dict):
        """Add a new workflow to track"""
        with self.lock:
            self.active_workflows[workflow_id] = {
                'workflow': workflow_instance,
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

class ThreadedEmailProcessor(EmailProcessor):
    """Concrete implementation that processes emails in separate threads"""
    
    def __init__(self):
        self.workflow_manager = WorkflowManager()
    
    def process(self, email: dict,  workflow: Workflow, workflow_id: str, events: Queue) -> None:
        """Process email in a separate thread"""
        
        print(f"Processing email: {email["snippet"]}")        
        threading.Thread(
            target=self.process_email, 
            args=(email, workflow, events, workflow_id)
        ).start()
        

    def process_email(self, email_input, workflow, events, workflow_id):
        """Process email with resumable workflow"""
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
        
        # Create thread-specific config
        thread_config = self._get_config(workflow_id)
        
        # Add workflow to manager
        self.workflow_manager.add_workflow(workflow_id, workflow, thread_config, inputs)
        
        try:
            
            wf = workflow.get_workflow
            
            # Start workflow execution
            result = wf.invoke(inputs, config=thread_config)
            
            # Check if workflow was interrupted
            if result.get("decision") == "notify":
                
                # Workflow is waiting for human input
                self.workflow_manager.update_workflow_status(workflow_id, 'waiting_for_input')
                
                # Send interrupt event to GUI
                events.put({
                    "type": {
                        "decision": {
                            "category": "notify",
                            "email_id": email_input.get("id"),
                            "summary": result.get("summary", ""),
                        }
                    }
                })
                print(f"Workflow {workflow_id} interrupted, waiting for human input...")


            elif result.get("decision") ==  "ignore":
                events.put({
                    "type": {
                        "decision": {
                            "category": "ignore",
                            "email_id": email_input.get("id")

                        }
                    }
                })
                
                self.workflow_manager.remove_workflow(workflow_id)
                print(f"Workflow {workflow_id} ended. LLM decided to ignore this email")
    
            return
                
                
        except Exception as e:
            print(f"Error processing email in workflow {workflow_id}: {e}")
            self.workflow_manager.remove_workflow(workflow_id)
            
    
    def resume_workflow(self, workflow_id: str, feedback: str, flag: bool, events: Queue):
        """Resume an interrupted workflow with user feedback"""
        
        workflow_data = self.workflow_manager.get_workflow(workflow_id)
        
        if not workflow_data:
            print(f"Workflow {workflow_id} not found")
            return
        
        if workflow_data['status'] != 'waiting_for_input':
            print(f"Workflow {workflow_id} is not waiting for input")
            return
        
        try:
            # Update workflow status
            self.workflow_manager.update_workflow_status(workflow_id, 'resuming')
            
            # Resume workflow
            thread_config = {
                **workflow_data['config'],
                "configurable": {"thread_id": workflow_id}
            }
            
            wf = workflow_data['workflow'].get_workflow

            # Continue from where it left off
            wf.invoke(
                {
                    "feedback": feedback,
                    "flag": flag
                 }, 
                config=thread_config
            )

            final_state = wf.get_state(config=thread_config)
            result = final_state.values

            # Handle completion
            self._handle_workflow_completion(workflow_id, result, events)
            
        except Exception as e:
            print(f"Error resuming workflow {workflow_id}: {e}")
            self.workflow_manager.remove_workflow(workflow_id)
    
    
    def _handle_workflow_completion(self, workflow_id: str, result: Dict, events: Queue):
        """Handle workflow completion"""
        email_id = result["input_email"]["id"]
                
        
        if result.get("send_decision") == "response":
            # Clean up
            self.workflow_manager.remove_workflow(workflow_id)
            print(f"Workflow {workflow_id} completed successfully")
        
        
        elif result.get("send_decision") == "rewrite":
            self.workflow_manager.update_workflow_status(workflow_id, 'waiting_for_input')
            
            events.put({
                "type": {
                    "ask_for_approval": {
                        "category": "pending",
                        "email_id": email_id,
                        "draft_response": result.get("draft_response", "")
                    }
                }
            })
            
        elif result.get("first_write") is True:
            self.workflow_manager.update_workflow_status(workflow_id, 'waiting_for_input')
            
            events.put(
                {
                    "type": {
                        "show_draft": {
                            "category": "pending",
                            "email_id": email_id,
                            "draft_response": result.get("draft_response", "")
                        }
                    }
                }
            )
        
    def _get_config(self, workflow_id):
        return {"configurable": {"thread_id": workflow_id}}
    
    
class EmailMonitor:
    """Main email monitoring class"""
    
    def __init__(self, gmail_toolkit, workflow_model: str = "gpt-4o-mini",
                 events: Queue = None, commands: Queue = None, 
                 check_interval: int = 10, first_run_delay: int = 3):
        
        self.gmail = gmail_toolkit
        self.searcher = EmailSearcher(GmailSearch(api_resource=self.gmail.api_resource))
        
        self.processor = ThreadedEmailProcessor()
        self.state = EmailState()
        self.model = workflow_model
        
        self.events = events
        self.commands = commands
        
        self.check_interval = check_interval
        self.first_run_delay = first_run_delay
        
        # Start command processing thread
        self.command_thread = threading.Thread(target=self._process_commands, daemon=True)
        self.command_thread.start()
     
     
    def _process_commands(self):
        """Process commands from GUI"""
        
        while True:
            try:
                if not self.commands.empty():
                    command = self.commands.get(timeout= 1)
                    self._handle_command(command)
                    self.commands.task_done()
                else:
                    continue 
                    
            except Exception as e:
                print(f"Error processing command: {e}")
                time.sleep(1)
    
    def _handle_command(self, command: Dict):
        """Handle specific commands from GUI"""
        command_type = command.get("type", {})
        
        if isinstance(command_type, dict):
            if any(key in command_type for key in ["email_response", "email_approval"]):
                
                cmd_data = command_type.get("email_response") or command_type.get("email_approval")
                if cmd_data:
                    workflow_id = cmd_data.get("workflow_id")
                    feedback = cmd_data.get("feedback", "")
                    flag = cmd_data.get("flag")
                
            
                    print(f"Resuming workflow {workflow_id} with feedback: {feedback}")
            
                    # Resume workflow in separate thread
                    threading.Thread(
                            target=self.processor.resume_workflow,
                            args=(workflow_id, feedback, flag, self.events), daemon= True).start()
        
        elif command_type == "cancel_workflow":
            workflow_id = command.get("workflow_id")
            workflow_data = self.processor.workflow_manager.get_workflow(workflow_id)
            
            if workflow_data:
                self.processor.workflow_manager.remove_workflow(workflow_id)
                print(f"Workflow {workflow_id} cancelled")
        
        else:
            print(f"Unknown command type: {command_type}")
    
    def _process_new_emails(self, search_results: List[Dict]) -> None:
        """Process new emails from search results"""
        
        new_emails_count = 0
        
        for email_dict in search_results:
            email_id = email_dict["id"]
            thread_id = email_dict["threadId"]
            sender = email_dict["sender"]
            
            if self.state.is_new_email(email_id, thread_id, sender):
                print(f"\n**New email**")
                
                email_dict= self._assign_workflowid(email_dict)
                self.state.add_email(email_id, thread_id)
                self.events.put({
                    "type": {"new_email": email_dict}
                })
                
                wf = Workflow(self.model)
                
                self.processor.process(email_dict, wf, email_dict["workflow_id"], self.events)
                new_emails_count += 1
        
        if new_emails_count == 0:
            print("No new emails found. Waiting for next run!")
    
    def _handle_daily_reset(self) -> None:
        """Handle daily state reset if needed"""
        if self.state.should_reset_daily_state():
            print("New day detected. Resetting daily state...")
            self.state.reset_daily_state()
    
    def _assign_workflowid(self, email: Dict):
        wfid = str(uuid.uuid4())
        email["workflow_id"] = wfid
        return email
        
        
    
    def run(self) -> None: 
        """Main monitoring loop"""
        print("Starting email monitoring...")
        
        while True:
            try:
                # Search for today's emails
                search_results = self.searcher.search_today_emails()
                print(f"\nNumber of emails in search results: {len(search_results)}")
                
                # Handle first run
                if self.state.is_first_run:
                    self.state.handle_first_run(search_results, self.events)
                    time.sleep(self.first_run_delay)
                    continue
                
                # Handle daily reset
                self._handle_daily_reset()
                
                # Process new emails
                self._process_new_emails(search_results)
                
                # Wait before next check
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                print("\nMonitoring stopped by user.")
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(self.check_interval)