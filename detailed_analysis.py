import json
from collections import Counter, defaultdict
from datetime import datetime

# Read the sample log file
with open('sampleLog.json', 'r') as f:
    data = json.load(f)

print("="*80)
print("DETAILED MongoDB Collection Analysis")
print("="*80)

# Document structure
print(f"\nDocument keys: {list(data.keys())}")
print(f"\nSession ID: {data.get('sessionId', 'N/A')}")
print(f"Agent Name: {data.get('agentName', 'N/A')}")
print(f"SFDC User ID: {data.get('sfdcUserId', 'N/A')}")

messages = data.get("messages", [])
print(f"\nTotal messages in session: {len(messages)}")

# Deep analysis of messages
print("\n" + "="*80)
print("MESSAGE STRUCTURE ANALYSIS")
print("="*80)

roles = []
sl_roles = []
has_tool_calls = 0
has_content_list = 0
has_content_string = 0
has_tool_results = 0

# Track tool flows
tool_flow = []

for i, msg in enumerate(messages):
    if not isinstance(msg, dict):
        continue

    role = msg.get("role")
    sl_role = msg.get("sl_role")

    if role:
        roles.append(role)
    if sl_role:
        sl_roles.append(sl_role)

    # Check content type
    content = msg.get("content")
    if isinstance(content, list):
        has_content_list += 1
    elif isinstance(content, str):
        has_content_string += 1

    # Check for tool calls (OpenAI format)
    if msg.get("tool_calls"):
        has_tool_calls += 1
        for tc in msg["tool_calls"]:
            tool_name = tc.get("function", {}).get("name")
            tool_flow.append({
                "index": i,
                "type": "tool_call",
                "name": tool_name,
                "id": tc.get("id")
            })

    # Check for tool results (Claude/Anthropic format)
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                if item.get("toolResult"):
                    has_tool_results += 1
                    tool_flow.append({
                        "index": i,
                        "type": "tool_result",
                        "toolUseId": item["toolResult"].get("toolUseId")
                    })
                if item.get("toolUse"):
                    tool_flow.append({
                        "index": i,
                        "type": "tool_use",
                        "name": item["toolUse"].get("name"),
                        "toolUseId": item["toolUse"].get("toolUseId")
                    })

print(f"\nRole distribution:")
for role, count in Counter(roles).most_common():
    print(f"  {role}: {count}")

print(f"\nSL_Role distribution:")
for role, count in Counter(sl_roles).most_common():
    print(f"  {role}: {count}")

print(f"\nContent types:")
print(f"  String content: {has_content_string}")
print(f"  List content: {has_content_list}")

print(f"\nTool interaction counts:")
print(f"  Messages with tool_calls: {has_tool_calls}")
print(f"  Tool results found: {has_tool_results}")

# Show conversation flow
print("\n" + "="*80)
print("CONVERSATION FLOW (First 10 messages)")
print("="*80)

for i, msg in enumerate(messages[:10]):
    if not isinstance(msg, dict):
        continue

    role = msg.get("role", "N/A")
    sl_role = msg.get("sl_role", "N/A")
    content = msg.get("content", "")

    print(f"\n[{i+1}] Role: {role} | SL_Role: {sl_role}")

    # Show content preview
    if isinstance(content, str):
        preview = content[:150].replace("\n", " ")
        print(f"    Content: {preview}...")
    elif isinstance(content, list):
        print(f"    Content: [list with {len(content)} items]")
        for j, item in enumerate(content[:2]):
            if isinstance(item, dict):
                if item.get("text"):
                    text_preview = item["text"][:100].replace("\n", " ")
                    print(f"      [{j}] text: {text_preview}...")
                elif item.get("toolUse"):
                    print(f"      [{j}] toolUse: {item['toolUse'].get('name')}")
                elif item.get("toolResult"):
                    print(f"      [{j}] toolResult for: {item['toolResult'].get('toolUseId', 'N/A')[:20]}...")

    # Show tool calls
    if msg.get("tool_calls"):
        print(f"    Tool calls:")
        for tc in msg["tool_calls"]:
            print(f"      - {tc.get('function', {}).get('name')} (id: {tc.get('id', 'N/A')[:20]}...)")

# Tool usage analysis
print("\n" + "="*80)
print("TOOL USAGE ANALYSIS")
print("="*80)

tool_names = []
for msg in messages:
    if isinstance(msg, dict):
        # OpenAI format
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                tool_names.append(tc.get('function', {}).get('name', 'Unknown'))

        # Anthropic format
        content = msg.get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("toolUse"):
                    tool_names.append(item["toolUse"].get("name", "Unknown"))

print(f"\nTotal tool invocations: {len(tool_names)}")
print(f"\nTool usage frequency:")
for tool, count in Counter(tool_names).most_common():
    print(f"  {tool}: {count}")

# Show tool flow sequence
print("\n" + "="*80)
print("TOOL EXECUTION SEQUENCE")
print("="*80)
print("\nFirst 15 tool interactions:")
for i, tool in enumerate(tool_flow[:15]):
    idx = tool.get("index")
    if tool["type"] == "tool_call":
        print(f"  [{idx}] CALL: {tool.get('name')}")
    elif tool["type"] == "tool_use":
        print(f"  [{idx}] USE: {tool.get('name')}")
    elif tool["type"] == "tool_result":
        print(f"  [{idx}] RESULT returned")

# Additional metadata
print("\n" + "="*80)
print("ADDITIONAL INSIGHTS")
print("="*80)

# Find longest message
longest_content_len = 0
longest_msg_idx = -1
for i, msg in enumerate(messages):
    if isinstance(msg, dict):
        content = msg.get("content", "")
        if isinstance(content, str):
            if len(content) > longest_content_len:
                longest_content_len = len(content)
                longest_msg_idx = i

print(f"\nLongest message: #{longest_msg_idx + 1} with {longest_content_len} characters")

# Count messages with different attributes
messages_with_function_id = sum(1 for m in messages if isinstance(m, dict) and m.get("function_id"))
print(f"Messages with function_id: {messages_with_function_id}")

# Check for errors
error_messages = [m for m in messages if isinstance(m, dict) and (m.get("role") == "error" or m.get("sl_role") == "ERROR")]
print(f"Error messages: {len(error_messages)}")

print("\n" + "="*80)
print("Analysis complete!")
print("="*80)
