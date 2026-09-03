"""
Tests for Abuse Report Dispatcher API Route (/api/report/abuse).
"""

def test_dispatch_abuse_report_success(client):
    """Verify valid report payload returns 201 Created and structured dossier."""
    payload = {
        "platform": "youtube",
        "target_url": "https://youtube.com/watch?v=sample123",
        "category": "Synthetic Impersonation",
        "confidence_score": 0.982,
        "analyst_notes": "Deepfake face-swap detected on frame 142."
    }
    response = client.post("/api/report/abuse", json=payload)
    assert response.status_code == 201
    assert response.is_json
    
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "Abuse dossier successfully generated and dispatched."
    assert json_data["error_code"] is None
    
    data = json_data["data"]
    assert "report_id" in data
    assert data["report_id"].startswith("VM-REP-")
    assert data["status"] == "DISPATCHED"
    assert "dispatch_timestamp" in data
    assert "platform_destination" in data
    assert data["platform_destination"]["platform"] == "Youtube"
    assert "forensic_evidence" in data
    assert "sha256_fingerprint" in data["forensic_evidence"]
    assert len(data["forensic_evidence"]["sha256_fingerprint"]) == 64
    assert "dispatch_receipt" in data
    assert "acknowledgment_code" in data["dispatch_receipt"]

def test_dispatch_abuse_report_unsupported_platform(client):
    """Verify report for unsupported platform (e.g. tiktok) returns 400 VALIDATION_ERROR."""
    payload = {
        "platform": "tiktok",
        "target_url": "https://tiktok.com/@user/video/123",
        "category": "Synthetic Impersonation"
    }
    response = client.post("/api/report/abuse", json=payload)
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "VALIDATION_ERROR"
    assert "unsupported platform" in json_data["message"].lower()

def test_dispatch_abuse_report_missing_target_url(client):
    """Verify report without target_url returns 400 VALIDATION_ERROR."""
    payload = {
        "platform": "meta",
        "category": "Synthetic Impersonation"
    }
    response = client.post("/api/report/abuse", json=payload)
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "VALIDATION_ERROR"
    assert "target url" in json_data["message"].lower()

def test_dispatch_abuse_report_empty_or_invalid_json(client):
    """Verify non-JSON payload returns 400 INVALID_JSON."""
    response = client.post("/api/report/abuse", data="not json", content_type="text/plain")
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_JSON"
