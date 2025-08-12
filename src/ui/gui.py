from pathlib import Path
from typing import Dict, List, Callable
from tkinter import END, messagebox

from customtkinter import *
from CTkListbox import *

import pystray
from PIL import Image, ImageDraw
import threading

from src.connect import FrontendCommunicator, Communicator
from src.email_service import EmailData, EmailService

class SystemTrayManager:
    """Manages system tray icon and window hiding/showing"""
    
    def __init__(self, gui_app):
        self.gui_app = gui_app
        self.icon = None
        self.is_hidden = False
        
    def create_tray_icon(self):
        """Create a simple tray icon"""
        # Create a simple icon (you can replace this with an actual icon file)
        image = Image.new('RGB', (64, 64), color='#359B0C')  # Use your app's green color
        draw = ImageDraw.Draw(image)
        draw.rectangle([8, 8, 56, 56], fill='white')
        draw.text((18, 22), "AM", fill='#359B0C')  # AuraMail
        
        # Alternative: Load from file if you have an icon
        # try:
        #     icon_path = ASSETS_PATH / "auramail_icon.png"
        #     if icon_path.exists():
        #         image = Image.open(str(icon_path))
        # except Exception as e:
        #     print(f"Could not load icon file: {e}")
        #     # Keep using generated icon
        
        # Create menu
        menu = pystray.Menu(
            pystray.MenuItem("Show AuraMail", self.show_window, default=True),
            pystray.MenuItem("Hide AuraMail", self.hide_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.quit_application)
        )
        
        # Create icon
        self.icon = pystray.Icon(
            "AuraMail",
            image,
            "AuraMail - Email Agent",
            menu
        )
        
        return self.icon
    
    def show_window(self, icon=None, item=None):
        """Show the main window"""
        if self.gui_app:
            self.gui_app.after(0, self._show_window_safe)
    
    def _show_window_safe(self):
        """Thread-safe window showing"""
        try:
            self.gui_app.deiconify() 
            self.gui_app.lift()      
            self.gui_app.focus_force()
            self.is_hidden = False
        except Exception as e:
            print(f"Error showing window: {e}")
    
    def hide_window(self, icon=None, item=None):
        """Hide the main window"""
        if self.gui_app:
            self.gui_app.after(0, self._hide_window_safe)
    
    def _hide_window_safe(self):
        """Thread-safe window hiding"""
        try:
            self.gui_app.withdraw()  # Hide window
            self.is_hidden = True
        except Exception as e:
            print(f"Error hiding window: {e}")
    
    def quit_application(self, icon=None, item=None):
        """Completely quit the application"""
        if self.gui_app:
            self.gui_app.after(0, self._quit_application_safe)
    
    def _quit_application_safe(self):
        """Thread-safe application quitting"""
        try:
            # Show confirmation dialog
            result = messagebox.askyesno(
                "Confirm Exit", 
                "Are you sure you want to exit AuraMail?\nThis will stop email monitoring.",
                parent=self.gui_app
            )
            
            if result:
                self.stop_tray_icon()
                # Call the app's shutdown method
                if hasattr(self.gui_app, 'shutdown'):
                    self.gui_app.shutdown()
                self.gui_app.quit()
                self.gui_app.destroy()
        except Exception as e:
            print(f"Error quitting application: {e}")
    
    def start_tray_icon(self):
        """Start the system tray icon in a separate thread"""
        if not self.icon:
            self.create_tray_icon()
        
        # Run in separate thread to avoid blocking GUI
        tray_thread = threading.Thread(target=self.icon.run, daemon=True)
        tray_thread.start()
    
    def stop_tray_icon(self):
        """Stop the system tray icon"""
        if self.icon:
            self.icon.stop()

# Constants
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path("ui/assets")

# UI Configuration
class UIConfig:
    WINDOW_SIZE = "1270x720"
    TITLE = "AuraMail"
    APPEARANCE_MODE = "dark"
    
    # Colors
    TASKBAR_COLOR = "#1B1A1A"
    BUTTON_COLOR = "#232431"
    BUTTON_HOVER = "#AF3030"
    BUTTON_ACTIVE = "#D10000"
    ROW_COLOR = "#333333"
    ROW_HOVER = "#444a54"
    CONTENT_BG = "#222"
    ACTION_BUTTON_COLOR = "#359B0C"
    ACTION_BUTTON_HOVER = "#3D8F20"
    REJECT_BUTTON_COLOR = "#8B0000"
    REJECT_BUTTON_HOVER = "#A52A2A"
    GENERATE_DRAFT_BUTTON_COLOR = "#1568F8"
    GENERATE_DRAFT_BUTTON_HOVER = "#0041B3"
    
    # Fonts
    BUTTON_FONT = ("Noto Sans", 18, "bold")
    SUBJECT_FONT = ("Helvetica", 20, "bold")
    SENDER_FONT = ("Helvetica", 14)
    EMAIL_FONT = ("Helvetica", 13)
    TIME_FONT = ("Helvetica", 12)
    BODY_FONT = ("Helvetica", 13)
    ACTION_BUTTON_FONT = ("Helvetica", 12, "bold")


class ContextDialog(CTkToplevel):
    """Dialog for getting user context input"""
    def __init__(self, parent, title: str, prompt: str, callback: Callable):
        super().__init__(parent)
        self.callback = callback
        self.result = None
        
        self.title(title)
        self.transient(parent)
        self.grab_set()
        
        # Set minimum size to prevent too small windows
        self.minsize(600, 300)
        
        # Create widgets first
        self._create_widgets(prompt)
        
        # Set size and center after widgets are created
        self.geometry("600x300")
        self.after_idle(self._center_dialog)
    
    def _create_widgets(self, prompt: str):
        """Create dialog widgets"""
        # Main frame
        main_frame = CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Prompt label
        prompt_label = CTkLabel(main_frame, text=prompt, font=UIConfig.SENDER_FONT, wraplength=450)
        prompt_label.pack(pady=(0, 15))
        
        # Text input
        self.text_input = CTkTextbox(main_frame, height=150, font=UIConfig.BODY_FONT)
        self.text_input.pack(fill="both", expand=True, pady=(0, 15))
        
        # Button frame
        button_frame = CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")
        
        # Cancel button
        cancel_btn = CTkButton(
            button_frame,
            text="Cancel",
            command=self._cancel,
            fg_color=UIConfig.REJECT_BUTTON_COLOR,
            hover_color=UIConfig.REJECT_BUTTON_HOVER
        )
        cancel_btn.pack(side="right", padx=(10, 80))
        
        # Submit button
        submit_btn = CTkButton(
            button_frame,
            text="Submit",
            command=self._submit,
            fg_color=UIConfig.ACTION_BUTTON_COLOR,
            hover_color=UIConfig.ACTION_BUTTON_HOVER
        )
        submit_btn.pack(side="right")
        
        # Focus on text input
        self.text_input.focus()

    def _center_dialog(self):
        """Center the dialog on screen"""
        self.update_idletasks()
        # Use the intended size (1200x800) for centering
        width = 600
        height = 400
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _submit(self):
        """Handle submit with improved error handling"""
        try:
            context = self.text_input.get("1.0", END).strip()
            if context:
                self.result = context
                self.destroy()
                # Run callback in separate thread
                threading.Thread(
                    target=self._run_callback,
                    args=(context,),
                    daemon=True
                ).start()
            else:
                messagebox.showwarning("Warning", "Please enter some context.")
        except Exception as e:
            print(f"Error in dialog submit: {e}")
            self.destroy()

    def _run_callback(self, context):
        """Run callback in separate thread"""
        self.callback(context)

    def _cancel(self):
        """Handle cancel button"""
        self.destroy()

class EmailGrid:
    """Manages the email list grid view"""
    def __init__(self, parent: CTkFrame, on_email_select: Callable):
        self.parent = parent
        self.on_email_select = on_email_select
        self.grid_frame = None
        self.email_rows = []
        self.current_view_type = "normal"
        self._destroyed = False
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the grid frame with a wrapper box"""
        # Create a wrapper frame with padding for the box effect
        self.wrapper_frame = CTkFrame(self.parent, fg_color="#1F1F24")
        self.wrapper_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Create the actual grid frame inside the wrapper (this creates the box effect)
        self.grid_frame = CTkFrame(self.wrapper_frame, fg_color="#1e2124", corner_radius=10)
        self.grid_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configure grid columns
        self.grid_frame.grid_columnconfigure(0, weight=1)
        self.grid_frame.grid_columnconfigure(1, weight=0, minsize=110)
        self.grid_frame.grid_columnconfigure(2, weight=0, minsize=200)
    
    def update_emails(self, emails: List[EmailData], view_type: str = "normal"):
        """Update the grid with new emails"""
        
        try:
            self._clear_grid()
            self.email_rows = []
            self.current_view_type = view_type
            
            # Add small delay to ensure proper cleanup
            if hasattr(self.parent, 'after'):
                self.parent.after(10, lambda: self._create_rows_delayed(emails, view_type))
            else:
                self._create_rows_delayed(emails, view_type)
                
        except Exception as e:
            print(f"Error in update_emails: {e}")

    # Add this new method to EmailGrid:
    def _create_rows_delayed(self, emails, view_type):
        """Create email rows with delay"""
        
        for idx, email in enumerate(emails):
            try:
                row = EmailRow(self.grid_frame, email, idx, self.on_email_select, view_type)
                self.email_rows.append(row)
            except Exception as e:
                print(f"Error creating email row {idx}: {e}")
                continue
     
    def _clear_grid(self):
        """Safely clear all widgets from the grid"""
        if getattr(self, '_destroyed', False) or not self.grid_frame:
            return
            
        try:
            # Get all children before starting destruction
            children = list(self.grid_frame.winfo_children())
            
            # Destroy children one by one with error handling
            for widget in children:
                try:
                    if widget.winfo_exists():
                        widget.destroy()
                except Exception as e:
                    # Widget might already be destroyed
                    pass
                    
            self.email_rows.clear()
            
        except Exception as e:
            print(f"Error clearing grid: {e}")
    
    def show(self):
        """Show the grid"""
        self.wrapper_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    def hide(self):
        """Hide the grid"""
        self.wrapper_frame.pack_forget()


class TaskbarButton:
    """Represents a single taskbar button"""
    def __init__(self, parent: CTkFrame, text: str, command: Callable, row: int, column: int):
        self.parent = parent
        self.text = text
        self.command = command
        self.is_active = False
        
        self.button = CTkButton(
            parent,
            text=text,
            font=UIConfig.BUTTON_FONT,
            command=command,
            fg_color=UIConfig.BUTTON_COLOR,
            bg_color=UIConfig.BUTTON_COLOR,
            hover_color=UIConfig.BUTTON_HOVER,
            corner_radius=0,
            height=40
        )
        self.button.grid(row=row, column=column, sticky="ew", padx=1, pady=1)
    
    def set_active(self, active: bool):
        """Set the button's active state"""
        self.is_active = active
        color = UIConfig.BUTTON_ACTIVE if active else UIConfig.BUTTON_COLOR
        self.button.configure(fg_color=color)

class Taskbar:
    """Manages the application taskbar"""
    def __init__(self, parent: CTk, callbacks: Dict[str, Callable]):
        self.parent = parent
        self.callbacks = callbacks
        self.taskbar_frame = None
        self.buttons = {}
        self.refresh_btn = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the taskbar widgets"""
        # Main taskbar frame
        self.taskbar_frame = CTkFrame(self.parent, height=500, fg_color=UIConfig.TASKBAR_COLOR)
        self.taskbar_frame.pack(side="top", fill="x")
        
        # Configure grid columns for equal spacing (4 columns for main buttons)
        for i in range(5):
            self.taskbar_frame.grid_columnconfigure(i, weight=1)
        
        # Create buttons
        button_configs = [
            ("home", "Home", 0),
            ("notify", "Notify", 1),
            ("ignore", "Ignore", 2),
            ("human", "Pending", 3),
            ("send", "Send Email", 4)
        ]
        
        for key, text, column in button_configs:
            self.buttons[key] = TaskbarButton(
                self.taskbar_frame,
                text,
                lambda k=key: self.callbacks[k](),
                0,
                column
            )
    
    def set_active_button(self, active_key: str):
        """Set which button is active"""
        for key, button in self.buttons.items():
            button.set_active(key == active_key)

class EmailDetailView:
    """Manages the detailed email view"""
    def __init__(self, parent: CTkFrame, on_back: Callable):
        self.parent = parent
        self.on_back = on_back
        
        self.content_frame = None
        self.header_frame = None
        self.back_btn = None
        
        self.subject_label = None
        self.sender_label = None
        
        self.summary_label = None
        self.content_label = None
        self.draft_label = None
        
        self.body_content = None
        self.summary_text = None
        self.body_text = None
        self.draft_text = None

        self.action_frame = None
        self.current_email = None
        self.current_category = None
        self.action_callback = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the detail view widgets"""
        # Main content frame
        self.content_frame = CTkFrame(self.parent, fg_color=UIConfig.CONTENT_BG)
        
        # Header frame
        self.header_frame = CTkFrame(self.content_frame, fg_color=UIConfig.CONTENT_BG)
        self.header_frame.pack(fill="x", padx=30, pady=(30, 0))
        
        # Back button
        self.back_btn = CTkButton(
            self.header_frame, 
            text="← Back", 
            width=80, 
            command=self.on_back,
            fg_color="#282b30"
        )
        self.back_btn.pack(anchor="w", padx=0, pady=0)
        
        # Subject label
        self.subject_label = CTkLabel(
            self.header_frame, 
            text="", 
            font=UIConfig.SUBJECT_FONT, 
            anchor="w"
        )
        self.subject_label.pack(fill="x", pady=(20, 5))
        
        # Sender label
        self.sender_label = CTkLabel(
            self.header_frame, 
            text="", 
            font=UIConfig.SENDER_FONT, 
            anchor="w"
        )
        self.sender_label.pack(fill="x", pady=(0, 10))
        
        # Body content frame
        self.body_content = CTkFrame(self.content_frame, fg_color=UIConfig.CONTENT_BG)
        self.body_content.pack(fill="both", expand=True, padx=30, pady=(1, 30))
        
        # Configure columns
        self.body_content.columnconfigure(0, weight=1)
        self.body_content.columnconfigure(1, weight=0, minsize=20)
        self.body_content.columnconfigure(2, weight=2)
        self.body_content.columnconfigure(3, weight=0, minsize=20)
        self.body_content.columnconfigure(4, weight=1)
        
        # Email Summary section
        self.summary_label = CTkLabel(
            self.body_content,
            text="Email Summary",
            font=UIConfig.SENDER_FONT,
            anchor="center"
        )
        self.summary_label.grid(row=0, column=0, sticky="nsew", padx=(0, 0), pady=(0, 3))
        
        self.summary_text = CTkTextbox(
            self.body_content,
            font=UIConfig.BODY_FONT,
            wrap="word",
            height=470,
            corner_radius=15,
            border_width=1,
            border_spacing=5,
            spacing1=2, spacing2=2, spacing3=2
        )
        self.summary_text.grid(row=1, column=0, sticky="nsew", pady=(0, 0))
        
        # Email Content section
        self.content_label = CTkLabel(
            self.body_content,
            text="Email Content",
            font=UIConfig.SENDER_FONT,
            anchor="center"
        )
        self.content_label.grid(row=0, column=2, sticky="nsew", padx=(0, 0), pady=(0, 3))
        
        self.body_text = CTkTextbox(
            self.body_content,
            font=UIConfig.BODY_FONT,
            wrap="word",
            height=470,
            corner_radius=15,
            border_width=1,
            border_spacing=5,
            spacing1=2, spacing2=2, spacing3=2

        )
        self.body_text.grid(row=1, column=2, sticky="nsew", pady=(0, 0))
        
        # Draft Response section (initially hidden)
        self.draft_label = CTkLabel(
            self.body_content,
            text="Draft Response",
            font=UIConfig.SENDER_FONT,
            anchor="center"
        )
        
        self.draft_text = CTkTextbox(
            self.body_content,
            font=UIConfig.BODY_FONT,
            wrap="word",
            height=470,
            corner_radius=15,
            border_width=1,
            border_spacing=5,
            spacing1=2, spacing2=2, spacing3=2

        )
        
        # Action frame for buttons (below sender label)
        self.action_frame = CTkFrame(self.content_frame, fg_color="transparent")
        self.action_frame.pack(fill="both", pady=(0, 15))
        
        # Set default content
        self._set_default_content()
    
    def _set_default_content(self):
        """Set default content when no email is selected"""
        self.subject_label.configure(text="Welcome to AuraMail!")
        self.sender_label.configure(text="Select an email to view its details.")
        self.body_text.configure(state="normal")
        self.body_text.delete("1.0", END)
        self.body_text.insert("1.0", "No email selected. Please choose an email from the list on the left to see its content here.")
        self.body_text.configure(state="disabled")

        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", END)
        self.summary_text.insert("1.0", "No summary available. Select an email to see its summary.")
        self.summary_text.configure(state="disabled")

        self._hide_draft_response()
        self._clear_action_buttons()

    def display_email(self, email: EmailData, summary_content=" ", show_draft: bool = False, category: str = None, action_callback: Callable = None):
        """Display an email in the detail view, with action buttons if needed"""
        self.current_email = email
        self.current_category = category
        self.action_callback = action_callback
        self.subject_label.configure(text=email.subject)
        self.sender_label.configure(text=f"From: {email.sender}")
        

        # Display email content
        self.body_text.configure(state="normal")
        self.body_text.delete("1.0", END)
        self.body_text.insert("1.0", email.body)
        self.body_text.configure(state="disabled")

        # Display summary with proper error handling
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", END)
        
        # Get summary as string with proper error handling
        summary_string = self._show_summary(content=summary_content)
        self.summary_text.insert("1.0", summary_string)
        self.summary_text.configure(state="disabled")

        # Show/hide draft response based on email type
        if show_draft and email.draft_response:
            self._show_draft_response(email.draft_response)
        else:
            self._hide_draft_response()

        # Show action buttons for notify or pending
        self._show_action_buttons(category)
    
        
    def _clear_action_buttons(self):
        for widget in self.action_frame.winfo_children():
            widget.destroy()

    def _show_action_buttons(self, category):
        self._clear_action_buttons()
        email = self.current_email
        cb = self.action_callback if self.action_callback else (lambda _: None)
        if category == "notify":

            # Ignore button
            ignore_btn = CTkButton(
                self.action_frame,
                text="Ignore",
                width=70,
                height=25,
                font=UIConfig.ACTION_BUTTON_FONT,
                fg_color=UIConfig.REJECT_BUTTON_COLOR,
                hover_color=UIConfig.REJECT_BUTTON_HOVER,
                command=lambda: self._handle_ignore()
            )
            ignore_btn.pack(side="right", padx=(5,50))
            
            # Respond button
            respond_btn = CTkButton(
                self.action_frame,
                text="Respond",
                width=70,
                height=25,
                font=UIConfig.ACTION_BUTTON_FONT,
                fg_color=UIConfig.ACTION_BUTTON_COLOR,
                hover_color=UIConfig.ACTION_BUTTON_HOVER,
                command=lambda: self._handle_respond()
            )
            respond_btn.pack(side="right", padx=(5,0))
            
        elif category == "human":
            
            # Reject button
            reject_btn = CTkButton(
                self.action_frame,
                text="Reject",
                width=70,
                height=25,
                font=UIConfig.ACTION_BUTTON_FONT,
                fg_color=UIConfig.REJECT_BUTTON_COLOR,
                hover_color=UIConfig.REJECT_BUTTON_HOVER,
                command=lambda: self._handle_reject()
            )
            reject_btn.pack(side="right", padx=(5,50))

            # Approve button
            approve_btn = CTkButton(
                self.action_frame,
                text="Approve",
                width=70,
                height=25,
                font=UIConfig.ACTION_BUTTON_FONT,
                fg_color=UIConfig.ACTION_BUTTON_COLOR,
                hover_color=UIConfig.ACTION_BUTTON_HOVER,
                command=lambda: self._handle_approve()
            )
            approve_btn.pack(side="right", padx=(5,0))
            
    def _show_summary(self, content=""):
        """Return summary content as string, handling various input types"""
        if content is None:
            return "No summary available."
        
        # If content is already a string, return it
        if isinstance(content, str):
            return content if content.strip() else "No summary available."
        
        # If content has a summary_content attribute (like a summary object)
        if hasattr(content, 'summary_content'):
            summary = getattr(content, 'summary_content', '')
            return str(summary) if summary else "No summary available."
        
        # If content is a dict, try to get summary from it
        if isinstance(content, dict):
            summary = content.get('summary', content.get('summary_content', ''))
            return str(summary) if summary else "No summary available."
        
        # For any other type, convert to string
        try:
            return str(content) if content else "No summary available."
        except:
            return "No summary available."
    
    
    def _handle_ignore(self):
        root = self._get_root()
        type = "resume_workflow"
        data = {
            "flag": False, 
            "workflow_id": self.current_email.workflow_id
        }
    
        EmailService.notify_to_ignore(self.current_email)
        
        if self.action_callback:
            self.action_callback("refresh")
            
        root.send_commands(type, data)
                    
    
    def _handle_respond(self):
        def on_context_provided(context: str):

            root = self._get_root()
            type = "resume_workflow"
            data = {
                "flag": True,
                "feedback": context,
                "workflow_id": self.current_email.workflow_id
            }   
            EmailService.remove_notify(self.current_email)
            if self.action_callback:
                self.action_callback("refresh")

            root.send_commands(type, data)

        dialog = ContextDialog(
            self.content_frame.master.master,
            title="Provide Response Context",
            prompt="Please provide context for your response to help the AI generate an appropriate email:",
            callback=on_context_provided
        )


    def _handle_approve(self):
        root = self._get_root()
        type = "approve"
        data = {
            "flag": True,
            "workflow_id": self.current_email.workflow_id
        }
                
        EmailService.approve_draft_response(self.current_email)
        
        if self.action_callback:
            self.action_callback("refresh")
            
        root.send_commands(command_type= type, data= data)


    def _handle_reject(self):
        def on_feedback_provided(feedback: str):
            root = self._get_root()
            type = "reject"
            data = {
                "flag": False,
                "feedback": feedback,
                "workflow_id": self.current_email.workflow_id
            }

            self._show_loading_draft()
                
            root.send_commands(type, data)

                
        dialog = ContextDialog(
            self.content_frame.master.master,
            title="Provide Feedback",
            prompt="Please provide feedback to help the AI improve the response:",
            callback=on_feedback_provided
        )

    def _show_loading_draft(self):
        self.draft_text.configure(state="normal", text_color="orange")
        self.draft_text.delete("1.0", END)
        self.draft_text.insert("1.0", "🤖 Generating draft email... Please wait.")
        self.draft_text.configure(state="disabled")        

    def _show_draft_response(self, draft_response: str):
        """Show the draft response section"""
        
        # Reconfigure columns to show 3 sections
        self.body_content.columnconfigure(0, weight=1)
        self.body_content.columnconfigure(1, weight=0, minsize=10)
        self.body_content.columnconfigure(2, weight=1)
        self.body_content.columnconfigure(3, weight=0, minsize=10)
        self.body_content.columnconfigure(4, weight=1)
        
        # Show draft label and text
        self.draft_label.grid(row=0, column=4, sticky="w", padx=(0, 0), pady=(0, 3))
        self.draft_text.grid(row=1, column=4, sticky="nsew", pady=(0, 0))
        
        # Update draft content
        self.draft_text.configure(state="normal", text_color="orange")
        self.draft_text.delete("1.0", END)
        self.draft_text.insert("1.0", draft_response)
        self.draft_text.configure(state="disabled")
    
    def _hide_draft_response(self):
        """Hide the draft response section"""
        # Reconfigure columns to show 2 sections
        self.body_content.columnconfigure(0, weight=1)
        self.body_content.columnconfigure(1, weight=0, minsize=20)
        self.body_content.columnconfigure(2, weight=2)
        self.body_content.columnconfigure(3, weight=0)
        self.body_content.columnconfigure(4, weight=0)
        
        # Hide draft widgets
        self.draft_label.grid_remove()
        self.draft_text.grid_remove()
    
    def show(self):
        """Show the detail view only if an email is selected"""
        if self.current_email is not None:
            self.content_frame.pack(fill="both", expand=True, padx=0, pady=0)
        else:
            self.hide()
    
    def hide(self):
        """Hide the detail view"""
        self.content_frame.pack_forget()
        
    def _get_root(self):
        """Get root window"""
        
        widget = self.parent
        while widget:
            if hasattr(widget, "frontend_communicator"):
                return widget
            widget= widget.master
        return None

class SendEmailView:
    """Manages the send email form view"""
    def __init__(self, parent: CTkFrame, on_back: Callable):
        self.parent = parent
        self.on_back = on_back
        
        self.content_frame = None
        self.header_frame = None
        self.back_btn = None
        
        self.from_entry = None
        self.to_entry = None
        self.prompt_text = None
        self.draft_text = None

        self.current_workflow_id = None  # Add this line

        self._create_widgets()
    
    def _create_widgets(self):
        """Create the send email form widgets"""
        # Main content frame
        self.content_frame = CTkFrame(self.parent, fg_color=UIConfig.CONTENT_BG)
        
        # Header frame
        self.header_frame = CTkFrame(self.content_frame, fg_color=UIConfig.CONTENT_BG)
        self.header_frame.pack(fill="x", padx=30, pady=(30, 0))
        
        # Back button
        self.back_btn = CTkButton(
            self.header_frame, 
            text="← Back", 
            width=80, 
            command=self.on_back,
            fg_color="#282b30"
        )
        self.back_btn.pack(anchor="w", padx=0, pady=0)
        
        # Title
        title_label = CTkLabel(
            self.header_frame, 
            text="Send Email", 
            font=UIConfig.SUBJECT_FONT, 
            anchor="w"
        )
        title_label.pack(fill="x", pady=(20, 5))
        
        # Main form frame with 2-column layout
        form_frame = CTkFrame(self.content_frame, fg_color=UIConfig.CONTENT_BG)
        form_frame.pack(fill="both", expand=True, padx=30, pady=(20, 30))
        
        # Configure grid columns: Left column (form), spacer, Right column (draft)
        form_frame.grid_columnconfigure(0, weight=1)  # Left column - form fields
        form_frame.grid_columnconfigure(1, weight=0, minsize=20)  # Spacer
        form_frame.grid_columnconfigure(2, weight=1)  # Right column - draft
        form_frame.grid_rowconfigure(0, weight=1)
        
        # LEFT COLUMN - Form Fields
        left_frame = CTkFrame(form_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # From field
        from_label = CTkLabel(left_frame, text="From:", font=UIConfig.SENDER_FONT)
        from_label.pack(anchor="w", pady=(0, 5))
        
        self.from_entry = CTkEntry(
            left_frame, 
            height=35, 
            font=UIConfig.BODY_FONT,
            placeholder_text="your-email@example.com"
        )
        self.from_entry.pack(fill="x", pady=(0, 15))
        
        # To field
        to_label = CTkLabel(left_frame, text="To:", font=UIConfig.SENDER_FONT)
        to_label.pack(anchor="w", pady=(0, 5))
        
        self.to_entry = CTkEntry(
            left_frame, 
            height=35, 
            font=UIConfig.BODY_FONT,
            placeholder_text="recipient@example.com"
        )
        self.to_entry.pack(fill="x", pady=(0, 10))
        
        # AI Prompt field
        prompt_label = CTkLabel(left_frame, text="AI Prompt (describe what email you want):", font=UIConfig.SENDER_FONT)
        prompt_label.pack(anchor="w", pady=(0, 0), side= 'top')
        
        self.prompt_text = CTkTextbox(
            left_frame,
            font=UIConfig.BODY_FONT,
            corner_radius=8,
            border_spacing=5,
            spacing1=2, spacing2=2, spacing3=2
            
        )
        self.prompt_text.pack(fill="both", pady=(0, 15), expand= True)
        
        # Generate button
        generate_btn = CTkButton(
            left_frame,
            text="Generate Draft",
            height=35,
            font=UIConfig.ACTION_BUTTON_FONT,
            fg_color=UIConfig.GENERATE_DRAFT_BUTTON_COLOR,
            hover_color=UIConfig.GENERATE_DRAFT_BUTTON_HOVER,
            command=self._generate_draft
        )
        generate_btn.pack(anchor="w", pady=(5, 0))
        
        # RIGHT COLUMN - Draft Email
        right_frame = CTkFrame(form_frame, fg_color="transparent")
        right_frame.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        
        # Draft response field
        draft_label = CTkLabel(right_frame, text="Draft Email (AI Generated):", font=UIConfig.SENDER_FONT)
        draft_label.pack(anchor="w", pady=(0, 5))
        
        self.draft_text = CTkTextbox(
            right_frame,
            font=UIConfig.BODY_FONT,
            corner_radius=8,
            state="disabled",
            border_spacing=5,
            spacing1=2, spacing2=2, spacing3=2
        )
        self.draft_text.pack(fill="both", expand=True, pady=(0, 15))
        
        # Add placeholder text to show it's empty initially
        self.draft_text.configure(state="normal")
        self.draft_text.insert("1.0", "Click 'Generate Draft' to create an AI-generated email...")
        self.draft_text.configure(state="disabled", text_color="gray")
        
        # Button frame (under draft email box)
        button_frame = CTkFrame(right_frame, fg_color="transparent")
        button_frame.pack(fill="x")
        
        # Send button (left)
        send_btn = CTkButton(
            button_frame,
            text="Send Email",
            height=35,
            font=UIConfig.ACTION_BUTTON_FONT,
            fg_color=UIConfig.ACTION_BUTTON_COLOR,
            hover_color=UIConfig.ACTION_BUTTON_HOVER,
            command=self._send_email
        )
        send_btn.pack(side="left", padx=(0, 10))
        
        # Clear button (right)
        clear_btn = CTkButton(
            button_frame,
            text="Reject",
            height=35,
            font=UIConfig.ACTION_BUTTON_FONT,
            fg_color=UIConfig.REJECT_BUTTON_COLOR,
            hover_color=UIConfig.REJECT_BUTTON_HOVER,
            command=self._reject_draft
        )
        clear_btn.pack(side="left")
    
    def _generate_draft(self):
        """Generate draft email using AI"""
        try:
            from_email = self.from_entry.get().strip()
            to_email = self.to_entry.get().strip()
            users_intent = self.prompt_text.get("1.0", END).strip()
            
            if not all([from_email, to_email, users_intent]):
                messagebox.showwarning("Warning", "Please fill in From, To, and AI Prompt fields.")
                return
            
            # Get root window to send command
            root = self._get_root()
            if root:
                # Generate unique workflow ID for tracking
                import uuid
                workflow_id = str(uuid.uuid4())
                
                # Send command to backend to generate email
                type = "generate_email"
                data = {
                    "from_email": from_email,
                    "to_email": to_email,
                    "users_intent": users_intent,
                    "workflow_id": workflow_id  # Add this for tracking
                }
                root.send_commands(type, data)
                
                # Store workflow_id for later use
                self.current_workflow_id = workflow_id
                
                # Show loading message in draft
                self._show_loading_draft()
            else:
                messagebox.showerror("Error", "Unable to connect to AI service.")
                
        except Exception as e:
            print(f"Error generating draft: {e}")
            messagebox.showerror("Error", "Failed to generate draft email.")
    
    def _show_loading_draft(self):
        self.draft_text.configure(state="normal", text_color="orange")
        self.draft_text.delete("1.0", END)
        self.draft_text.insert("1.0", "🤖 Generating draft email... Please wait.")
        self.draft_text.configure(state="disabled")
    
    def _send_email(self):
        """Send the email (approve the draft)"""
        try:
            draft_content = self.draft_text.get("1.0", END).strip()
            
            if not hasattr(self, 'current_workflow_id'):
                messagebox.showwarning("Warning", "Please generate a draft first.")
                return
            
            if not draft_content or "Click 'Generate Draft'" in draft_content:
                messagebox.showwarning("Warning", "Please generate a draft first.")
                return
            
            # Get root window to send command
            root = self._get_root()
            if root:
                # Send approve command to backend
                type = "approve_draft"
                data = {
                    "flag": True,
                    "workflow_id": self.current_workflow_id
                }
                root.send_commands(type, data)
                
                messagebox.showinfo("Success", "Email sent successfully!")
                self._clear_form()
            else:
                messagebox.showerror("Error", "Unable to send email.")
                
        except Exception as e:
            print(f"Error sending email: {e}")
            messagebox.showerror("Error", "Failed to send email.")

    def _reject_draft(self):
        """Reject current draft and ask for feedback"""
        def on_context_provided(feedback: str):
            """Callback function called when user provides feedback"""
            root = self._get_root()
            
            # Send command to backend with user's feedback
            type = "reject_draft"
            data = {
                "flag": False,
                "feedback": feedback,
                "workflow_id": self.current_workflow_id
            }
            
            self._show_loading_draft()
            root.send_commands(type, data)
                
        # Show context dialog with callback
        dialog = ContextDialog(
            self.parent.master.master,
            title="Provide feedback",
            prompt="Please provide feedback to help the AI improve the response:",
            callback=on_context_provided  
        )

    def _clear_form(self):
        """Clear all form fields"""
        self.from_entry.delete(0, END)
        self.to_entry.delete(0, END)
        self.prompt_text.delete("1.0", END)
        
        # Reset draft box to initial state
        self.draft_text.configure(state="normal", text_color="gray")
        self.draft_text.delete("1.0", END)
        self.draft_text.insert("1.0", "Click 'Generate Draft' to create an AI-generated email...")
        self.draft_text.configure(state="disabled")
    
    def update_draft(self, draft_content: str):
        """Update the draft text field with generated content"""
        self.draft_text.configure(state="normal", text_color="white")  # Normal text color
        self.draft_text.delete("1.0", END)
        self.draft_text.insert("1.0", draft_content)
        self.draft_text.configure(state="normal")  # Allow editing of generated draft
    
    def _get_root(self):
        """Get root window"""
        widget = self.parent
        while widget:
            if hasattr(widget, "frontend_communicator"):
                return widget
            widget = widget.master
        return None
    
    def show(self):
        """Show the send email view"""
        self.content_frame.pack(fill="both", expand=True, padx=0, pady=0)
    
    def hide(self):
        """Hide the send email view"""
        self.content_frame.pack_forget()

class EmailRow:
    """Represents a single email row in the grid"""
    def __init__(self, parent: CTkFrame, email: EmailData, index: int, on_click: Callable, 
                 view_type: str = "normal"):
        self.parent = parent
        self.email = email
        self.index = index
        self.on_click = on_click
        self.view_type = view_type
        self.row_frame = None
        self.left_label = None
        self.time_label = None
        self.action_frame = None
        
        self._create_widgets()
        self._bind_events()
    
    def _create_widgets(self):
        """Create the row widgets"""
        # Main row frame
        self.row_frame = CTkFrame(self.parent, fg_color=UIConfig.ROW_COLOR)
        self.row_frame.grid(row=self.index, column=0, columnspan=3, sticky="ewns", padx=0, pady=1)
        
        # Configure columns based on view type
        if self.view_type in ["notify", "pending"]:
            self.row_frame.grid_columnconfigure(0, weight=1)
            self.row_frame.grid_columnconfigure(1, weight=0, minsize=110)
            self.row_frame.grid_columnconfigure(2, weight=0, minsize=200)
        else:
            self.row_frame.grid_columnconfigure(0, weight=1)
            self.row_frame.grid_columnconfigure(1, weight=0, minsize=110)
        
        # Left label (sender | snippet)
        left_text = f"{self.email.sender} | {self.email.subject}"
        self.left_label = CTkLabel(
            self.row_frame, 
            text=left_text, 
            anchor="w", 
            font=UIConfig.EMAIL_FONT
        )
        self.left_label.grid(row=0, column=0, sticky="ewns", padx=(10,5), pady=2)
        
        # Time label
        self.time_label = CTkLabel(
            self.row_frame, 
            text=self.email.time, 
            anchor="e", 
            font=UIConfig.TIME_FONT, 
            width=100
        )
        self.time_label.grid(row=0, column=1, sticky="e", padx=(5,10), pady=2)
        
        # Action buttons for notify and pending views
        if self.view_type == "notify":
            self._create_notify_actions()
        elif self.view_type == "pending":
            self._create_pending_actions()
    
    def _create_notify_actions(self):
        """Create action buttons for notify view"""
        self.action_frame = CTkFrame(self.row_frame, fg_color="transparent")
        self.action_frame.grid(row=0, column=2, sticky="e", padx=(5,10), pady=2)
        
        # Ignore button
        ignore_btn = CTkButton(
            self.action_frame,
            text="Ignore",
            width=70,
            height=25,
            font=UIConfig.ACTION_BUTTON_FONT,
            fg_color=UIConfig.REJECT_BUTTON_COLOR,
            hover_color=UIConfig.REJECT_BUTTON_HOVER,
            command=lambda: self._handle_ignore()
        )
        ignore_btn.pack(side="right", padx=(5,0))
        
        # Respond button
        respond_btn = CTkButton(
            self.action_frame,
            text="Respond",
            width=70,
            height=25,
            font=UIConfig.ACTION_BUTTON_FONT,
            fg_color=UIConfig.ACTION_BUTTON_COLOR,
            hover_color=UIConfig.ACTION_BUTTON_HOVER,
            command=lambda: self._handle_respond()
        )
        respond_btn.pack(side="right")
    
    def _create_pending_actions(self):
        """Create action buttons for pending view"""
        self.action_frame = CTkFrame(self.row_frame, fg_color="transparent")
        self.action_frame.grid(row=0, column=2, sticky="e", padx=(5,10), pady=2)
        
        # Reject button
        reject_btn = CTkButton(
            self.action_frame,
            text="Reject",
            width=70,
            height=25,
            font=UIConfig.ACTION_BUTTON_FONT,
            fg_color=UIConfig.REJECT_BUTTON_COLOR,
            hover_color=UIConfig.REJECT_BUTTON_HOVER,
            command=lambda: self._handle_reject()
        )
        reject_btn.pack(side="right", padx=(5,0))
        
        # Approve button
        approve_btn = CTkButton(
            self.action_frame,
            text="Approve",
            width=70,
            height=25,
            font=UIConfig.ACTION_BUTTON_FONT,
            fg_color=UIConfig.ACTION_BUTTON_COLOR,
            hover_color=UIConfig.ACTION_BUTTON_HOVER,
            command=lambda: self._handle_approve()
        )
        approve_btn.pack(side="right")
    
    def _handle_ignore(self):
        """Handle ignore button click"""
        
        root = self._get_root()
        
        type = "resume_workflow"
        data = {
            "flag": False, 
            "workflow_id": self.email.workflow_id
        }
        
        # Move email to ignore category
        EmailService.notify_to_ignore(self.email)
        self.on_click("refresh")

        root.send_commands(type, data)

    def _handle_respond(self):
        """Handle respond button click"""
        
        def on_context_provided(context: str):
            """Callback function called when user provides context"""
            root = self._get_root()
            
            # Send command to backend with user's context
            type = "resume_workflow"
            data = {
                "flag": True,
                "feedback": context,
                "workflow_id": self.email.workflow_id
            }
            
            EmailService.remove_notify(self.email)
            self.on_click("refresh")
            
            root.send_commands(type, data)
                
        # Show context dialog with callback
        dialog = ContextDialog(
            self.parent.master.master,
            title="Provide Response Context",
            prompt="Please provide context for your response to help the AI generate an appropriate email:",
            callback=on_context_provided  
        )


    def _handle_approve(self):
        """Handle approve button click"""

        root = self._get_root()
        type = "approve"
        data = {
            "flag": True,
            "workflow_id": self.email.workflow_id
        }
        
        # Send the draft response
        EmailService.approve_draft_response(self.email)
        self.on_click("refresh")
        
        root.send_commands(type, data)
    
    def _handle_reject(self):
        """Handle reject button click"""

        
        def on_context_provided(feedback: str):
            """Callback function called when user provides context"""
            root = self._get_root()
            
            # Send command to backend with user's context
            type = "reject"
            data = {
                "flag": False,
                "feedback": feedback,
                "workflow_id": self.email.workflow_id
            }
            
            self.on_click("refresh")
            
            root.send_commands(type, data)
                
        # Show context dialog with callback
        dialog = ContextDialog(
            self.parent.master.master,
            title="Provide feedback",
            prompt="Please provide feedback to help the AI improve the response:",
            callback=on_context_provided  
        )


        
    def _get_root(self):
        """Get root window"""
        
        widget = self.parent
        while widget:
            if hasattr(widget, "frontend_communicator"):
                return widget
            widget= widget.master
        return None
    
    def _bind_events(self):
        """Bind hover and click events"""
        widgets = [self.row_frame, self.left_label, self.time_label]
        
        for widget in widgets:
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", self._on_click)
    
    def _on_enter(self, event):
        """Handle mouse enter (hover)"""
        self.row_frame.configure(fg_color=UIConfig.ROW_HOVER)
    
    def _on_leave(self, event):
        """Handle mouse leave"""
        self.row_frame.configure(fg_color=UIConfig.ROW_COLOR)
    
    def _on_click(self, event):
        """Handle click event"""
        self.on_click(self.index)
        
class EmailAgentGUI(CTk):
    """Main application class"""
    
    def __init__(self, communicator: Communicator):
        super().__init__()

        self.frontend_communicator = FrontendCommunicator(
           events= communicator.events, 
           commands= communicator.commands
        )     
        
        self.frontend_communicator.set_gui(gui= self)
        
        self.current_category = "home"
        self.current_emails = []
        self.selected_email_index = None
        self._processing_response = False


        self._setup_window()
        self._create_components()
        self._initialize_app()

        # Add system tray setup
        self.tray_manager = None
        self._setup_system_tray()
        
        # Override close behavior
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self._start_event_polling()
            
    def _setup_window(self):
        """Setup the main window"""
        self.title(UIConfig.TITLE)
        self.geometry(UIConfig.WINDOW_SIZE)
        set_appearance_mode(UIConfig.APPEARANCE_MODE)
    
    def _create_components(self):
        """Create all UI components"""
        
        # Taskbar (create first so it appears at top)
        taskbar_callbacks = {
            "home": self.show_home,
            "notify": lambda: self.load_emails("notify"),
            "ignore": lambda: self.load_emails("ignore"),
            "human": lambda: self.load_emails("human"),
            "send": self.show_send_email
        }
        self.taskbar = Taskbar(self, taskbar_callbacks)
        
        # Main frame (below taskbar)
        self.main_frame = CTkFrame(self)
        self.main_frame.pack(side="top", fill="both", expand=True, padx=0, pady=0)
        
        # Email grid
        self.email_grid = EmailGrid(self.main_frame, self.handle_email_interaction)
        
        # Email detail view
        self.email_detail = EmailDetailView(self.main_frame, self.show_email_list)
        
        # Send Email view
        self.send_email_view = SendEmailView(self.main_frame, self.show_email_list)

        
    
    def _initialize_app(self):
        """Initialize the application"""
        self.show_home()
    
    def show_home(self):
        """Show the home view with all emails"""
        self.load_emails("home")

    def show_send_email(self):
        """Show the send email view"""
        self.current_category = "send"
        self.taskbar.set_active_button("send")
        
        # Hide other views
        self.email_grid.hide()
        self.email_detail.hide()
        
        # Show send email view
        self.send_email_view.show()
    
    def load_emails(self, category: str):
        """Load emails for a specific category"""
        
        self.current_category = category
        self.taskbar.set_active_button(category)
        
        # Load emails from service
        self.current_emails = EmailService.load_emails_by_category(category)
        
        # Determine view type based on category
        view_type = "normal"
        
        if category == "notify":
            view_type = "notify"
        elif category == "human":
            view_type = "pending"
            
        # Update grid view
        self.email_grid.update_emails(self.current_emails, view_type)
        
        # Reset detail view state
        self.email_detail.current_email = None
        self.show_email_list()

    
    def handle_email_interaction(self, action):
        """Handle email interaction (click or action)"""
        
        if action == "refresh":
            # Refresh the current view
            self.load_emails(self.current_category)
            
        elif isinstance(action, int):
            
            # Display email details
            self.display_email_details(action)

    def display_email_details(self, index: int):
        """Display detailed view of selected email"""
        
        if 0 <= index < len(self.current_emails):
            self.selected_email_index = index
            email = self.current_emails[index]
            
            # Always use the current category for detail view
            category = self.current_category
            summary = email.summary
            draft = category == "human" and email.draft_response
            
            self.email_grid.hide()
            self.email_detail.display_email(
                email,
                summary_content= summary,
                show_draft=draft,
                category=category,
                action_callback=self.handle_email_interaction
            )
            self.email_detail.show()
            
        else:
            self.show_email_list()
    
    def show_email_list(self):
        """Show the email list grid"""
        self.email_detail.hide()
        self.send_email_view.hide() 
        self.email_grid.show()
        self.selected_email_index = None

        # Only show grid if not in send email mode
        if self.current_category != "send":
            self.email_grid.show()
        else:
            # If coming back from send email, go to home
            self.show_home()
        
        self.selected_email_index = None

    def handle_draft_generated(self, draft_content: str):
        """Handle draft email generated by AI"""
        if hasattr(self, 'send_email_view'):
            self.send_email_view.update_draft(draft_content)
        
    def _start_event_polling(self):
        """Start polling for events from backend"""
        self._poll_events()
    
    def _poll_events(self):
        """Poll for events and schedule next poll"""
        try:
            # Process up to 5 events per poll cycle to prevent GUI freezing
            self.frontend_communicator.poll_events(
                callback_func=self.frontend_communicator.process_events,
                max_events_per_poll=5
            )
            
            # If there are still events pending, schedule immediate next poll
            if self.frontend_communicator.has_pending_events():
                poll_interval = 10  
            else:
                poll_interval = 100 
                
        except Exception as e:
            print(f"Error in GUI event polling: {e}")
            poll_interval = 100  # Default interval on error
        
        # Schedule next poll
        self.after(poll_interval, self._poll_events)
        
    def send_commands(self, command_type: str, data: dict):
        """Send commands to backend"""
        try:
            self.frontend_communicator.send_commands(command_type, data)
            print(f"Sent command: {command_type} with data: {data}")
        except Exception as e:
            print(f"Error sending command: {e}")

    def _setup_system_tray(self):
        """Setup system tray functionality"""
        try:
            self.tray_manager = SystemTrayManager(self)
            self.tray_manager.start_tray_icon()
            print("System tray icon started")
        except Exception as e:
            print(f"Failed to setup system tray: {e}")
            # Continue without tray if it fails
    
    def on_closing(self):
        """Handle window close button click"""
        try:
            # Show notification about minimizing to tray
            result = messagebox.askyesnocancel(
                "AuraMail", 
                "What would you like to do?\n\n"
                "• Yes: Exit completely (stop email monitoring)\n"
                "• No: Minimize to system tray (keep running in background)\n"
                "• Cancel: Keep window open"
            )
            if result is True:  # Yes - minimize to tray
                self.quit_application()
                    
            elif result is False:  # No - exit completely
                if self.tray_manager:
                    self.tray_manager.hide_window()
                else:
                    # Fallback to iconify if tray not available
                    self.iconify()
            # Cancel - do nothing, keep window open
                
        except Exception as e:
            print(f"Error in on_closing: {e}")
            # Fallback behavior
            self.iconify()
    
    def quit_application(self):
        """Completely quit the application"""
        try:
            if self.tray_manager:
                self.tray_manager.stop_tray_icon()
            
            self.quit()
            self.destroy()
            
        except Exception as e:
            print(f"Error quitting application: {e}")
    
    def shutdown(self):
        """Shutdown method that can be called externally"""
        if self.tray_manager:
            self.tray_manager.stop_tray_icon()    
  
def app():
    """Main entry point"""
    app = EmailAgentGUI(Communicator())
    app.mainloop()

if __name__ == "__main__":
    app()