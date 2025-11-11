import pymongo
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from collections import Counter
import json
import sys

# Load environment variables
load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")

print("="*80)
print("SnapLogic Database Analysis")
print("="*80)

try:
    print("\nAttempting to connect to MongoDB...")
    # Add timeout and direct connection to handle DNS issues
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, directConnection=False)

    # Test connection
    client.admin.command('ping')
    print("✓ Successfully connected to MongoDB")

    db = client.get_database("snaplogic")
    collection = db.get_collection("Log")

    # Get total count
    total_count = collection.count_documents({})
    print(f"\nTotal documents: {total_count}")

    if total_count == 0:
        print("No documents found in this database.")
        sys.exit(0)

    # Get date range
    print("\n" + "="*80)
    print("DATE RANGE")
    print("="*80)
    try:
        oldest = list(collection.find().sort("_id", 1).limit(1))[0]
        newest = list(collection.find().sort("_id", -1).limit(1))[0]

        oldest_time = oldest['_id'].generation_time
        newest_time = newest['_id'].generation_time

        print(f"\nOldest session: {oldest_time}")
        print(f"Newest session: {newest_time}")
        print(f"Total span: {(newest_time - oldest_time).days} days")
    except Exception as e:
        print(f"Could not determine date range: {e}")

    # Get last 2 weeks of data
    print("\n" + "="*80)
    print("RECENT ACTIVITY (Last 2 Weeks)")
    print("="*80)

    two_weeks_ago = datetime.utcnow() - timedelta(days=14)
    recent_count = collection.count_documents({
        "_id": {"$gte": pymongo.objectid.ObjectId.from_datetime(two_weeks_ago)}
    })

    print(f"\nSessions in last 2 weeks: {recent_count}")
    print(f"Average per day: {recent_count / 14:.1f}")

    # Analyze agent names
    print("\n" + "="*80)
    print("AGENT DISTRIBUTION")
    print("="*80)

    agent_names = collection.distinct("agentName")
    print(f"\nTotal distinct agent names: {len(agent_names)}")
    print(f"\nAgent usage statistics:")

    agent_stats = []
    for agent in agent_names:
        count = collection.count_documents({"agentName": agent})
        agent_stats.append((agent, count))

    # Sort by count
    agent_stats.sort(key=lambda x: x[1], reverse=True)
    for agent, count in agent_stats:
        print(f"  - {agent if agent else '(no agent name)'}: {count} sessions")

    # Analyze session IDs
    session_ids = collection.distinct("sessionId")
    print(f"\nTotal unique sessions: {len(session_ids)}")

    # Check for sfdcUserId
    print("\n" + "="*80)
    print("USER AUTHENTICATION")
    print("="*80)

    docs_with_sfdc = collection.count_documents({"sfdcUserId": {"$exists": True, "$ne": None}})
    docs_without_sfdc = total_count - docs_with_sfdc

    print(f"\nAuthenticated sessions (with sfdcUserId): {docs_with_sfdc}")
    print(f"Unauthenticated sessions: {docs_without_sfdc}")

    if docs_with_sfdc > 0:
        sfdc_users = collection.distinct("sfdcUserId", {"sfdcUserId": {"$exists": True, "$ne": None}})
        print(f"\nUnique SFDC users: {len(sfdc_users)}")
        print(f"\nTop users by session count:")

        user_stats = []
        for user in sfdc_users:
            if user:
                count = collection.count_documents({"sfdcUserId": user})
                user_stats.append((user, count))

        user_stats.sort(key=lambda x: x[1], reverse=True)
        for user, count in user_stats[:10]:
            print(f"  - {user}: {count} sessions")

    # Analyze message structure and tool usage
    print("\n" + "="*80)
    print("MESSAGE STRUCTURE ANALYSIS")
    print("="*80)

    # Sample a few documents to understand message patterns
    sample_docs = list(collection.find().limit(10))

    total_messages = 0
    all_roles = []
    all_sl_roles = []
    all_tools = []
    sessions_with_tools = 0
    sessions_with_errors = 0

    for doc in sample_docs:
        if "messages" in doc:
            messages = doc["messages"]
            total_messages += len(messages)

            has_tools = False
            has_errors = False

            for msg in messages:
                if isinstance(msg, dict):
                    if msg.get("role"):
                        all_roles.append(msg.get("role"))
                    if msg.get("sl_role"):
                        all_sl_roles.append(msg.get("sl_role"))

                    # Check for errors
                    if msg.get("role") == "error" or msg.get("sl_role", "").upper() == "ERROR":
                        has_errors = True

                    # Check for tool calls
                    if msg.get("tool_calls"):
                        has_tools = True
                        for tc in msg["tool_calls"]:
                            tool_name = tc.get("function", {}).get("name")
                            if tool_name:
                                all_tools.append(tool_name)

                    # Check for anthropic style tool use
                    content = msg.get("content", [])
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("toolUse"):
                                has_tools = True
                                tool_name = item["toolUse"].get("name")
                                if tool_name:
                                    all_tools.append(tool_name)

            if has_tools:
                sessions_with_tools += 1
            if has_errors:
                sessions_with_errors += 1

    print(f"\nAnalyzed {len(sample_docs)} sample sessions")
    print(f"Average messages per session: {total_messages / len(sample_docs):.1f}")
    print(f"Sessions with tool usage: {sessions_with_tools}/{len(sample_docs)}")
    print(f"Sessions with errors: {sessions_with_errors}/{len(sample_docs)}")

    if all_roles:
        print(f"\nMessage role distribution (sample):")
        for role, count in Counter(all_roles).most_common():
            print(f"  - {role}: {count}")

    if all_sl_roles:
        print(f"\nSL_Role distribution (sample):")
        for role, count in Counter(all_sl_roles).most_common():
            print(f"  - {role}: {count}")

    if all_tools:
        print(f"\nTool usage (sample):")
        print(f"Total tool invocations: {len(all_tools)}")
        print(f"\nMost used tools:")
        for tool, count in Counter(all_tools).most_common(15):
            print(f"  - {tool}: {count}")

    # Recent sessions detail
    print("\n" + "="*80)
    print("LAST 20 SESSIONS")
    print("="*80)

    recent_sessions = list(collection.find({}, {
        "sessionId": 1,
        "agentName": 1,
        "sfdcUserId": 1,
        "messages": 1,
        "_id": 1
    }).sort("_id", -1).limit(20))

    for i, session in enumerate(recent_sessions, 1):
        timestamp = session['_id'].generation_time
        agent = session.get('agentName', 'N/A')
        session_id = session.get('sessionId', 'N/A')
        user = session.get('sfdcUserId', 'N/A')
        msg_count = len(session.get('messages', []))

        print(f"{i:2d}. {timestamp} | Messages: {msg_count:3d} | Agent: {agent:20s} | User: {user}")

    # Tool usage trends
    print("\n" + "="*80)
    print("DETAILED TOOL ANALYSIS (Last 50 sessions)")
    print("="*80)

    recent_for_tools = list(collection.find({}).sort("_id", -1).limit(50))
    tool_counter = Counter()
    total_tool_calls = 0

    for doc in recent_for_tools:
        if "messages" in doc:
            for msg in doc["messages"]:
                if isinstance(msg, dict):
                    # OpenAI format
                    if msg.get("tool_calls"):
                        for tc in msg["tool_calls"]:
                            tool_name = tc.get("function", {}).get("name")
                            if tool_name:
                                tool_counter[tool_name] += 1
                                total_tool_calls += 1

                    # Anthropic format
                    content = msg.get("content", [])
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("toolUse"):
                                tool_name = item["toolUse"].get("name")
                                if tool_name:
                                    tool_counter[tool_name] += 1
                                    total_tool_calls += 1

    print(f"\nTotal tool invocations: {total_tool_calls}")
    print(f"Unique tools used: {len(tool_counter)}")
    print(f"\nTool frequency:")
    for tool, count in tool_counter.most_common(20):
        percentage = (count / total_tool_calls * 100) if total_tool_calls > 0 else 0
        print(f"  {tool:40s}: {count:4d} ({percentage:5.1f}%)")

    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)

except pymongo.errors.ServerSelectionTimeoutError as e:
    print(f"\n✗ Failed to connect to MongoDB: {e}")
    print("\nNote: Connection timeout. This may be due to network restrictions.")
    print("The database is accessible via the Streamlit app which runs in a different environment.")
    sys.exit(1)
except Exception as e:
    print(f"\n✗ Error during analysis: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
