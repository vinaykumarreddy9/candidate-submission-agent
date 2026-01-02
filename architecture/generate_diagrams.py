import os
import sys

# Appending project root to sys.path to resolve internal 'agent' module.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.graph import initialize_recruitment_workflow

def generate_graph_image():
    """
    Generates and saves the LangGraph architecture diagram as a PNG.
    """
    print("🚀 Initializing Recruitment Workflow...")
    app = initialize_recruitment_workflow()
    
    try:
        # Get the graph and generate PNG data
        print("📊 Drawing graph architecture...")
        png_data = app.get_graph().draw_mermaid_png()
        
        # Define output path
        output_path = os.path.join(os.path.dirname(__file__), "agent_architecture.png")
        
        # Save the binary data to a file
        with open(output_path, "wb") as f:
            f.write(png_data)
        
        print(f"✅ Success! Architecture diagram saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Error generating graph image: {e}")
        print("\nNote: This operation typically requires 'pygraphviz' or the 'mermaid.js' CLI.")
        print("If you are in a notebook environment, you can use: Display(Image(graph.get_graph().draw_mermaid_png()))")

if __name__ == "__main__":
    generate_graph_image()
