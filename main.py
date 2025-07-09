from src.workflow import Workflow

workflow = Workflow(model=...)
graph = workflow._create_workflow()
config = ...


def main():
    # Infinite loop
    while True:     
        new_email = ... # email_alert() # If there is a new email flag True; otheriwse False
        if new_email:
            input_email = ... # a dictionary containing author, to, subject, email_thread, email_id
            graph.invoke(input_email, config= config)
        
        