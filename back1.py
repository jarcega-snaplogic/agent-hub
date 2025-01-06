import streamlit as st
import json
import graphviz

st.set_page_config(layout="wide")

st.title("LLM Agent Hub")

# Load execution history from sampleLog.json
with open("sampleLog.json", "r", encoding="latin-1") as f:
    data = json.load(f)
    history = data.get("messages", [])

# @st.cache_data
# def generate_graph(history):
#     # Visualize decision-making process (dynamically generated graphviz graph)
#     graph = graphviz.Digraph(graph_attr={"rankdir": "LR"}, node_attr={"shape": "square"})

#     graph = graphviz.Digraph(graph_attr={"rankdir": "LR"}, node_attr={"shape": "square"})

#     last_node = None
#     rank_nodes = {"user_system": [], "tool_assistant": []}
#     current_rank = "user_system"
#     max_nodes_per_rank = 4

#     for i, message in enumerate(history):
#         if isinstance(message, dict) and message.get("tool_calls"):
#             current_rank = "tool_assistant"
#             for j, tool_call in enumerate(message["tool_calls"]):
#                 tool_name = tool_call['function']['name']
#                 arguments = tool_call['function'].get('arguments', '')
#                 tool_call_node = f"{tool_name}_{i}_{j}"
#                 graph.node(tool_call_node, label=f"{tool_name}\\n{arguments}")
#                 if last_node:
#                     graph.edge(last_node, tool_call_node)
#                 last_node = tool_call_node
#                 rank_nodes[current_rank].append(tool_call_node)

#         role = message.get('role', message.get('sl_role', 'Output')) if isinstance(message, dict) else 'Output'
#         content = message.get('content', '') if isinstance(message, dict) else message
#         role_node = f"{role}_{i}"
#         graph.node(role_node, label=f"{role}\\n{content}")
#         if last_node:
#             graph.edge(last_node, role_node)
#         last_node = role_node
#         if role in ("user", "system"):
#             current_rank = "user_system"
#             rank_nodes[current_rank].append(role_node)
#         else:
#             current_rank = "tool_assistant"
#             rank_nodes[current_rank].append(role_node)


#     for rank, nodes in rank_nodes.items():
#         for i in range(0, len(nodes), max_nodes_per_rank):
#             group = nodes[i:i + max_nodes_per_rank]
#             with graph.subgraph() as s:
#                 s.attr(rank='same')
#                 for n in group:
#                     s.node(n)

#     # Initialize last_node for the first time
#     if rank_nodes["user_system"]:
#         last_node = rank_nodes["user_system"][0]
#     elif rank_nodes["tool_assistant"]:
#         last_node = rank_nodes["tool_assistant"][0]


#     return graph

# graph = generate_graph(history)

# st.graphviz_chart(graph)

st.header("Execution History")

# Add functionality for filtering messages by role (system, user, assistant, tool)
selected_roles = st.multiselect("Filter by Role", ["system", "user", "assistant", "tool"], default=["system", "user", "assistant", "tool"])
selected_roles_lower = [role.lower() for role in selected_roles]

simplify_assistant_messages = st.checkbox("Simplify Assistant Messages with Tool Calls")

filtered_history = []
for message in history:
    if isinstance(message, dict):
        if "tool_calls" in message and "tool" in selected_roles_lower:
            filtered_history.append(message)
        elif message.get("role", "").lower() in selected_roles_lower or message.get("sl_role", "").lower() in selected_roles_lower:
            filtered_history.append(message)


# Display filtered history with tool calls and parameters
if filtered_history:    
    for i, message in enumerate(filtered_history):
        role = message.get('role', message.get('sl_role', 'Output')) if isinstance(message, dict) else 'Output'

def display_full_message(message, i, role):
    with st.expander(f"Message {i + 1} - {role}"):
        st.json(message)
        if message.get("tool_calls"):
            st.subheader("Tool Calls")
            for tool_call in message["tool_calls"]:
                st.write(f"**Function:** {tool_call.get('function', {}).get('name', 'N/A')}")
                st.write(f"**Arguments:** {tool_call.get('function', {}).get('arguments', 'N/A')}")

if filtered_history:    
    for i, message in enumerate(filtered_history):
        role = message.get('role', message.get('sl_role', 'Output')) if isinstance(message, dict) else 'Output'
        if message.get("tool_calls"):
            role += " (tool call)"
        with st.expander(f"Message {i + 1} - {role}"):
            if simplify_assistant_messages and message.get("tool_calls") and (message.get("role", "").lower() == "assistant" or message.get("sl_role", "").lower() == "assistant"):
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
