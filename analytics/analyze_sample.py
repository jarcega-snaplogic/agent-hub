import json
from collections import Counter
from datetime import datetime

# Read the sample log file
with open('sampleLog.json', 'r') as f:
    data = json.load(f)

print("="*80)
print("Sample Log Analysis")
print("="*80)

# Check if it's a single document or array
if isinstance(data, dict):
    print("\nData type: Single document")
    print(f"\nDocument keys: {list(data.keys())}")

    # Display metadata
    if "sessionId" in data:
        print(f"\nSession ID: {data['sessionId']}")
    if "agentName" in data:
        print(f"Agent Name: {data['agentName']}")
    if "sfdcUserId" in data:
        print(f"SFDC User ID: {data['sfdcUserId']}")

    # Analyze messages
    if "messages" in data:
        messages = data["messages"]
        print(f"\nTotal messages: {len(messages)}")

        # Count roles
        roles = []
        sl_roles = []
        tool_calls_count = 0
        tool_responses_count = 0

        for msg in messages:
            if isinstance(msg, dict):
                if "role" in msg:
                    roles.append(msg.get("role"))
                if "sl_role" in msg:
                    sl_roles.append(msg.get("sl_role"))
                if msg.get("tool_calls"):
                    tool_calls_count += len(msg["tool_calls"])

                # Check for tool responses
                content = msg.get("content", [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("toolResult"):
                            tool_responses_count += 1

        print(f"\n--- Message Role Distribution ---")
        for role, count in Counter(roles).most_common():
            print(f"  {role}: {count}")

        if sl_roles:
            print(f"\n--- SL_Role Distribution ---")
            for role, count in Counter(sl_roles).most_common():
                print(f"  {role}: {count}")

        print(f"\nTool calls: {tool_calls_count}")
        print(f"Tool responses: {tool_responses_count}")

        # Show first few messages
        print(f"\n--- First 3 Messages ---")
        for i, msg in enumerate(messages[:3]):
            print(f"\nMessage {i+1}:")
            print(f"  Role: {msg.get('role', 'N/A')}")
            print(f"  SL_Role: {msg.get('sl_role', 'N/A')}")

            content = msg.get("content")
            if isinstance(content, str):
                preview = content[:200] if len(content) > 200 else content
                print(f"  Content: {preview}...")
            elif isinstance(content, list):
                print(f"  Content type: list with {len(content)} items")
                if content and isinstance(content[0], dict):
                    print(f"    First item keys: {list(content[0].keys())}")

            if msg.get("tool_calls"):
                print(f"  Tool calls: {len(msg['tool_calls'])}")
                for tc in msg["tool_calls"][:2]:
                    print(f"    - {tc.get('function', {}).get('name', 'N/A')}")

        # Analyze tool usage
        tool_names = []
        for msg in messages:
            if isinstance(msg, dict):
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        tool_names.append(tc.get('function', {}).get('name', 'Unknown'))

                # Check for SnapLogic style tool calls
                content = msg.get("content", [])
                if isinstance(content, list) and len(content) > 1:
                    for item in content:
                        if isinstance(item, dict) and item.get("toolUse"):
                            tool_names.append(item["toolUse"].get("name", "Unknown"))

        if tool_names:
            print(f"\n--- Tool Usage Statistics ---")
            for tool, count in Counter(tool_names).most_common(10):
                print(f"  {tool}: {count}")

elif isinstance(data, list):
    print(f"\nData type: Array with {len(data)} documents")

    if data:
        print(f"\nFirst document keys: {list(data[0].keys())}")

        # Aggregate statistics
        all_agents = []
        all_sessions = []

        for doc in data:
            if "agentName" in doc:
                all_agents.append(doc["agentName"])
            if "sessionId" in doc:
                all_sessions.append(doc["sessionId"])

        print(f"\nUnique agents: {len(set(all_agents))}")
        print(f"Unique sessions: {len(set(all_sessions))}")

        if all_agents:
            print(f"\n--- Agent Distribution ---")
            for agent, count in Counter(all_agents).most_common():
                print(f"  {agent}: {count}")

print("\n" + "="*80)
print("Analysis complete!")
