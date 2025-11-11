# Analytics Scripts

This folder contains analysis scripts for the MongoDB collections used by the Agent Hub application.

## Scripts

### `analyze_snaplogic.py`
Comprehensive analysis of the **snaplogic** database:
- Total document counts and date ranges
- Agent name distribution
- User authentication statistics (sfdcUserId)
- Message structure and role distribution
- Tool usage statistics and trends
- Recent session activity

**Usage:**
```bash
python analyze_snaplogic.py
```

### `analyze_data.py`
General MongoDB analysis for both databases (snaplogic and audiobooks):
- Basic document statistics
- Agent and session counts
- Sample message structure

### `analyze_sample.py`
Basic analysis of the `sampleLog.json` file to understand document structure.

### `detailed_analysis.py`
Deep dive into the `sampleLog.json` file:
- Message flow patterns
- Tool execution sequences
- Content type analysis
- Conversation flow visualization

## Requirements

These scripts require:
- MongoDB connection (via MONGO_URI in `.env`)
- Python packages: `pymongo`, `python-dotenv`
- Network access with DNS resolution for MongoDB Atlas

**Note:** The analysis scripts may not work in restricted network environments due to MongoDB SRV DNS lookup requirements. The Streamlit app handles this internally.

## Database Structure

Based on analysis of sample data:

### Collection: `Log`

Each document represents a single agent conversation session:

```json
{
  "_id": ObjectId,
  "sessionId": "uuid-string",
  "agentName": "string (optional)",
  "sfdcUserId": "string (optional)",
  "messages": [
    {
      "role": "system|user|assistant",
      "sl_role": "SYSTEM|USER|TOOL|ERROR",
      "content": "string or array",
      "tool_calls": [...],
      "function_id": "string"
    }
  ]
}
```

### Key Findings from Sample Data:

- **Session**: Children's storytelling agent
- **27 messages** total
- **13 tool invocations**
- **Tools used**:
  - `UpdateWorkingMemory` (54% of calls)
  - `CreateChapterContent` (23%)
  - `AnalyzeStoryPrompt`, `GenerateInitialContext`, `PlanStoryStructure`

### Message Types:

1. **SYSTEM** - Agent instructions
2. **USER** - User input
3. **assistant** - Agent responses (often with tool_calls)
4. **TOOL** - Tool execution results

The app supports both OpenAI and Anthropic message formats, with tool calls tracked through `tool_calls` arrays or `toolUse`/`toolResult` content objects.
