import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Callable
import tkinter as tk
from tkinter import END, messagebox

from customtkinter import *
from CTkListbox import *

import queue
import datetime

# Constants
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path("ui/assets")

# UI Configuration
class UIConfig:
    WINDOW_SIZE = "1000x600"
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
    
    # Fonts
    BUTTON_FONT = ("Noto Sans", 18, "bold")
    SUBJECT_FONT = ("Arial", 20, "bold")
    SENDER_FONT = ("Arial", 14)
    EMAIL_FONT = ("Arial", 13)
    TIME_FONT = ("Arial", 12)
    BODY_FONT = ("Arial", 13)
    ACTION_BUTTON_FONT = ("Arial", 12, "bold")

class EmailData:
    """Data class for email information"""
    def __init__(self, subject: str, sender: str, body: str, 
                 time: str, category: str = None, id: str = None,  
                 workflow_id: str = None, summary: str = None, draft_response: str = None):
        
        self.subject = subject
        self.sender = sender
        self.body = body
        self.time = time
        self.category = category # "notify", "ignore", "pending"
        self.id = id
        self.workflow_id = workflow_id
        self.summary = summary
        self.draft_response = draft_response  
    
    def get_snippet(self, max_length: int = 40) -> str:
        """Get truncated body text for preview"""
        if len(self.body) <= max_length:
            return self.body
        return self.body[:max_length] + "..."

class ContextDialog(CTkToplevel):
    """Dialog for getting user context input"""
    def __init__(self, parent, title: str, prompt: str, callback: Callable):
        super().__init__(parent)
        self.callback = callback
        self.result = None
        
        self.title(title)
        self.geometry("500x300")
        self.transient(parent)
        self.grab_set()
        
        # Center the dialog
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.winfo_screenheight() // 2) - (300 // 2)
        self.geometry(f"500x300+{x}+{y}")
        
        self._create_widgets(prompt)
    
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
    
    def _submit(self):
        """Handle submit button"""
        context = self.text_input.get("1.0", END).strip()
        if context:
            self.result = context
            self.callback(context)
            self.destroy()
        else:
            messagebox.showwarning("Warning", "Please enter some context.")
    
    def _cancel(self):
        """Handle cancel button"""
        self.destroy()

class EmailRow:
    """Represents a single email row in the grid"""
    def __init__(self, parent: CTkFrame, email: EmailData, index: int, on_click: Callable, 
                 view_type: str = "normal"):
        self.parent = parent
        self.email = email
        self.index = index
        self.on_click = on_click
        self.view_type = view_type  # "normal", "notify", "pending"
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
        left_text = f"{self.email.sender} | {self.email.get_snippet()}"
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
        data = {
            "workflow_id": self.email.workflow_id,
        }
        root.send_command_to_backend(command_type= "cancel_workflow", data= data)
        
        # Move email to ignore category
        EmailService.notify_to_ignore(self.email)
        self.on_click("refresh")
    
    def _handle_respond(self):
        """Handle respond button click"""
        def on_context_provided(context: str):
            # Generate draft response with context

            root = self._get_root()
            data = {
                "workflow_id": self.email.workflow_id,
                "flag": True,
                "feedback": context
            }
            root.send_command_to_backend(command_type= "email_response", data= data)
            
            EmailService.notify_to_pending(self.email)
            self.on_click("refresh")
        
        # Show context dialog
        dialog = ContextDialog(
            self.parent.master.master,  # Get root window
            title= "Provide Response Context",
            prompt= "Please provide context for your response to help the AI generate an appropriate email:",
            callback= on_context_provided
        )
    
    def _handle_approve(self):
        """Handle approve button click"""
        root = self._get_root()
        data = {
            "workflow_id": self.email.workflow_id,
            "flag": True,
            "feedback": "<no feedback given>"
        }
        root.send_command_to_backend(command_type= "email_approval", data= data)
        
        # Send the draft response
        EmailService.approve_draft_response(self.email)
        self.on_click("refresh")
    
    def _handle_reject(self):
        """Handle reject button click"""
        
        def on_feedback_provided(feedback: str):
            # Regenerate draft with feedback
            root = self._get_root()
            data = {
                "workflow_id": self.email.workflow_id,
                "flag": False,
                "feedback": feedback
            }
            root.send_command_to_backend(command_type= "email_approval", data= data)
            
            EmailService.regenerate_draft_response(self.email, feedback)
            self.on_click("refresh")
        
        # Show feedback dialog
        dialog = ContextDialog(
            self.parent.master.master,  # Get root window
            title= "Provide Feedback",
            prompt= "Please provide feedback to help the AI improve the response:",
            callback= on_feedback_provided
        )
    
    def _bind_events(self):
        """Bind hover and click events"""
        widgets = [self.row_frame, self.left_label, self.time_label]
        
        for widget in widgets:
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", self._on_click)
    
    def _get_root(self):
        """Get root window"""
        
        widget = self.parent
        while widget:
            if hasattr(widget, "send_command_to_backend"):
                return widget
            widget.master
        return None
    
    def _on_enter(self, event):
        """Handle mouse enter (hover)"""
        self.row_frame.configure(fg_color=UIConfig.ROW_HOVER)
    
    def _on_leave(self, event):
        """Handle mouse leave"""
        self.row_frame.configure(fg_color=UIConfig.ROW_COLOR)
    
    def _on_click(self, event):
        """Handle click event"""
        self.on_click(self.index)

class EmailGrid:
    """Manages the email list grid view"""
    def __init__(self, parent: CTkFrame, on_email_select: Callable):
        self.parent = parent
        self.on_email_select = on_email_select
        self.grid_frame = None
        self.email_rows = []
        self.current_view_type = "normal"
        
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
        self._clear_grid()
        self.email_rows = []
        self.current_view_type = view_type
        
        for idx, email in enumerate(emails):
            row = EmailRow(self.grid_frame, email, idx, self.on_email_select, view_type)
            self.email_rows.append(row)
     
    def _clear_grid(self):
        """Clear all widgets from the grid"""
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
    
    def show(self):
        """Show the grid"""
        self.wrapper_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    def hide(self):
        """Hide the grid"""
        self.wrapper_frame.pack_forget()

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
            height=500,
            corner_radius=15,
            border_width=1,
            border_spacing=5,
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
            height=500,
            corner_radius=15,
            border_width=1,
            border_spacing=5,
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
            height=500,
            corner_radius=15,
            border_width=1,
            border_spacing=5,
        )
        
        # Action frame for buttons (below sender label)
        self.action_frame = CTkFrame(self.content_frame, fg_color="transparent")
        self.action_frame.pack(fill="x", pady=(0, 15))
        
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
        
    
    def display_email(self, email: EmailData, summary_content = None, show_draft: bool = False, category: str = None, action_callback: Callable = None):
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

        # Display summary (placeholder for now)
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", END)
        self.summary_text.insert("1.0", self._show_summary(email.sender, content= summary_content))
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
            
    def _show_summary(self, sender, content):
        return f"Summary of email from {sender}: \n\n{content}" 
    
    def _handle_ignore(self):
        root = self._get_root()
        data = {
            "workflow_id": self.current_email.workflow_id,

        }
        root.send_command_to_backend(command_type= "cancel_workflow", data= data)
        
        EmailService.notify_to_ignore(self.current_email)
        
        if self.action_callback:
            self.action_callback("refresh")

    def _handle_respond(self):
        def on_context_provided(context: str):
            root = self._get_root()
            data = {
                "workflow_id": self.current_email.workflow_id,
                "flag": True,
                "feedback": context
            }
            root.send_command_to_backend(command_type= "email_response", data= data)
            
            EmailService.notify_to_pending(self.current_email)
            
            if self.action_callback:
                self.action_callback("refresh")
                
        dialog = ContextDialog(
            self.content_frame.master.master,
            title="Provide Response Context",
            prompt="Please provide context for your response to help the AI generate an appropriate email:",
            callback=on_context_provided
        )

    def _handle_approve(self):
        root = self._get_root()
        data = {
            "workflow_id": self.current_email.workflow_id,
            "flag": True,
            "feedback": "<no feedback given>"
        }
        root.send_command_to_backend(command_type= "email_approval", data= data)
        
        EmailService.approve_draft_response(self.current_email)
        
        if self.action_callback:
            self.action_callback("refresh")

    def _handle_reject(self):
        def on_feedback_provided(draft: str):
            
            root = self._get_root()
            data = {
                "workflow_id": self.current_email.workflow_id,
                "flag": False,
                "feedback": draft
            }
            root.send_command_to_backend(command_type= "email_approval", data= data)
            
            EmailService.regenerate_draft_response(self.current_email, draft)
            
            if self.action_callback:
                self.action_callback("refresh")
                
        dialog = ContextDialog(
            self.content_frame.master.master,
            title="Provide Feedback",
            prompt="Please provide feedback to help the AI improve the response:",
            callback=on_feedback_provided
        )
    
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
        self.draft_text.configure(state="normal")
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

class EmailService:
    """Service class for handling email data operations"""
    emails = {
            "home": [],
            "notify": [],
            "ignore": [],
            "human": []
        }

    @staticmethod
    def load_emails_by_category(category: str) -> List[EmailData]:
        """Load emails for a specific category"""
        return EmailService.emails.get(category, EmailService.emails["home"])
        
    @staticmethod
    def add_to_ignore(email: EmailData):
        """Add email to ignore"""
        
        if email in EmailService.emails["home"]:
            EmailService.emails["ignore"].append(email)
            
    @staticmethod
    def add_to_notify(email: EmailData):
        """Add email to ignore"""
        
        if email in EmailService.emails["home"]:
            EmailService.emails["notify"].append(email)
    
    @staticmethod
    def notify_to_ignore(email: EmailData):
        """Move email from notify to ignore category"""
        # Remove from notify
        if email in EmailService.emails["notify"]:
            EmailService.emails["notify"].remove(email)
        
        # Add to ignore if not already there
        if email not in EmailService.emails["ignore"]:
            EmailService.emails["ignore"].append(email)
        
        print(f"Email '{email.subject}' moved to ignore category")
        
    @staticmethod
    def notify_to_pending(email: EmailData):
        """Generate a draft response with user context"""
        
        # Create new email with draft response
        pending_email = EmailData(
                                  email.subject, email.sender, email.body, 
                                  email.time, email.category, email.id, 
                                  email.workflow_id, email.summary, email.draft_response
        )
        
        # Remove from notify
        if email in EmailService.emails["notify"]:
            EmailService.emails["notify"].remove(email)
        
        # Add to pending
        EmailService.emails["human"].append(pending_email)
        
        print(f"Draft response generated for email '{email.subject}'")
    
    @staticmethod
    def approve_draft_response(email: EmailData):
        """Approve and send the draft response"""
        
        # Simulate sending email
        print(f"Email response approved and sent for '{email.subject}'")
        
        # Remove from pending
        if email in EmailService.emails["human"]:
            EmailService.emails["human"].remove(email)
        
        # In a real implementation, you would send the actual email here
    
    @staticmethod
    def regenerate_draft_response(email: EmailData, draft: str):
        """Regenerate draft response with user feedback"""
        
        # Update the draft response
        email.draft_response = draft
        
        print(f"Draft response regenerated for email '{email.subject}' with feedback")

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
        for i in range(4):
            self.taskbar_frame.grid_columnconfigure(i, weight=1)
        
        # Create buttons
        button_configs = [
            ("home", "Home", 0),
            ("notify", "Notify", 1),
            ("ignore", "Ignore", 2),
            ("human", "Pending", 3)
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

class EmailAgentGUI(CTk):
    """Main application class"""
    
    def __init__(self, events: queue = None, commands: queue = None):
        super().__init__()
        
        self.events = events
        self.commands = commands
        
        self.current_category = "home"
        self.current_emails = []
        self.selected_email_index = None
        
        
        self._setup_window()
        self._create_components()
        self._initialize_app()
    
    
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
            "human": lambda: self.load_emails("human")
        }
        self.taskbar = Taskbar(self, taskbar_callbacks)
        
        # Main frame (below taskbar)
        self.main_frame = CTkFrame(self)
        self.main_frame.pack(side="top", fill="both", expand=True, padx=0, pady=0)
        
        # Email grid
        self.email_grid = EmailGrid(self.main_frame, self.handle_email_interaction)
        
        # Email detail view
        self.email_detail = EmailDetailView(self.main_frame, self.show_email_list)
        
    
    def _initialize_app(self):
        """Initialize the application"""
        self.show_home()
    
    def show_home(self):
        """Show the home view with all emails"""
        self.load_emails("home")
    
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


    def add_email(self, email: dict):
        email_input = EmailData(
            subject = email["subject"],
            sender = email["sender"],
            body = email["body"],
            time = datetime.datetime.now().strftime("%H:%M %d/%m/%Y"),
            id = email["id"],
            workflow_id= email["workflow_id"]
        )
        
        EmailService.emails["home"].append(email_input)
        
        self.load_emails(self.current_category)
    
    def update_email_states(self, id: str, category: str = None, summary: str = None, draft: str = None):
        emails = EmailService.load_emails_by_category("home")
        
        for email in emails:
            
            email_id = email.id  
            if category == "notify" and id == email_id:
                EmailService.add_to_notify(email)
                email.category = category
                email.summary = summary
                
            elif category == "ignore" and id == email_id:
                EmailService.add_to_ignore(email)
                email.category = category
            
            elif category == "pending" and id == email_id:
                email.draft_response = draft
                email.category = category
    
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
        self.email_grid.show()
        self.selected_email_index = None
    
    def send_command_to_backend(self, command_type, data= None):
        if self.commands:
            command = {
                "type": {command_type: data}
            }
            self.commands.put(command)
            print(f"GUI: Sent command '{command_type}' to backend")
        else:
            print(f"GUI: No command queue available to send '{command_type}'")
            
def app():
    """Main entry point"""
    app = EmailAgentGUI()
    app.mainloop()

if __name__ == "__main__":
    app()
    
    
