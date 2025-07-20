from src.nodes import Nodes
from src.states import State
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.utils import parse_email
from dotenv import load_dotenv


load_dotenv() 

class Workflow:
    def __init__(self, model):
        # Note: fixed spelling from `checkpoiter` to `checkpointer`
        self.Node = Nodes(model)
        self.graph = StateGraph(State)
        self.checkpointer = MemorySaver()
        self.get_workflow = self._create_workflow()
        
        self.category = {"decision": None}
        self.summary = {"summary": None}

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
    