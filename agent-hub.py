import streamlit as st
import json
import graphviz
import base64
from pymongo import MongoClient

# Configure the page to use wide layout
st.set_page_config(layout="wide")

# Initialize session state variables
if 'selected_session' not in st.session_state:
    st.session_state.selected_session = None
if 'filter_roles' not in st.session_state:
    st.session_state.filter_roles = ["system", "user", "assistant", "tool"]

st.title("LLM Agent Hub")
if st.button("Show Start Command"):
    st.markdown("To start the app, run `streamlit run agent-hub.py` in your terminal.")

# MongoDB connection string
MONGO_URI = "mongodb+srv://jocelynarcega:PVnDsfN4XnOYv0CX@taletime.s8dtl.mongodb.net/?retryWrites=true&w=majority&appName=taletime"

# Initialize MongoDB client
client = MongoClient(MONGO_URI)
db = client.get_database("audiobooks")
history_collection = db.get_collection("Log")

def fetch_history(session_id):
    if session_id:
        history = list(history_collection.find({"sessionId": session_id}).limit(1))
        if history:
            return history[0].get("messages", [])
    return []

# Fetch all session IDs
all_sessions = list(history_collection.distinct("sessionId"))

# Sidebar for session selection
st.sidebar.header("Session Selection")

# Display session IDs in a table-like format with styling for the selected session
for session_id in all_sessions:
    if st.sidebar.button(session_id, key=session_id):
        st.session_state.selected_session = session_id

# Graph generation functions
@st.cache_data
def generate_graph(history, scale=1.0):
    # Create graph with improved styling
    graph = graphviz.Digraph(
        graph_attr={
            "rankdir": "TB",
            "splines": "polyline",
            "nodesep": f"{0.5 * scale}",
            "ranksep": f"{0.4 * scale}",
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
    tool_nodes = {}
    current_tool_responses = []

    for i, message in enumerate(history):
        if not isinstance(message, dict):
            continue

        node_id = f"message_{i}"
        
        if message.get("sl_role") in ["SYSTEM", "USER"]:
            graph.node(node_id,
                       label=message["sl_role"],
                       shape="rectangle",
                       style="rounded,filled",
                       fillcolor="#E3F2FD",
                       color="#1565C0")
            
        elif message.get("role") == "assistant":
            for response in current_tool_responses:
                graph.edge(response, node_id)
            current_tool_responses = []

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
            
            if message.get("tool_calls"):
                with graph.subgraph() as s:
                    s.attr(rank='same')
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
            if message.get("function_id") and message["function_id"] in tool_nodes:
                current_tool_responses.append(tool_nodes[message["function_id"]])

    if current_tool_responses and last_assistant_node:
        for response in current_tool_responses:
            graph.edge(response, last_assistant_node)

    return graph

def get_graph_source(graph):
    """Get the DOT source code for the graph."""
    return graph.source

# Create sidebar controls for graph
st.sidebar.header("Graph Controls")
graph_scale = st.sidebar.slider("Graph Scale", min_value=0.5, max_value=2.0, value=1.0, step=0.1)

# Add download button for DOT source in sidebar
if st.session_state.selected_session:
    history = fetch_history(st.session_state.selected_session)
    if history:
        dot_source = get_graph_source(generate_graph(history, scale=graph_scale))
        st.sidebar.download_button(
            label="Download Graph Source (DOT)",
            data=dot_source,
            file_name="agent_flow.dot",
            mime="text/plain"
        )
    st.sidebar.markdown("[Graphviz Online Viewer](https://dreampuf.github.io/GraphvizOnline/)")

# Main content area
if st.session_state.selected_session:
    st.markdown(f"Selected Session: **{st.session_state.selected_session}**")
    history = fetch_history(st.session_state.selected_session)
    
    # Common filter control for both graph and history
    selected_roles = st.multiselect(
        "Filter by Role",
        ["system", "user", "assistant", "tool"],
        default=st.session_state.filter_roles,
        key="filter_roles"
    )
    st.session_state.filter_roles = selected_roles
    
    # Graph section
    st.header("Agent Flow Graph")
    show_graph = st.checkbox("Show Graph", value=False)
    
    if show_graph:
        with st.container():
            st.markdown(
                """
                <style>
                    [data-testid="stVerticalBlock"] {
                        max-width: 800px;
                        margin: 0 auto;
                    }
                </style>
                """,
                unsafe_allow_html=True,
            )
            graph = generate_graph(history, scale=graph_scale)
            st.graphviz_chart(graph, use_container_width=True)

    # Execution History section
    st.header("Execution History")
    simplify_assistant_messages = st.checkbox("Simplify Assistant Messages with Tool Calls", value=True)

    # Filter and display history based on selected roles
    selected_roles_lower = [role.lower() for role in selected_roles]
    filtered_history = []
    
    for message in history:
        if isinstance(message, dict):
            if "tool_calls" in message and "tool" in selected_roles_lower:
                filtered_history.append(message)
            elif message.get("role", "").lower() in selected_roles_lower or \
                    message.get("sl_role", "").lower() in selected_roles_lower:
                filtered_history.append(message)

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
else:
    st.markdown("No session selected")

# Future features:
# - Allow users to step through the execution history
# - Integrate with different LLM providers
