import time
import threading
import sys
import os
from datetime import datetime
from typing import Dict
from dataclasses import dataclass
from pathlib import Path

# Import unified path utilities
from path_utils import debug_paths, load_environment

def check_and_run_setup_gui():
    """
    Check if setup is complete and run GUI setup if needed.
    Returns True if setup is complete, False if user cancelled setup.
    """
    # Add debug information
    debug_paths()
    
    from setup import check_setup_status
    
    is_complete, missing_components = check_setup_status()
    
    if is_complete:
        print("✅ Setup is complete. Starting application...")
        return True
    
    print("\n" + "="*60)
    print("⚠️  SETUP REQUIRED")
    print("="*60)
    print("SmartEmailBot requires initial setup before it can run.")
    print(f"Missing components: {', '.join(missing_components)}")
    print("\nLaunching setup wizard...")
    
    # Import GUI setup here to avoid import issues
    from src.ui.startup_gui import SetupStartupGUI
    
    setup_complete = False
    
    def on_setup_complete():
        nonlocal setup_complete
        setup_complete = True
    
    try:
        # Run the setup GUI
        setup_gui = SetupStartupGUI(on_complete_callback=on_setup_complete)
        completed = setup_gui.run()
        
        if completed and setup_complete:
            # Re-check setup status after GUI setup
            is_complete, remaining_missing = check_setup_status()
            if is_complete:
                print("\n✅ Setup completed successfully! Starting application...")
                return True
            else:
                print(f"\n❌ Setup incomplete. Still missing: {', '.join(remaining_missing)}")
                return False
        else:
            print("\nSetup cancelled or incomplete.")
            return False
            
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        print("Please run setup.py manually to complete the setup.")
        return False

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
        self.communicator = None
        self.db_path = db_path
        
        # Configuration
        self.workflow_model = workflow_model
        self.check_interval = check_interval
        
        # Threading
        self.backend_thread = None
        self.is_setup = False
        self.running = False
        
        # Setup/Startup GUI
        self.startup_gui = None
        
        # Store initialized components
        self.gmail_tool = None

    def show_startup_progress(self):
        """Show startup progress using the GUI"""
        from src.ui.startup_gui import SetupStartupGUI
        
        def on_startup_complete():
            print("Startup GUI completed - ready to launch main app!")
            
        self.startup_gui = SetupStartupGUI(on_complete_callback=on_startup_complete)
 
        # Start initialization in separate thread during GUI startup
        self.backend_thread = threading.Thread(target=self.initialize_with_progress, daemon=True)
        self.backend_thread.start()
        
        # Run the startup GUI
        startup_completed = self.startup_gui.run()
        
        return startup_completed

    def initialize_with_progress(self):
        """Initialize all components with progress updates to the GUI"""
        try:
            # Check if we're in startup progress mode (not setup mode)
            if not hasattr(self.startup_gui, 'progress_var'):
                print("Setup mode detected - skipping progress updates")
                return
            
            # Update progress as components initialize
            steps = [
                ("Loading configuration...", self.load_config_step),
                ("Initializing Gmail API...", self.init_gmail_step),
                ("Checking OpenAI connection...", self.check_openai_step),
                ("Setting up database...", self.setup_database_step),
                ("Finalizing startup...", self.finalize_startup_step),
            ]
            
            for i, (status_text, func) in enumerate(steps):
                progress = (i / len(steps)) * 100
                if self.startup_gui:
                    self.startup_gui.root.after(0, lambda p=progress, s=status_text: 
                                              self.startup_gui.update_progress(p, s))
                
                # Execute step
                detail = func()
                if detail and self.startup_gui:
                    self.startup_gui.root.after(0, lambda d=detail: 
                                               self.startup_gui.update_detail(d))
                
                time.sleep(1)  # Visual feedback delay
            
            # Complete
            if self.startup_gui and hasattr(self.startup_gui, 'progress_var'):
                def safe_complete():
                    try:
                        self.startup_gui.update_progress(100, "✅ Startup complete!")
                        # Small delay then complete
                        self.startup_gui.root.after(1000, self.startup_gui.complete_startup)
                    except Exception:
                        # Widget already destroyed, just complete
                        self.startup_gui.complete_startup()
                
                self.startup_gui.root.after(0, safe_complete)
                
        except Exception as e:
            if self.startup_gui:
                self.startup_gui.root.after(0, lambda: 
                                           self.startup_gui.show_startup_error(str(e)))

    def load_config_step(self):
        """Load application configuration"""
        print("Loading configuration...")
        debug_paths()  
        
        from src.email_service import EmailService
        EmailService.load_from_file()
        
        # Import Communicator here after setup check
        from src.connect import Communicator
        self.communicator = Communicator()
        
        return "Configuration loaded successfully"
        
    def init_gmail_step(self):
        """Initialize Gmail API with health checks"""
        print("Initializing GmailToolkit and checking Gmail API...")
        
        # Initialize variables before the retry loop
        gmail_ok = False
        gmail_msg = "Gmail initialization not attempted"
        gmail_tool = None
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                from langchain_google_community import GmailToolkit
                gmail_tool = GmailToolkit()

                from helper import check_gmail_api
                gmail_ok, gmail_msg = check_gmail_api(gmail_tool)
                print(f"Attempt {attempt + 1}: {gmail_msg}")
                
                if gmail_ok:
                    break
                    
                if attempt < max_retries - 1:
                    print(f"Retrying Gmail connection in 1 seconds...")
                    time.sleep(1)
                else:
                    print("All Gmail connection attempts failed")
                    
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                gmail_ok = False
                gmail_msg = f"Exception during attempt {attempt + 1}: {str(e)}"
                print(f"Refreshing token...")
        
                from helper import refresh_gmail_token
                refresh_gmail_token()
                
                if attempt < max_retries - 1:
                    print(f"Retrying in 1 seconds...")
                    time.sleep(1)

        # Decide whether to continue
        if not gmail_ok:
            error_msg = f"Gmail API health check FAILED after all retries: {gmail_msg}"
            print(f"\n⚠️ {error_msg}")
            print("Possible solutions:")
            print("1. Run setup.py to re-authenticate with correct scopes")
            print("2. Check your internet connection")
            print("3. Verify credentials.json and token.json exist")
            print("4. Check if Gmail API is enabled in Google Cloud Console")
            raise RuntimeError(error_msg)
        
        # Store the gmail_tool for later use
        self.gmail_tool = gmail_tool
        return "Gmail API connection established"
        
    def check_openai_step(self):
        """Check OpenAI API connection"""
        print("Checking OpenAI access...")
        from helper import check_openai_api
        openai_ok, openai_msg = check_openai_api()
        print(openai_msg)
        
        if not openai_ok:
            error_msg = "OpenAI API health check FAILED. Please ensure OPENAI_API_KEY is set in your .env file."
            print(f"\n⚠️ {error_msg}")
            raise RuntimeError(error_msg)
            
        return "OpenAI API verified"
        
    def setup_database_step(self):
        """Setup database connections"""
        time.sleep(1.5)  # Simulate database setup
        return "Database connections established"
        
    def finalize_startup_step(self):
        """Finalize startup process"""
        print("✅ All health checks passed!")
        return "All systems ready"

    def start_backend(self):
        """Start the email monitoring backend (simplified - health checks already done)"""
        print("==Starting backend==")
        
        from src.backend import EmailManager
        
        self.backend = EmailManager(
            model=self.workflow_model,
            communicator=self.communicator,
            gmail_api=self.gmail_tool,
            check_interval=self.check_interval,
            db_path=self.db_path
        )
        
        if not self.backend:
            raise RuntimeError("Backend not initialized. Run initialization first.")
        
        # Start backend monitoring loop
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
            notification.startup(len(notify_emails), len(pending_emails))
        
        from src.ui.gui import EmailAgentGUI
        self.gui = EmailAgentGUI(communicator=self.communicator)
    
    def run(self):
        """Main application entry point (after initialization is complete)"""
        try:
            self.running = True
            
            # Start backend monitoring in separate thread
            self.backend_thread = threading.Thread(target=self.start_backend, daemon=True)
            self.backend_thread.start()
            time.sleep(2)  # Reduced sleep since initialization is already done
            print("\n===BACKEND STARTED===")
            
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
            self.backend_thread.join(timeout=10)
            
            if self.backend and hasattr(self.backend, 'workflow_manager'):
                self.backend.workflow_manager.save_workflows()
            
            EmailService.save_to_file()

            if self.backend_thread.is_alive():
                print("=== Backend thread did not stop gracefully ===")

def main():
    """Main function to start the connected application"""
    try:
        print("=== SMARTEMAILBOT STARTUP ===")
        
        # Load environment variables first
        print("Loading environment variables...")
        env_loaded = load_environment()
        
        # Show debug information
        debug_paths()
        
        if not env_loaded:
            print("⚠️  Environment not fully loaded, but continuing with setup check...")
        
        # Check setup before creating app
        if not check_and_run_setup_gui():
            print("Setup required but not completed. Exiting.")
            sys.exit(1)
        
        # Re-load environment after potential setup
        print("Re-loading environment after setup...")
        load_environment()
        
        # Create the application instance (no initialization yet)
        app = EmailApp(
            workflow_model="gpt-4o-mini",
            check_interval=120,
        )
        
        # Show startup progress and initialize all components
        print("===SHOWING STARTUP PROGRESS===")
        startup_completed = app.show_startup_progress()
        
        if not startup_completed:
            print("Startup cancelled or failed")
            sys.exit(1)
            
        print("===INITIALIZATION COMPLETED===\n")
        
        # Now run the application with pre-initialized components
        app.run()
        
    except Exception as e:
        print(f"Failed to start application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()