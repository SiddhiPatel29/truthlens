"""
Tests for Text Detection API Route (/api/detect/text).
"""

def test_detect_text_success(client, sample_text):
    """Verify valid text input returns 200 and expected forensic metrics."""
    response = client.post("/api/detect/text", json={"text": sample_text})
    assert response.status_code == 200
    assert response.is_json
    
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "Text analyzed successfully."
    assert json_data["error_code"] is None
    
    data = json_data["data"]
    assert "is_ai_generated" in data
    assert isinstance(data["is_ai_generated"], bool)
    assert "ai_confidence_score" in data
    assert 0.0 <= data["ai_confidence_score"] <= 1.0
    assert "metrics" in data
    assert data["metrics"]["total_words"] > 0
    assert "sentence_breakdown" in data
    assert len(data["sentence_breakdown"]) > 0

def test_detect_text_missing_field(client):
    """Verify request without 'text' field returns 400 INVALID_INPUT."""
    response = client.post("/api/detect/text", json={"wrong_field": "content"})
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_INPUT"

def test_detect_text_too_short(client):
    """Verify text under 20 characters returns 400 TEXT_TOO_SHORT."""
    response = client.post("/api/detect/text", json={"text": "Too short"})
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "TEXT_TOO_SHORT"

def test_detect_text_non_string_type(client):
    """Verify non-string input returns 400 INVALID_INPUT."""
    response = client.post("/api/detect/text", json={"text": 12345678901234567890})
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_INPUT"

def test_detect_text_empty_body(client):
    """Verify empty or non-JSON body returns 400 INVALID_INPUT."""
    response = client.post("/api/detect/text", data="not json", content_type="text/plain")
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_INPUT"
