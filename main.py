import time
import threading
from datetime import datetime
from typing import Dict
from dataclasses import dataclass
from langchain_google_community import GmailToolkit

from src.backend import EmailManager
from src.ui.gui import EmailAgentGUI
from src.connect import Communicator


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
    
    def __init__(
                 self, 
                 workflow_model: str = "gpt-4o-mini", 
                 db_path: str = "db/checkpoints.sqlite" ,
                 check_interval: int = 10,
                 ):
        
        
        # Initialize components
        self.backend = None
        self.gui = None
        self.communicator = Communicator()
        self.db_path = db_path
        
        # Configuration
        self.workflow_model = workflow_model
        self.check_interval = check_interval
        
        # Threading
        self.backend_thread = None
        self.running = False
        


    def start_backend(self):
        """Start the email monitoring backend"""
        print("Starting backend...")
        
        from src.email_service import EmailService
        EmailService.load_from_file()
        
        self.backend = EmailManager(
            model= self.workflow_model,
            communicator= self.communicator,
            gmail_api= GmailToolkit(),
            check_interval= self.check_interval,
            db_path= self.db_path
        )
        
        # Start poll emails in separate thread and run backend
        self.backend.run()

    def start_frontend(self):
        """Start the GUI frontend"""
        
        print("Starting GUI frontend...")
        from src.email_service import EmailService
        from src.utils import Notification
        
        notification = Notification()
        
        notify_emails = EmailService.load_emails_by_category("notify")
        pending_emails = EmailService.load_emails_by_category("human")
                
        if notify_emails or pending_emails:
            notification.startup(len(notify_emails), (pending_emails))
        
        self.gui = EmailAgentGUI(
            communicator= self.communicator
        )
    
    def run(self):
        """Main application entry point"""
        try:
            self.running = True
            
            # Start backend in separate thread
            self.backend_thread = threading.Thread(target=self.start_backend, daemon=True)
            self.backend_thread.start()
            print("===BACKEND STARTED===")
            time.sleep(1)
            
            # Start frontend
            self.start_frontend()
            print("===FRONTEND STARTED===")
            time.sleep(0.5)
            
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
            from src.email_service import EmailService
            print("Shutting down application...")
            self.running = False
            
            # Shutdown GUI first (including tray icon)
            if self.gui:
                try:
                    self.gui.shutdown()
                except Exception as e:
                    print(f"Error shutting down GUI: {e}")
            
            # Record shutdown in backend if it exists
            if self.backend:
                self.backend.shutdown()
            
            # Wait for backend thread to finish
            if self.backend_thread and self.backend_thread.is_alive():
                print("Waiting for backend thread to finish...")
                self.backend_thread.join(timeout=5)
                
                if self.backend and hasattr(self.backend, 'workflow_manager'):
                    self.backend.workflow_manager.save_workflows()
                
                EmailService.save_to_file()

                if self.backend_thread.is_alive():
                    print("=== Backend thread did not stop gracefully ===")




def main():
    """Main function to start the connected application"""
    try:
        # Create and run the connected application
        app = EmailApp(
            workflow_model="gpt-4o-mini",
            check_interval=30,
        )
        
        app.run()
        
    except Exception as e:
        print(f"Failed to start application: {e}")


if __name__ == "__main__":
    main()
    
    
