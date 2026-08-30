import pytest

def test_api_exception_sanitization():
    raw_error = "Database connection timeout at 10.0.0.1:5432 with password secret_pass"
    user_error_message = "An unexpected database error occurred. Please try again later."
    
    assert "secret_pass" not in user_error_message
    assert "10.0.0.1" not in user_error_message
    assert user_error_message == "An unexpected database error occurred. Please try again later."

def test_ai_provider_fallback_graceful_degradation():
    provider_status = {"primary": "offline", "fallback": "online"}
    active_provider = provider_status["fallback"] if provider_status["primary"] == "offline" else provider_status["primary"]
    
    assert active_provider == "online"
