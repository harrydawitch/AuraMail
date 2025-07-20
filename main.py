import os
import time
import threading
import queue
from queue import Queue

from datetime import datetime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

from src.email import EmailMonitor
from src.ui.gui import EmailAgentGUI
from langchain_google_community import GmailToolkit

from customtkinter import *


@dataclass
class AppEvent:
    """Event structure for communication between backend and frontend"""
    event_type: str
    data: Dict
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class EmailApp:
    """Main application class that connects backend and frontend"""
    
    def __init__(self, workflow_model: str = "gpt-4o-mini", 
                 check_interval: int = 10, first_run_delay: int = 3):
        
        # Create communication queues
        self.events = Queue()  # Backend -> Frontend
        self.commands = Queue()  # Frontend -> Backend
        
        # Initialize components
        self.gmail = GmailToolkit()
        self.monitor = None
        self.gui = None
        
        # Configuration
        self.workflow_model = workflow_model
        self.check_interval = check_interval
        self.first_run_delay = first_run_delay
        
        # Threading
        self.monitor_thread = None
        self.event_processor_thread = None
        self.running = False
    
    def start_backend(self):
        """Start the email monitoring backend"""
        print("Starting email monitoring backend...")
        
        self.monitor = EmailMonitor(
            gmail_toolkit=self.gmail,
            workflow_model=self.workflow_model,
            events=self.events,
            commands=self.commands,
            check_interval=self.check_interval,
            first_run_delay=self.first_run_delay
        )
        
        # Start monitor in separate thread
        self.monitor_thread = threading.Thread(target=self.monitor.run, daemon=True)
        self.monitor_thread.start()

    def safe_gui_update(self, update_func, *args, **kwargs):
        """Safely update GUI from any thread"""
        if self.gui:
            try:
                self.gui.after(0, lambda: update_func(*args, **kwargs))
            except Exception as e:
                print(f"Error scheduling GUI update: {e}")

    def start_frontend(self):
        """Start the GUI frontend"""
        print("Starting GUI frontend...")
        
        self.gui = EmailAgentGUI(
            events=self.events,
            commands=self.commands
        )
        
        # Start event processor for GUI updates
        self.event_processor_thread = threading.Thread(
            target=self.process_events, daemon=True
        )
        self.event_processor_thread.start()
    
    def process_events(self):
        """Process events from backend to update frontend"""
        while self.running:
            try:
                # Check for events with timeout to allow graceful shutdown
                try:
                    event = self.events.get(timeout=1)
                    self.handle_event(event)
                    self.events.task_done()
                except queue.Empty:
                    continue
                    
            except Exception as e:
                print(f"Error processing event: {e}")
                time.sleep(1)
        
    
    def handle_event(self, event):
        """Handle specific events from backend"""
        if not self.gui:
            return
        
        try:
            event_type = event.get("type", {})
            
            if "new_email" in event_type:
                if event_type["new_email"]:
                    email_data = event_type["new_email"]
                    print(f"GUI: Received new email - {email_data["subject"]}")
                    
                    self.safe_gui_update(self.gui.add_email, email_data)

            
            if "decision" in event_type:
                decision_data = event_type["decision"]
                if decision_data and decision_data.get("category") == "notify":
                    category = decision_data.get("category")
                    email_id = decision_data.get("email_id")
                    summary = decision_data.get("summary")

                    print(f"GUI: Classify new email as: {category}")
                    
                    self.safe_gui_update(
                            self.gui.update_email_states, 
                            category=category, 
                            id=email_id, 
                            summary=summary
                        )
                
                elif decision_data and decision_data.get("category") == "ignore":
                    category = decision_data.get("category")
                    email_id = decision_data.get("email_id")
            
                    print(f"GUI: Classify new email as: {category}")

                    self.safe_gui_update(
                            self.gui.update_email_states, 
                            category=category, 
                            id=email_id, 

                        )
            
            
            if "ask_for_approval" in event_type:
                if event_type["ask_for_approval"] and event_type["ask_for_approval"].get("draft_response"):
                    
                    draft_response = event_type["ask_for_approval"].get("draft_response")
                    email_id = event_type["ask_for_approval"].get("email_id")
                    category = event_type["ask_for_approval"].get("category")

                    
                    print(f"GUI: Send draft response back to user:\n {draft_response}\n")

                    self.safe_gui_update(
                            self.gui.update_email_states, 
                            category=category, 
                            id=email_id, 
                            draft= draft_response
                        )
                    
            if "show_draft" in event_type:
                if event_type["show_draft"] and event_type["show_draft"].get("draft_response"):
                    
                    draft_response = event_type["show_draft"].get("draft_response")
                    email_id = event_type["show_draft"].get("email_id")
                    category = event_type["show_draft"].get("category")

                    
                    print(f"GUI: Show draft response to user:\n {draft_response}\n")

                    self.safe_gui_update(
                            self.gui.update_email_states, 
                            category=category, 
                            id=email_id, 
                            draft= draft_response
                        )
        except Exception as e:
            print(f"Error handling GUI event: {e}")

    
    
    def run(self):
        """Main application entry point"""
        try:
            self.running = True
            
            # Start backend
            self.start_backend()
            time.sleep(2)
            
            # Start frontend
            self.start_frontend()
            time.sleep(2)
            
            # Run GUI main loop (blocking)
            self.gui.mainloop()
            
            
        except KeyboardInterrupt:
            print("\nApplication stopped by user.")
        except Exception as e:
            print(f"Application error: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown"""
        print("Shutting down application...")
        self.running = False
        
        # Wait for threads to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        
        if self.event_processor_thread and self.event_processor_thread.is_alive():
            self.event_processor_thread.join(timeout=2)





def main():
    """Main function to start the connected application"""
    try:
        # Create and run the connected application
        app = EmailApp(
            workflow_model="gpt-4o-mini",
            check_interval=60,
            first_run_delay=1
        )
        
        app.run()
        
    except Exception as e:
        print(f"Failed to start application: {e}")


if __name__ == "__main__":
    main()
    
    
