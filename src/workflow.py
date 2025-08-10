from src.nodes import Nodes
from src.states import State
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from dotenv import load_dotenv

try:
    load_dotenv()
except Exception as e:
    print(f"Error in loading .env")

class Workflow:
    def __init__(self, model, db_path: str):
        self.Node = Nodes(model)
        self.graph = StateGraph(State)
        
        self.db_path = db_path
        self.checkpointer = self._initialize_checkpointer()
        self.get_workflow = self._create_workflow()
        

    def _initialize_checkpointer(self):
        """Initialize SQLite checkpointer for persistence"""
        try:
            # Validate db_paths
            if not self.db_path:
                print(f"ERROR: db_path is None or empty")
                return None
            
            # Create connection to SQLite database
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            
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

                
    def _create_workflow(self): 
        # Bind node methods
        classifier         = self.Node.classifier
        summarizer         = self.Node.summarizer
        interrupts_handler = self.Node.interrupts_handler
        writer             = self.Node.writer
        send_response      = self.Node.send_response
        
        
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
            {"response": END, "rewrite": "writer"}
        )

        
        # Compile with checkpointer
        workflow = self.graph.compile(checkpointer= self.checkpointer)
        return workflow
    
  
  
if "__main__" == __name__:

    workflow_instance = Workflow(model="gpt-4o-mini")
    workflow = workflow_instance.workflow
    