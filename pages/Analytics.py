import streamlit as st
import pymongo
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from collections import Counter
import pandas as pd

st.set_page_config(layout="wide")

st.title("📊 Database Analytics")

# Load environment variables
load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")

try:
    client = MongoClient(MONGO_URI)

    # Database selection
    selected_db = st.selectbox("Select Database", ["snaplogic", "audiobooks"])

    db = client.get_database(selected_db)
    collection = db.get_collection("Log")

    # Get total count
    total_count = collection.count_documents({})

    # Overview metrics
    st.header("📈 Overview")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Sessions", f"{total_count:,}")

    if total_count > 0:
        # Date range
        oldest = list(collection.find().sort("_id", 1).limit(1))[0]
        newest = list(collection.find().sort("_id", -1).limit(1))[0]

        oldest_time = oldest['_id'].generation_time
        newest_time = newest['_id'].generation_time
        span_days = (newest_time - oldest_time).days

        with col2:
            st.metric("Date Range", f"{span_days} days")

        with col3:
            # Recent activity
            two_weeks_ago = datetime.utcnow() - timedelta(days=14)
            recent_count = collection.count_documents({
                "_id": {"$gte": pymongo.objectid.ObjectId.from_datetime(two_weeks_ago)}
            })
            st.metric("Last 14 Days", f"{recent_count} sessions")

        st.write(f"**Oldest session:** {oldest_time.strftime('%Y-%m-%d %H:%M:%S')}")
        st.write(f"**Newest session:** {newest_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Agent Distribution
        st.header("🤖 Agent Distribution")
        agent_names = collection.distinct("agentName")

        if agent_names:
            agent_stats = []
            for agent in agent_names:
                count = collection.count_documents({"agentName": agent})
                agent_stats.append({
                    "Agent Name": agent if agent else "(no agent name)",
                    "Session Count": count,
                    "Percentage": f"{(count / total_count * 100):.1f}%"
                })

            agent_stats.sort(key=lambda x: x["Session Count"], reverse=True)
            agent_df = pd.DataFrame(agent_stats)

            st.dataframe(agent_df, use_container_width=True, hide_index=True)

            # Bar chart
            st.bar_chart(agent_df.set_index("Agent Name")["Session Count"])
        else:
            st.info("No agent names found in the database.")

        # User Authentication
        st.header("👤 User Authentication")
        docs_with_sfdc = collection.count_documents({"sfdcUserId": {"$exists": True, "$ne": None}})
        docs_without_sfdc = total_count - docs_with_sfdc

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Authenticated Sessions", f"{docs_with_sfdc:,}")
        with col2:
            st.metric("Unauthenticated Sessions", f"{docs_without_sfdc:,}")

        if docs_with_sfdc > 0:
            sfdc_users = collection.distinct("sfdcUserId", {"sfdcUserId": {"$exists": True, "$ne": None}})
            st.write(f"**Unique SFDC Users:** {len(sfdc_users)}")

            # Top users
            user_stats = []
            for user in sfdc_users:
                if user:
                    count = collection.count_documents({"sfdcUserId": user})
                    user_stats.append({
                        "User ID": user,
                        "Sessions": count
                    })

            user_stats.sort(key=lambda x: x["Sessions"], reverse=True)
            user_df = pd.DataFrame(user_stats[:10])

            st.subheader("Top 10 Users")
            st.dataframe(user_df, use_container_width=True, hide_index=True)

        # Tool Usage Analysis
        st.header("🔧 Tool Usage Analysis")

        # Let user select how many sessions to analyze
        sample_size = st.slider("Number of recent sessions to analyze", 10, 200, 50, 10)

        with st.spinner(f"Analyzing tool usage in last {sample_size} sessions..."):
            recent_docs = list(collection.find({}).sort("_id", -1).limit(sample_size))

            tool_counter = Counter()
            total_messages = 0
            sessions_with_tools = 0

            for doc in recent_docs:
                if "messages" in doc:
                    total_messages += len(doc["messages"])
                    has_tools = False

                    for msg in doc["messages"]:
                        if isinstance(msg, dict):
                            # OpenAI format
                            if msg.get("tool_calls"):
                                has_tools = True
                                for tc in msg["tool_calls"]:
                                    tool_name = tc.get("function", {}).get("name")
                                    if tool_name:
                                        tool_counter[tool_name] += 1

                            # Anthropic format
                            content = msg.get("content", [])
                            if isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict) and item.get("toolUse"):
                                        has_tools = True
                                        tool_name = item["toolUse"].get("name")
                                        if tool_name:
                                            tool_counter[tool_name] += 1

                    if has_tools:
                        sessions_with_tools += 1

            if tool_counter:
                total_tools = sum(tool_counter.values())

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Tool Calls", f"{total_tools:,}")
                with col2:
                    st.metric("Unique Tools", len(tool_counter))
                with col3:
                    st.metric("Sessions with Tools", f"{sessions_with_tools}/{sample_size}")

                # Tool frequency table
                tool_data = []
                for tool, count in tool_counter.most_common(20):
                    percentage = (count / total_tools * 100)
                    tool_data.append({
                        "Tool Name": tool,
                        "Usage Count": count,
                        "Percentage": f"{percentage:.1f}%"
                    })

                tool_df = pd.DataFrame(tool_data)

                st.subheader(f"Top 20 Tools (from {sample_size} sessions)")
                st.dataframe(tool_df, use_container_width=True, hide_index=True)

                # Bar chart
                st.bar_chart(tool_df.set_index("Tool Name")["Usage Count"])
            else:
                st.info("No tool usage found in the analyzed sessions.")

        # Message Statistics
        st.header("💬 Message Statistics")

        if total_messages > 0:
            avg_messages = total_messages / len(recent_docs)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Avg Messages per Session", f"{avg_messages:.1f}")
            with col2:
                st.metric("Sessions with Tools", f"{(sessions_with_tools / len(recent_docs) * 100):.1f}%")

        # Recent Sessions
        st.header("📅 Recent Sessions")

        recent_sessions = list(collection.find({}, {
            "sessionId": 1,
            "agentName": 1,
            "sfdcUserId": 1,
            "messages": 1,
            "_id": 1
        }).sort("_id", -1).limit(20))

        session_data = []
        for session in recent_sessions:
            timestamp = session['_id'].generation_time
            session_data.append({
                "Timestamp": timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                "Session ID": session.get('sessionId', 'N/A')[:30] + "...",
                "Agent": session.get('agentName', 'N/A'),
                "User": session.get('sfdcUserId', 'N/A'),
                "Messages": len(session.get('messages', []))
            })

        sessions_df = pd.DataFrame(session_data)
        st.dataframe(sessions_df, use_container_width=True, hide_index=True)

    else:
        st.warning("No data found in this database.")

except Exception as e:
    st.error(f"❌ Error connecting to database: {e}")
    with st.expander("Show error details"):
        import traceback
        st.code(traceback.format_exc())
