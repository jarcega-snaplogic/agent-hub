import streamlit as st
import json
import graphviz
import base64
from pymongo import MongoClient

# Configure the page to use wide layout
st.set_page_config(layout="wide")

st.title("LLM Agent Hub")

# MongoDB connection string
MONGO_URI = "mongodb+srv://jocelynarcega:PVnDsfN4XnOYv0CX@taletime.s8dtl.mongodb.net/?retryWrites=true&w=majority&appName=taletime"

# Initialize MongoDB client
client = MongoClient(MONGO_URI)
db = client.get_database("audiobooks")
history_collection = db.get_collection("Log")

# Fetch all session IDs
all_sessions = list(history_collection.distinct("sessionId"))
if not all_sessions:
    st.warning("No sessions found in the database.")
    history = []
else:
    # Initialize session selection
    session_start_index = 0
    session_end_index = 10
    
    # Sidebar for session selection
    st.sidebar.header("Session Selection")
    
    # Navigation buttons
    col1, col2 = st.sidebar.columns(2)
    if col1.button("Previous 10"):
        session_start_index = max(0, session_start_index - 10)
        session_end_index = max(10, session_end_index - 10)
    if col2.button("Next 10"):
        session_start_index = min(len(all_sessions), session_start_index + 10)
        session_end_index = min(len(all_sessions), session_end_index + 10)
    
    # Display session IDs in a selectbox
    current_sessions = all_sessions[session_start_index:session_end_index]
    selected_session = st.sidebar.selectbox(
        "Select Session",
        current_sessions,
        index=0,
        format_func=lambda x: f"Session ID: {x}"
    )
    
    # Fetch execution history from MongoDB for the selected session
    history = list(history_collection.find({"sessionId": selected_session}).limit(1))
    if history:
        history = history[0].get("messages", [])
    else:
        history = []

@st.cache_data
def generate_graph(history, scale=1.0):
    # Create graph with improved styling
    graph = graphviz.Digraph(
        graph_attr={
            "rankdir": "TB",  # Top to bottom layout
            "splines": "polyline",  # Clean, straight edges with bends
            "nodesep": f"{0.5 * scale}",  # Horizontal space between nodes
            "ranksep": f"{0.4 * scale}",  # Vertical space between ranks
            "fontname": "Arial",
            "bgcolor": "white"
        },
        node_attr={
            "fontname": "Arial",
            "fontsize": "11",
            "margin": "0.2"
        }
    )

    # Track nodes and relationships
    last_assistant_node = None
    tool_nodes = {}  # Map function_id to node_id
    current_tool_responses = []

    for i, message in enumerate(history):
        if not isinstance(message, dict):
            continue

        node_id = f"message_{i}"
        
        if message.get("sl_role") in ["SYSTEM", "USER"]:
            # Create system or user message nodes
            graph.node(node_id,
                       label=message["sl_role"],
                       shape="rectangle",
                       style="rounded,filled",
                       fillcolor="#E3F2FD",
                       color="#1565C0")
            
        elif message.get("role") == "assistant":
            # Connect any pending tool responses to this assistant
            for response in current_tool_responses:
                graph.edge(response, node_id)
            current_tool_responses = []

            # Create assistant node with tool calls list if present
            if message.get("tool_calls"):
                tool_calls = message["tool_calls"]
                tool_calls_text = ["Assistant"]
                for tool_call in tool_calls:
                    tool_calls_text.append(f"• {tool_call['function']['name']}")
                label = "\n".join(tool_calls_text)
            else:
                label = "Assistant"

            graph.node(node_id,
                       label=label,
                       shape="rectangle",
                       style="rounded,filled",
                       fillcolor="#FFF3E0",
                       color="#E65100")
            
            # Create tool nodes for this assistant's tool calls
            if message.get("tool_calls"):
                with graph.subgraph() as s:
                    s.attr(rank='same')  # Keep tools at same rank for parallel layout
                    for tool_call in message["tool_calls"]:
                        tool_node_id = f"tool_{tool_call['id']}"
                        tool_name = tool_call['function']['name']
                        s.node(tool_node_id,
                               label=tool_name,
                               shape="hexagon",
                               style="filled",
                               fillcolor="#F3E5F5",
                               color="#6A1B9A")
                        graph.edge(node_id, tool_node_id)
                        tool_nodes[tool_call['id']] = tool_node_id
            
            last_assistant_node = node_id
            
        elif message.get("sl_role") == "TOOL":
            # Track tool responses to connect to next assistant
            if message.get("function_id") and message["function_id"] in tool_nodes:
                current_tool_responses.append(tool_nodes[message["function_id"]])

    # Handle any remaining tool responses at end of flow
    if current_tool_responses and last_assistant_node:
        for response in current_tool_responses:
            graph.edge(response, last_assistant_node)

    return graph

def get_graph_source(graph):
    """Get the DOT source code for the graph."""
    return graph.source

# Create sidebar controls
st.sidebar.header("Graph Controls")
graph_scale = st.sidebar.slider("Graph Scale", min_value=0.5, max_value=2.0, value=1.0, step=0.1)

# Add download button for DOT source - visible at all times
# The download button should be in the sidebar
dot_source = get_graph_source(generate_graph(history, scale=graph_scale))
st.sidebar.download_button(
    label="Download Graph Source (DOT)",
    data=dot_source,
    file_name="agent_flow.dot",
    mime="text/plain"
)
# Add link to Graphviz website
st.sidebar.markdown("[Graphviz Online Viewer](https://dreampuf.github.io/GraphvizOnline/)")

# Display the header and the checkbox above the graph
st.header("Agent Flow Graph")
show_graph = st.checkbox("Show Graph", value=False)  # Now unchecked by default

# Generate and display the graph only if the checkbox is checked
if show_graph:
    graph = generate_graph(history, scale=graph_scale)
    st.graphviz_chart(graph, use_container_width=True)

# Display execution history
st.header("Execution History")

# Add functionality for filtering messages by role
selected_roles = st.multiselect(
    "Filter by Role",
    ["system", "user", "assistant", "tool"],
    default=["system", "user", "assistant", "tool"]
)
selected_roles_lower = [role.lower() for role in selected_roles]

simplify_assistant_messages = st.checkbox("Simplify Assistant Messages with Tool Calls", value=True) # Checked by default

# Filter history based on selected roles
filtered_history = []
for message in history:
    if isinstance(message, dict):
        if "tool_calls" in message and "tool" in selected_roles_lower:
            filtered_history.append(message)
        elif message.get("role", "").lower() in selected_roles_lower or \
                message.get("sl_role", "").lower() in selected_roles_lower:
            filtered_history.append(message)

# Display filtered history with expandable sections
if filtered_history:    
    for i, message in enumerate(filtered_history):
        role = message.get('role', message.get('sl_role', 'Output')) \
                if isinstance(message, dict) else 'Output'
        if message.get("tool_calls"):
            role += " (tool call)"
            
        with st.expander(f"Message {i + 1} - {role}"):
            if simplify_assistant_messages and \
                message.get("tool_calls") and \
                (message.get("role", "").lower() == "assistant" or \
                 message.get("sl_role", "").lower() == "assistant"):
                st.json(message, expanded=False)
            else:
                st.json(message)
                
            if message.get("tool_calls"):
                st.subheader("Tool Calls")
                for tool_call in message["tool_calls"]:
                    st.write(f"**Function:** {tool_call.get('function', {}).get('name', 'N/A')}")
                    arguments = tool_call.get('function', {}).get('arguments', 'N/A')
                    st.json(arguments, expanded=True)
else:
    st.info("No messages match the selected filter.")

# Future features:
# - Allow users to step through the execution history
# - Integrate with different LLM providers
