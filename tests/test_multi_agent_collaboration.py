import pytest

def test_planner_to_executor_handoff():
    plan_steps = ["Analyze dataset", "Generate summary report", "Validate findings"]
    execution_state = {"current_step": 0, "status": "in_progress"}
    
    execution_state["current_step"] += 1
    assert plan_steps[execution_state["current_step"]] == "Generate summary report"

def test_critic_feedback_cycle():
    critic_report = {
        "material_findings": 2,
        "suggestions": ["Refine chart formatting", "Include executive summary"],
        "approved": False
    }
    
    assert critic_report["approved"] is False
    assert len(critic_report["suggestions"]) == 2
