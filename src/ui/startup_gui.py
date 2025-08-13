import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
import threading
import time
import os
import sys
import webbrowser
from pathlib import Path
from typing import Optional, Callable
import json
import shutil

import sys
from pathlib import Path

# Add the project's root directory to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Import setup functions
from setup import (
    check_setup_status, 
    copy_credentials_file, 
    ensure_token, 
    update_env_file,
    GCP_CREDENTIALS_URL,
    APP_DIR,
    CREDENTIALS_PATH,
    TOKEN_PATH,
    ENV_PATH
)

class SetupStartupGUI:
    """
    A GUI that handles both initial setup and startup progress.
    Shows setup screens if not configured, otherwise shows startup progress.
    """
    
    def __init__(self, on_complete_callback: Optional[Callable] = None):
        self.on_complete_callback = on_complete_callback
        self.setup_complete = False
        self.startup_complete = False
        self.current_step = 0
        self.total_steps = 6
        
        # Setup the main window
        self.setup_window()
        self.check_initial_status()
        
    def setup_window(self):
        """Initialize the main window"""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.title("SmartEmailBot Setup")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        # Center the window
        self.center_window()
        
        # Main container
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.root.winfo_screenheight() // 2) - (500 // 2)
        self.root.geometry(f"600x500+{x}+{y}")
        
    def check_initial_status(self):
        """Check if setup is needed or if we can go straight to startup"""
        is_complete, missing_components = check_setup_status()
        
        if is_complete:
            self.show_startup_progress()
        else:
            self.show_setup_welcome(missing_components)
            
    def show_setup_welcome(self, missing_components):
        """Show the welcome screen for setup"""
        self.clear_frame()
        
        # Title
        title = ctk.CTkLabel(
            self.main_frame, 
            text="🤖 SmartEmailBot Setup", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=20)
        
        # Welcome message
        welcome_text = """
Welcome to SmartEmailBot! 

This intelligent email assistant will help you manage your Gmail inbox with AI-powered classification, summarization, and response generation.

Before we start, we need to set up a few things:
        """
        
        welcome_label = ctk.CTkLabel(
            self.main_frame,
            text=welcome_text,
            font=ctk.CTkFont(size=14),
            wraplength=500
        )
        welcome_label.pack(pady=10)
        
        # Missing components
        missing_text = f"Missing components: {', '.join(missing_components)}"
        missing_label = ctk.CTkLabel(
            self.main_frame,
            text=missing_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="orange"
        )
        missing_label.pack(pady=5)
        
        # Setup steps
        steps_text = """
Setup will configure:
• Gmail API credentials (credentials.json)
• OAuth authentication (token.json) 
• OpenAI API key and email settings (.env)
• Application launcher files
        """
        
        steps_label = ctk.CTkLabel(
            self.main_frame,
            text=steps_text,
            font=ctk.CTkFont(size=12),
            justify="left"
        )
        steps_label.pack(pady=10)
        
        # Buttons
        button_frame = ctk.CTkFrame(self.main_frame)
        button_frame.pack(pady=20, fill="x")
        
        start_button = ctk.CTkButton(
            button_frame,
            text="🚀 Start Setup",
            command=self.start_setup_flow,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=40
        )
        start_button.pack(side="left", padx=10, expand=True, fill="x")
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="❌ Cancel",
            command=self.cancel_setup,
            fg_color="gray",
            hover_color="dark gray",
            height=40
        )
        cancel_button.pack(side="right", padx=10)
        
    def start_setup_flow(self):
        """Start the setup flow"""
        self.current_setup_step = 1
        self.show_gmail_setup()
        
    def show_gmail_setup(self):
        """Show Gmail API setup screen"""
        self.clear_frame()
        
        # Progress indicator
        progress_text = f"Step 1 of 3: Gmail API Setup"
        progress_label = ctk.CTkLabel(
            self.main_frame,
            text=progress_text,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        progress_label.pack(pady=10)
        
        # Title
        title = ctk.CTkLabel(
            self.main_frame,
            text="🔑 Gmail API Credentials",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=10)
        
        # Instructions
        instructions = """
To access Gmail, SmartEmailBot needs API credentials from Google Cloud Console.

If you don't have credentials.json yet:
1. Click 'Open Google Cloud Console' below
2. Create OAuth credentials (Desktop Application)
3. Download the credentials.json file
4. Return here and select the file
        """
        
        instructions_label = ctk.CTkLabel(
            self.main_frame,
            text=instructions,
            font=ctk.CTkFont(size=12),
            wraplength=500,
            justify="left"
        )
        instructions_label.pack(pady=10)
        
        # Check if credentials already exist
        if CREDENTIALS_PATH.exists():
            status_label = ctk.CTkLabel(
                self.main_frame,
                text="✅ credentials.json found!",
                text_color="green",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            status_label.pack(pady=5)
            
            next_button = ctk.CTkButton(
                self.main_frame,
                text="Next: OAuth Setup →",
                command=self.show_oauth_setup,
                font=ctk.CTkFont(size=14, weight="bold")
            )
            next_button.pack(pady=20)
        else:
            # Buttons for credential setup
            button_frame = ctk.CTkFrame(self.main_frame)
            button_frame.pack(pady=20, fill="x")
            
            cloud_button = ctk.CTkButton(
                button_frame,
                text="🌐 Open Google Cloud Console",
                command=self.open_cloud_console,
                height=40
            )
            cloud_button.pack(pady=5, fill="x")
            
            file_button = ctk.CTkButton(
                button_frame,
                text="📁 Select credentials.json",
                command=self.select_credentials_file,
                height=40,
                fg_color="green",
                hover_color="dark green"
            )
            file_button.pack(pady=5, fill="x")
            
        # Back button
        back_button = ctk.CTkButton(
            self.main_frame,
            text="← Back",
            command=lambda: self.check_initial_status(),
            fg_color="gray",
            hover_color="dark gray",
            width=100
        )
        back_button.pack(side="bottom", pady=10)
        
    def open_cloud_console(self):
        """Open Google Cloud Console for credential setup"""
        try:
            webbrowser.open(GCP_CREDENTIALS_URL)
            messagebox.showinfo(
                "Browser Opened", 
                "Google Cloud Console opened in your browser.\n\n"
                "Create OAuth credentials (Desktop Application) and download the JSON file.\n\n"
                "Then return here and click 'Select credentials.json'"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Could not open browser: {e}")
            
    def select_credentials_file(self):
        """Allow user to select credentials.json file"""
        file_path = filedialog.askopenfilename(
            title="Select credentials.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=os.path.expanduser("~/Downloads")
        )
        
        if file_path:
            try:
                copy_credentials_file(Path(file_path))
                messagebox.showinfo("Success", "credentials.json copied successfully!")
                self.show_oauth_setup()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to copy credentials file: {e}")
                
    def show_oauth_setup(self):
        """Show OAuth authorization screen"""
        self.clear_frame()
        
        # Progress indicator
        progress_text = f"Step 2 of 3: OAuth Authorization"
        progress_label = ctk.CTkLabel(
            self.main_frame,
            text=progress_text,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        progress_label.pack(pady=10)
        
        # Title
        title = ctk.CTkLabel(
            self.main_frame,
            text="🔐 Gmail Authorization",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=10)
        
        # Instructions
        instructions = """
Now we need to authorize SmartEmailBot to access your Gmail account.

When you click 'Start Authorization':
1. Your browser will open with Google's sign-in page
2. Sign in to your Gmail account
3. Grant permissions for SmartEmailBot to read and send emails
4. The authorization will complete automatically

This is secure and uses Google's OAuth 2.0 standard.
        """
        
        instructions_label = ctk.CTkLabel(
            self.main_frame,
            text=instructions,
            font=ctk.CTkFont(size=12),
            wraplength=500,
            justify="left"
        )
        instructions_label.pack(pady=10)
        
        # Check if token already exists
        if TOKEN_PATH.exists():
            status_label = ctk.CTkLabel(
                self.main_frame,
                text="✅ OAuth token found! Authorization complete.",
                text_color="green",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            status_label.pack(pady=5)
            
            next_button = ctk.CTkButton(
                self.main_frame,
                text="Next: API Configuration →",
                command=self.show_api_setup,
                font=ctk.CTkFont(size=14, weight="bold")
            )
            next_button.pack(pady=20)
        else:
            # Authorization button
            auth_button = ctk.CTkButton(
                self.main_frame,
                text="🚀 Start Authorization",
                command=self.start_oauth_flow,
                font=ctk.CTkFont(size=16, weight="bold"),
                height=50,
                fg_color="blue",
                hover_color="dark blue"
            )
            auth_button.pack(pady=20)
            
        # Back button
        back_button = ctk.CTkButton(
            self.main_frame,
            text="← Back",
            command=self.show_gmail_setup,
            fg_color="gray",
            hover_color="dark gray",
            width=100
        )
        back_button.pack(side="bottom", pady=10)
        
    def start_oauth_flow(self):
        """Start OAuth flow in a separate thread"""
        def oauth_thread():
            try:
                # Show loading state
                self.root.after(0, self.show_oauth_loading)
                
                # Run OAuth flow
                creds = ensure_token()
                
                if creds and creds.valid:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Success", 
                        "OAuth authorization completed successfully!"
                    ))
                    self.root.after(0, self.show_api_setup)
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error",
                        "OAuth authorization failed. Please try again."
                    ))
                    self.root.after(0, self.show_oauth_setup)
                    
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Error",
                    f"OAuth authorization failed: {e}"
                ))
                self.root.after(0, self.show_oauth_setup)
                
        threading.Thread(target=oauth_thread, daemon=True).start()
        
    def show_oauth_loading(self):
        """Show loading screen during OAuth"""
        self.clear_frame()
        
        title = ctk.CTkLabel(
            self.main_frame,
            text="🔄 Authorizing...",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=50)
        
        loading_label = ctk.CTkLabel(
            self.main_frame,
            text="Please complete authorization in your browser.\nThis window will update when complete.",
            font=ctk.CTkFont(size=14),
            justify="center"
        )
        loading_label.pack(pady=20)
        
        # Loading spinner
        spinner = ctk.CTkProgressBar(self.main_frame, mode="indeterminate")
        spinner.pack(pady=20, padx=50, fill="x")
        spinner.start()
        
    def show_api_setup(self):
        """Show API keys and email configuration"""
        self.clear_frame()
        
        # Progress indicator
        progress_text = f"Step 3 of 3: API Configuration"
        progress_label = ctk.CTkLabel(
            self.main_frame,
            text=progress_text,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        progress_label.pack(pady=10)
        
        # Title
        title = ctk.CTkLabel(
            self.main_frame,
            text="🔑 API Configuration",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=10)
        
        # Instructions
        instructions = ctk.CTkLabel(
            self.main_frame,
            text="Enter your OpenAI API key and email information:",
            font=ctk.CTkFont(size=14)
        )
        instructions.pack(pady=10)
        
        # Input fields container (with scrollable frame if needed)
        input_container = ctk.CTkScrollableFrame(self.main_frame)
        input_container.pack(pady=10, padx=20, fill="both", expand=True)
        
        # OpenAI API Key
        api_key_label = ctk.CTkLabel(
            input_container, 
            text="OpenAI API Key:", 
            font=ctk.CTkFont(weight="bold")
        )
        api_key_label.pack(pady=(10, 5), anchor="w")
        
        self.api_key_entry = ctk.CTkEntry(
            input_container,
            placeholder_text="sk-...",
            show="*",
            font=ctk.CTkFont(size=12),
            height=35
        )
        self.api_key_entry.pack(pady=(0, 10), fill="x")
        
        # Email
        email_label = ctk.CTkLabel(
            input_container, 
            text="Your Email:", 
            font=ctk.CTkFont(weight="bold")
        )
        email_label.pack(pady=(5, 5), anchor="w")
        
        self.email_entry = ctk.CTkEntry(
            input_container,
            placeholder_text="your-email@gmail.com",
            font=ctk.CTkFont(size=12),
            height=35
        )
        self.email_entry.pack(pady=(0, 10), fill="x")
        
        # Username
        username_label = ctk.CTkLabel(
            input_container, 
            text="Your Name:", 
            font=ctk.CTkFont(weight="bold")
        )
        username_label.pack(pady=(5, 5), anchor="w")
        
        self.username_entry = ctk.CTkEntry(
            input_container,
            placeholder_text="Your Name",
            font=ctk.CTkFont(size=12),
            height=35
        )
        self.username_entry.pack(pady=(0, 20), fill="x")
        
        # Buttons frame - Fixed positioning at bottom
        button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        button_frame.pack(side="bottom", pady=10, padx=20, fill="x")
        
        # Complete setup button
        complete_button = ctk.CTkButton(
            button_frame,
            text="✅ Complete Setup",
            command=self.complete_setup,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45,
            fg_color="green",
            hover_color="dark green"
        )
        complete_button.pack(pady=(0, 5), fill="x")
        
        # Back button
        back_button = ctk.CTkButton(
            button_frame,
            text="← Back",
            command=self.show_oauth_setup,
            fg_color="gray",
            hover_color="dark gray",
            height=35
        )
        back_button.pack(pady=(5, 0), fill="x")
        
    def complete_setup(self):
        """Complete the setup process"""
        # Validate inputs
        api_key = self.api_key_entry.get().strip()
        email = self.email_entry.get().strip()
        username = self.username_entry.get().strip()
        
        if not api_key:
            messagebox.showerror("Error", "Please enter your OpenAI API key")
            return
            
        if not email:
            messagebox.showerror("Error", "Please enter your email address")
            return
            
        if not username:
            messagebox.showerror("Error", "Please enter your name")
            return
            
        try:
            # Update .env file
            update_env_file(api_key, email, username)
            
            # Check final setup status
            is_complete, missing = check_setup_status()
            
            if is_complete:
                messagebox.showinfo(
                    "Setup Complete!",
                    "SmartEmailBot has been set up successfully!\n\n"
                    "The application will now start."
                )
                self.setup_complete = True
                self.show_startup_progress()
            else:
                messagebox.showerror(
                    "Setup Incomplete",
                    f"Setup is still missing: {', '.join(missing)}\n\n"
                    "Please check the setup steps."
                )
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to complete setup: {e}")
            
    def show_startup_progress(self):
        """Show startup progress screen"""
        self.clear_frame()
        
        # Title
        title = ctk.CTkLabel(
            self.main_frame,
            text="🚀 Starting SmartEmailBot",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=30)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ctk.CTkProgressBar(
            self.main_frame,
            variable=self.progress_var,
            width=400,
            height=20
        )
        self.progress_bar.pack(pady=20)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="Initializing...",
            font=ctk.CTkFont(size=14)
        )
        self.status_label.pack(pady=10)
        
        # Detailed status
        self.detail_label = ctk.CTkLabel(
            self.main_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.detail_label.pack(pady=5)
        
        # Start the startup process
        self.start_startup_process()
        
    def start_startup_process(self):
        """Start the backend startup process"""
        def startup_thread():
            try:
                steps = [
                    ("Loading configuration...", self.load_config),
                    ("Initializing Gmail API...", self.init_gmail),
                    ("Checking OpenAI connection...", self.check_openai),
                    ("Setting up database...", self.setup_database),
                    ("Starting backend services...", self.start_backend_services),
                    ("Finalizing startup...", self.finalize_startup)
                ]
                
                for i, (status_text, func) in enumerate(steps):
                    progress = (i / len(steps)) * 100
                    self.root.after(0, lambda p=progress, s=status_text: self.update_progress(p, s))
                    
                    # Execute step
                    detail = func()
                    if detail:
                        self.root.after(0, lambda d=detail: self.update_detail(d))
                    
                    time.sleep(0.5)  # Small delay for visual feedback
                
                # Complete
                self.root.after(0, lambda: self.update_progress(100, "✅ Startup complete!"))
                time.sleep(1)
                self.root.after(0, self.complete_startup)
                
            except Exception as e:
                self.root.after(0, lambda: self.show_startup_error(str(e)))
                
        threading.Thread(target=startup_thread, daemon=True).start()
        
    def load_config(self):
        """Load application configuration"""
        time.sleep(1)  # Simulate work
        return "Configuration loaded successfully"
        
    def init_gmail(self):
        """Initialize Gmail API"""
        time.sleep(2)  # Simulate Gmail API initialization
        return "Gmail API connection established"
        
    def check_openai(self):
        """Check OpenAI API connection"""
        time.sleep(1)  # Simulate OpenAI check
        return "OpenAI API verified"
        
    def setup_database(self):
        """Setup database connections"""
        time.sleep(1)  # Simulate database setup
        return "Database connections established"
        
    def start_backend_services(self):
        """Start backend services"""
        time.sleep(2)  # Simulate backend startup
        return "Email monitoring service started"
        
    def finalize_startup(self):
        """Finalize startup process"""
        time.sleep(1)  # Simulate finalization
        return "All systems ready"
        
    def update_progress(self, progress, status):
        """Update progress bar and status"""
        self.progress_var.set(progress / 100)
        self.status_label.configure(text=status)
        
    def update_detail(self, detail):
        """Update detailed status"""
        self.detail_label.configure(text=detail)
        
    def show_startup_error(self, error_msg):
        """Show startup error"""
        self.clear_frame()
        
        title = ctk.CTkLabel(
            self.main_frame,
            text="❌ Startup Failed",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="red"
        )
        title.pack(pady=30)
        
        error_label = ctk.CTkLabel(
            self.main_frame,
            text=f"Error: {error_msg}",
            font=ctk.CTkFont(size=12),
            text_color="red",
            wraplength=500
        )
        error_label.pack(pady=20)
        
        retry_button = ctk.CTkButton(
            self.main_frame,
            text="🔄 Retry",
            command=self.show_startup_progress
        )
        retry_button.pack(pady=10)
        
        exit_button = ctk.CTkButton(
            self.main_frame,
            text="❌ Exit",
            command=self.root.quit,
            fg_color="gray",
            hover_color="dark gray"
        )
        exit_button.pack(pady=5)
        
    def complete_startup(self):
        """Complete the startup process and close window"""
        self.startup_complete = True
        
        # Show completion message briefly
        self.clear_frame()
        
        success_label = ctk.CTkLabel(
            self.main_frame,
            text="🎉 SmartEmailBot Ready!",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="green"
        )
        success_label.pack(expand=True)
        
        # Auto-close after 2 seconds
        self.root.after(2000, self.close_window)
        
    def close_window(self):
        """Close the setup window and trigger callback"""
        self.root.withdraw()
        if self.on_complete_callback:
            self.on_complete_callback()
        self.root.quit()
        
    def cancel_setup(self):
        """Cancel setup process"""
        if messagebox.askyesno("Cancel Setup", "Are you sure you want to cancel setup?\n\nSmartEmailBot requires setup to function properly."):
            self.root.quit()
            sys.exit(0)
            
    def clear_frame(self):
        """Clear all widgets from main frame"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
    def run(self):
        """Run the setup/startup GUI"""
        self.root.protocol("WM_DELETE_WINDOW", self.cancel_setup)
        self.root.mainloop()
        return self.startup_complete


# Example usage
if __name__ == "__main__":
    def on_complete():
        print("Setup/Startup completed - ready to launch main app!")
        
    setup_gui = SetupStartupGUI(on_complete_callback=on_complete)
    setup_gui.run()
    
