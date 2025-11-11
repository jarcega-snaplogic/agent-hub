import streamlit as st
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from collections import Counter
import pymongo

# Load environment variables
load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")

st.title("SnapLogic Database Analysis")

try:
    client = MongoClient(MONGO_URI)
    db = client.get_database("snaplogic")
    collection = db.get_collection("Log")

    # Get total count
    total_count = collection.count_documents({})

    st.header(f"Total Documents: {total_count}")

    if total_count > 0:
        # Date range
        oldest = list(collection.find().sort("_id", 1).limit(1))[0]
        newest = list(collection.find().sort("_id", -1).limit(1))[0]

        oldest_time = oldest['_id'].generation_time
        newest_time = newest['_id'].generation_time

        st.subheader("Date Range")
        st.write(f"Oldest: {oldest_time}")
        st.write(f"Newest: {newest_time}")
        st.write(f"Span: {(newest_time - oldest_time).days} days")

        # Recent activity
        two_weeks_ago = datetime.utcnow() - timedelta(days=14)
        recent_count = collection.count_documents({
            "_id": {"$gte": pymongo.objectid.ObjectId.from_datetime(two_weeks_ago)}
        })

        st.subheader("Recent Activity (Last 2 Weeks)")
        st.write(f"Sessions: {recent_count}")
        st.write(f"Average per day: {recent_count / 14:.1f}")

        # Agents
        st.subheader("Agent Distribution")
        agent_names = collection.distinct("agentName")
        st.write(f"Total distinct agents: {len(agent_names)}")

        agent_stats = []
        for agent in agent_names:
            count = collection.count_documents({"agentName": agent})
            agent_stats.append((agent if agent else "(no agent)", count))

        agent_stats.sort(key=lambda x: x[1], reverse=True)
        st.dataframe(agent_stats, column_config={
            "0": "Agent Name",
            "1": "Session Count"
        })

        # Users
        st.subheader("User Authentication")
        docs_with_sfdc = collection.count_documents({"sfdcUserId": {"$exists": True, "$ne": None}})
        st.write(f"Authenticated sessions: {docs_with_sfdc}")
        st.write(f"Unauthenticated: {total_count - docs_with_sfdc}")

        # Tool usage
        st.subheader("Tool Usage Analysis (Last 50 Sessions)")
        recent_docs = list(collection.find({}).sort("_id", -1).limit(50))

        tool_counter = Counter()
        for doc in recent_docs:
            if "messages" in doc:
                for msg in doc["messages"]:
                    if isinstance(msg, dict):
                        if msg.get("tool_calls"):
                            for tc in msg["tool_calls"]:
                                tool_name = tc.get("function", {}).get("name")
                                if tool_name:
                                    tool_counter[tool_name] += 1

        if tool_counter:
            st.write(f"Total tool invocations: {sum(tool_counter.values())}")
            st.write(f"Unique tools: {len(tool_counter)}")

            tool_data = [(tool, count) for tool, count in tool_counter.most_common(20)]
            st.dataframe(tool_data, column_config={
                "0": "Tool Name",
                "1": "Usage Count"
            })

except Exception as e:
    st.error(f"Error: {e}")
    import traceback
    st.code(traceback.format_exc())
