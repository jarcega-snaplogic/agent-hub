import streamlit as st
import json
import graphviz
import base64
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Configure the page to use wide layout
st.set_page_config(layout="wide")

# Initialize session state variables
if 'selected_session' not in st.session_state:
    st.session_state.selected_session = None

# Initialize filter roles with default values
if 'filter_roles' not in st.session_state:
    st.session_state.filter_roles = ["system", "user", "assistant", "tool", "error"]

def update_filter_roles():
    st.session_state.filter_roles = st.session_state.role_multiselect

st.title("LLM Agent Hub")

# Load environment variables
load_dotenv()

# MongoDB connection string
MONGO_URI = os.getenv("MONGO_URI")

# Initialize MongoDB client
client = MongoClient(MONGO_URI)
db = client.get_database("audiobooks")
history_collection = db.get_collection("Log")

# Sidebar for database and session selection
st.sidebar.header("Database and Session Selection")

# Database selection dropdown
selected_database = st.sidebar.selectbox("Select Database", ["snaplogic", "audiobooks"], key="selected_database")

# Initialize selected session based on the database
if "selected_session" not in st.session_state or st.session_state.get("previous_database", None) != selected_database:
    st.session_state.selected_session = None
st.session_state.previous_database = selected_database

# MongoDB connection string
MONGO_URI = os.getenv("MONGO_URI")

# Initialize MongoDB client
client = MongoClient(MONGO_URI)
db = client.get_database(selected_database)
history_collection = db.get_collection("Log")

# Fetch distinct agent names
agent_names = sorted(list(set(history_collection.distinct("agentName"))))

# Fetch session IDs and agent names (up to 10 for initial display)
all_sessions = list(history_collection.find({}, {"sessionId": 1, "agentName": 1, "_id": 0}).sort("_id", -1).limit(10)) if not agent_names else []


# Search boxes for session ID and agent name
selected_agent = st.sidebar.selectbox("Filter by Agent Name", ["All"] + agent_names)
search_session_id = st.sidebar.text_input("Search Session ID")

def fetch_history(session_id):
    if session_id:
        history = list(history_collection.find({"sessionId": session_id}).limit(1))
        if history:
            return history[0].get("messages", [])
    return []

# Fetch sessions based on search input or get the last 10
if selected_agent != "All":
    all_sessions = list(history_collection.find({"agentName": selected_agent}, {"sessionId": 1, "agentName": 1, "_id": 0}))
elif search_session_id:
    all_sessions = list(history_collection.find({"sessionId": search_session_id}, {"sessionId": 1, "agentName": 1, "_id": 0}))
else:
    all_sessions = list(history_collection.find({}, {"sessionId": 1, "agentName": 1, "_id": 0}).sort("_id", -1).limit(10)) if not agent_names else []

# Display session IDs and agent names
if all_sessions:
    for i, session_data in enumerate(all_sessions):
        session_id = session_data.get("sessionId")
        agent_name = session_data.get("agentName")
        session_label = f"{session_id} ({agent_name})" if agent_name else session_id
        if st.sidebar.button(session_label, key=f"{session_id}_{i}"):  # Unique key
            st.session_state.selected_session = session_id
else:
    st.sidebar.info("No sessions found.")


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
    tool_names = {}  # Store tool names for each function ID

    for i, message in enumerate(history):
        if not isinstance(message, dict):
            continue
        i = i+1
        node_id = f"message_{i}"
        
        if message.get("sl_role") in ["SYSTEM", "USER"]:
            graph.node(node_id,
                       label=f"{message['sl_role']}\nID: {i}",
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
                tool_calls_text = [f"Assistant\nID: {i}"]
                for tool_call in tool_calls:
                    tool_calls_text.append(f"• {tool_call['function']['name']}")
                    # Store tool name for the function ID
                    tool_names[tool_call['id']] = tool_call['function']['name']
                label = "\n".join(tool_calls_text)
            else:
                label = f"Assistant\nID: {i}"

            graph.node(node_id,
                       label=label,
                       shape="rectangle",
                       style="rounded,filled",
                       fillcolor="#FFF3E0",
                       color="#E65100")
            
            if message.get("tool_calls"):
                with graph.subgraph() as s:
                    s.attr(rank='same')
                    y = 1
                    for tool_call in message["tool_calls"]:
                        tool_node_id = f"tool_{tool_call['id']}"
                        tool_name = tool_call['function']['name']
                        s.node(tool_node_id,
                               label=f"{tool_name}\nID: {i+y}",
                               shape="hexagon",
                               style="filled",
                               fillcolor="#F3E5F5",
                               color="#6A1B9A")
                        graph.edge(node_id, tool_node_id)
                        tool_nodes[tool_call['id']] = tool_node_id
                        y += 1

            last_assistant_node = node_id
            
        elif message.get("sl_role") == "TOOL":
            if message.get("function_id") and message["function_id"] in tool_nodes:
                current_tool_responses.append(tool_nodes[message["function_id"]])

    if current_tool_responses and last_assistant_node:
        for response in current_tool_responses:
            graph.edge(response, last_assistant_node)

    return graph, tool_names

def get_graph_source(graph):
    """Get the DOT source code for the graph."""
    return graph.source

# Create sidebar controls for graph
st.sidebar.header("Graph Controls")
graph_scale = st.sidebar.slider("Graph Scale", min_value=0.5, max_value=2.0, value=1.0, step=0.1)

# Main content area
if st.session_state.selected_session:
    st.markdown(f"Selected Session: **{st.session_state.selected_session}**")
    history = fetch_history(st.session_state.selected_session)
    
    # Fetch the session document to check for sfdcUserId
    session_doc = list(history_collection.find({"sessionId": st.session_state.selected_session}).limit(1))
    if session_doc and "sfdcUserId" in session_doc[0]:
        st.markdown(f"Authenticated User: **{session_doc[0]['sfdcUserId']}**")
    
    # Generate graph and get tool names
    graph, tool_names = generate_graph(history, scale=graph_scale)
    
    # Add download button for DOT source in sidebar
    if history:
        dot_source = get_graph_source(graph)
        st.sidebar.download_button(
            label="Download Graph Source (DOT)",
            data=dot_source,
            file_name="agent_flow.dot",
            mime="text/plain"
        )
    st.sidebar.markdown("[Graphviz Online Viewer](https://dreampuf.github.io/GraphvizOnline/)")
    
    # Graph section
    st.header("Agent Flow Graph")
    show_graph = st.checkbox("Show Graph", value=False)
    
    if show_graph:
        st.markdown(
            """
            <style>
                .graph-container {
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 1rem;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )
        
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.graphviz_chart(graph, use_container_width=True)

    # Execution History section
    st.header("Execution History")
    
    # Common filter control for both graph and history with improved state management
    selected_roles = st.multiselect(
        "Filter by Role",
        ["system", "user", "assistant", "tool", "error"],
        default=st.session_state.filter_roles,
        key="role_multiselect",
        on_change=update_filter_roles
    )
    
    simplify_assistant_messages = st.checkbox("Simplify Assistant Messages with Tool Calls", value=True)

    # Find tool names for TOOL messages
    tool_function_names = {}
    for i, message in enumerate(history):
        if isinstance(message, dict) and message.get("role") == "assistant" and message.get("tool_calls"):
            for tool_call in message["tool_calls"]:
                tool_function_names[tool_call["id"]] = tool_call["function"]["name"]

    # Corrected filtering logic
    selected_roles_lower = [role.lower() for role in selected_roles]
    filtered_history = []
    
    for message in history:
        if isinstance(message, dict):
            message_role = message.get("role", message.get("sl_role", "")).lower()
            
            # Regular role-based filtering
            if message_role in selected_roles_lower:
                filtered_history.append(message)
            # Tool-specific filtering
            elif message.get("sl_role") == "TOOL" and "tool" in selected_roles_lower:
                filtered_history.append(message)
            elif message.get("sl_role") == "ERROR" and "error" in selected_roles_lower:
                filtered_history.append(message)
            # Assistant messages with tool calls are only shown if both tool and assistant are selected
            elif message.get("tool_calls") and "tool" in selected_roles_lower and "assistant" in selected_roles_lower and message_role == "assistant":
                filtered_history.append(message)

    if filtered_history:
        for i, message in enumerate(filtered_history):
            role = message.get('role', message.get('sl_role', 'Output')) \
                    if isinstance(message, dict) else 'Output'
                    
            # Add tool name for TOOL messages
            tool_name = ""
            if role == "TOOL" and message.get("function_id"):
                tool_name = f" ({tool_function_names.get(message['function_id'], 'Unknown')})"
            
            if message.get("tool_calls"):
                role += " (tool call)"
                
            with st.expander(f"Message {i + 1} - {role}{tool_name}"):
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
