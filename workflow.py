from nodes import Nodes
from states import State
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from graphviz import Source

from IPython.display import Image



import os
from dotenv import load_dotenv

load_dotenv()



class Workflow:
    def __init__(self, model):
        # Note: fixed spelling from `checkpoiter` to `checkpointer`
        self.Node = Nodes(model)
        self.graph = StateGraph(State)
        # self.checkpointer = MemorySaver()
        
        self.workflow = self._create_workflow()

    def save_graph(self, path: str = "workflow.png") -> None:
            """
            Dump the Mermaid‑based PNG to a file so you can open it in your OS.
            """
            png_bytes = self.workflow.get_graph().draw_mermaid_png()
            with open(path, "wb") as f:
                f.write(png_bytes)
            print(f"Workflow graph saved to {path}")
                
    def _create_workflow(self):
        # Bind your node methods
        classifier         = self.Node.classifer
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
        
        # Declare all valid transitions (including “ignore” branches to END)
        self.graph.add_edge("classifier",         "summarizer")
        self.graph.add_edge("classifier",         END)
        
        self.graph.add_edge("summarizer",         "interrupts_handler")
        
        self.graph.add_edge("interrupts_handler", "writer")
        self.graph.add_edge("interrupts_handler",  END)
        
        self.graph.add_edge("writer",             "send_response")
        self.graph.add_edge("send_response",      "writer")
        self.graph.add_edge("send_response",      END)

        
        # Entry point
        self.graph.set_entry_point("classifier")
        
        # Compile with checkpointer
        workflow = self.graph.compile()
        return workflow
    
  

workflow_instance = Workflow(model="gpt-4o-mini")
workflow = workflow_instance.workflow