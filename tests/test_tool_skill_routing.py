import pytest

def test_tool_routing_intent_classification():
    user_prompt = "Find all documents mentioning quarterly earnings"
    tool_map = {
        "search_docs": ["find", "document", "search"],
        "calculator": ["calculate", "math", "sum"]
    }
    selected_tool = None
    for tool, keywords in tool_map.items():
        if any(kw in user_prompt.lower() for kw in keywords):
            selected_tool = tool
            break
            
    assert selected_tool == "search_docs"

def test_skill_execution_context_passing():
    skill_config = {"name": "summarizer", "owner_id": "user_123", "enabled": True}
    execution_payload = {"input": "Sample text for summary", "skill": skill_config["name"]}
    
    assert skill_config["enabled"] is True
    assert execution_payload["skill"] == "summarizer"
