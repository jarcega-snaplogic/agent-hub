import pymongo
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from collections import Counter
import json

# Load environment variables
load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)

# Analyze both databases
databases = ["snaplogic", "audiobooks"]

for db_name in databases:
    print(f"\n{'='*80}")
    print(f"Database: {db_name}")
    print(f"{'='*80}")

    db = client.get_database(db_name)
    collection = db.get_collection("Log")

    # Get total count
    total_count = collection.count_documents({})
    print(f"\nTotal documents: {total_count}")

    if total_count == 0:
        print("No documents found in this database.")
        continue

    # Get date range
    try:
        oldest = list(collection.find().sort("_id", 1).limit(1))[0]
        newest = list(collection.find().sort("_id", -1).limit(1))[0]
        print(f"\nOldest document ID: {oldest['_id']}")
        print(f"Newest document ID: {newest['_id']}")

        # Try to get timestamps
        oldest_time = oldest['_id'].generation_time
        newest_time = newest['_id'].generation_time
        print(f"Date range: {oldest_time} to {newest_time}")
    except Exception as e:
        print(f"Could not determine date range: {e}")

    # Get last 2 weeks of data (based on _id timestamp)
    two_weeks_ago = datetime.utcnow() - timedelta(days=14)
    recent_docs = list(collection.find({
        "_id": {"$gte": pymongo.objectid.ObjectId.from_datetime(two_weeks_ago)}
    }))

    print(f"\nDocuments from last 2 weeks: {len(recent_docs)}")

    # Analyze agent names
    agent_names = collection.distinct("agentName")
    print(f"\nDistinct agent names ({len(agent_names)}):")
    for agent in sorted(agent_names):
        count = collection.count_documents({"agentName": agent})
        print(f"  - {agent}: {count} sessions")

    # Analyze session IDs
    session_ids = collection.distinct("sessionId")
    print(f"\nTotal unique sessions: {len(session_ids)}")

    # Check for sfdcUserId
    docs_with_sfdc = collection.count_documents({"sfdcUserId": {"$exists": True}})
    print(f"\nDocuments with sfdcUserId: {docs_with_sfdc}")

    if docs_with_sfdc > 0:
        sfdc_users = collection.distinct("sfdcUserId")
        print(f"Unique SFDC users: {len(sfdc_users)}")
        for user in sfdc_users[:10]:  # Show first 10
            count = collection.count_documents({"sfdcUserId": user})
            print(f"  - {user}: {count} sessions")

    # Analyze message structure
    print(f"\n--- Sample Document Structure ---")
    sample = list(collection.find().limit(1))[0]
    print(f"Document keys: {list(sample.keys())}")

    if "messages" in sample:
        messages = sample["messages"]
        print(f"\nTotal messages in sample: {len(messages)}")

        # Analyze message roles
        roles = []
        sl_roles = []
        for msg in messages:
            if isinstance(msg, dict):
                if "role" in msg:
                    roles.append(msg.get("role"))
                if "sl_role" in msg:
                    sl_roles.append(msg.get("sl_role"))

        print(f"\nMessage roles distribution:")
        for role, count in Counter(roles).most_common():
            print(f"  - {role}: {count}")

        if sl_roles:
            print(f"\nSL_role distribution:")
            for role, count in Counter(sl_roles).most_common():
                print(f"  - {role}: {count}")

        # Show sample message
        print(f"\n--- Sample Message ---")
        if messages and isinstance(messages[0], dict):
            print(json.dumps(messages[0], indent=2, default=str)[:500] + "...")

    # Recent activity (last 10 sessions)
    print(f"\n--- Last 10 Sessions ---")
    recent_sessions = list(collection.find({}, {
        "sessionId": 1,
        "agentName": 1,
        "sfdcUserId": 1,
        "_id": 1
    }).sort("_id", -1).limit(10))

    for i, session in enumerate(recent_sessions, 1):
        timestamp = session['_id'].generation_time
        agent = session.get('agentName', 'N/A')
        session_id = session.get('sessionId', 'N/A')
        user = session.get('sfdcUserId', 'N/A')
        print(f"{i}. {timestamp} | Agent: {agent} | Session: {session_id[:20]}... | User: {user}")

print("\n" + "="*80)
print("Analysis complete!")
