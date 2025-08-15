from abc import ABC, abstractmethod

from src.nodes import Nodes
from src.states import EmailResponseState, SendEmailState
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

import sqlite3
from dotenv import load_dotenv

try:
    load_dotenv()
except Exception as e:
    print(f"Error in loading .env")
    

class Workflow(ABC):
    def __init__(self, model: str, db_path: str):
        self.model = model
        self.db_path = db_path
        self.node = Nodes(model)
        self.checkpointer = self._initialize_checkpointer()
        
        
    def _initialize_checkpointer(self):
        """Initialize SQLite checkpointer for persistence"""
        try:
            # Validate db_paths
            if not self.db_path:
                print(f"ERROR: db_path is None or empty")
                return None
            
            # Create connection to SQLite database
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            print(f"DEBUG: Connect to SQLITE")
            
            # Create Sqlitesaver with connection
            checkpointer = SqliteSaver(conn)
            return checkpointer
        
        except Exception as e:
            print(f"Error initializing checkpointer: {e}")
            print(f"db_path was: {self.db_path}")
            return None
        
    
    def save_graph(self, path: str = "workflow.png") -> None:
            """
            Dump the Mermaid‑based PNG to a file so you can open it in your OS.
            """
            png_bytes = self.workflow.get_graph().draw_mermaid_png()
            with open(path, "wb") as f:
                f.write(png_bytes)
            print(f"Workflow graph saved to {path}")

    @abstractmethod
    def _create_workflow(self):
        pass
    
class SendEmailWorkflow(Workflow):
    def __init__(self, model: str, db_path: str):
        super().__init__(model, db_path)
        
        self.graph = StateGraph(SendEmailState)
        self.get_workflow = self._create_workflow()
        
    
    def _create_workflow(self):
        # Bind node methods
        writer          = self.node.writer
        send_response   = self.node.send_response

        # Register nodes in the graph
        self.graph.add_node("writer", writer)
        self.graph.add_node("send_response", send_response)
        
        # Set entry point
        self.graph.set_entry_point("writer")
        
        # Connecting nodes
        self.graph.add_edge("writer", "send_response")
        self.graph.add_conditional_edges(
            "send_response", lambda state: state["send_decision"],
            {"response": END, "rewrite": "writer", "error": END}
        )
        
        # Compile with checkpointer
        workflow = self.graph.compile(checkpointer= self.checkpointer)
        return workflow
                
class EmailResponseWorkflow(Workflow):
    def __init__(self, model: str, db_path: str):
        super().__init__(model, db_path)
        
        self.graph = StateGraph(EmailResponseState)        
        self.get_workflow = self._create_workflow()
                   
    def _create_workflow(self): 
        # Bind node methods
        classifier         = self.node.classifier
        summarizer         = self.node.summarizer
        interrupts_handler = self.node.interrupts_handler
        writer             = self.node.writer
        send_response      = self.node.send_response
        
        
        # Register nodes in the graph
        self.graph.add_node("classifier", classifier)
        self.graph.add_node("summarizer", summarizer)
        self.graph.add_node("interrupts_handler", interrupts_handler)
        self.graph.add_node("writer", writer)
        self.graph.add_node("send_response", send_response)
        
        # Set entry point
        self.graph.set_entry_point("classifier")
        
        # Connecting nodes
        self.graph.add_conditional_edges(
            "classifier", lambda state: state["decision"],
            {"notify": "summarizer", "ignore": END}
        )
        
        self.graph.add_edge("summarizer", "interrupts_handler")
        self.graph.add_conditional_edges(
            "interrupts_handler", lambda state: state["interrupt_decision"],
            {"response": "writer", "ignore": END}
        )

        
        self.graph.add_edge("writer", "send_response")
        self.graph.add_conditional_edges(
            "send_response", lambda state: state["send_decision"],
            {"response": END, "rewrite": "writer", "error": END}
        )

        
        # Compile with checkpointer
        workflow = self.graph.compile(checkpointer= self.checkpointer)
        return workflow
    
if "__main__" == __name__:
    workflow_instance = EmailResponseWorkflow(model="gpt-4o-mini", db_path= "db/workflows.json")
    workflow = workflow_instance.workflow