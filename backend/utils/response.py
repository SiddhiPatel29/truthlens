"""
Standard API Response utility.
Ensures every API response follows an exact, predictable JSON structure.
"""
from flask import jsonify

def api_response(success: bool, message: str, data=None, error_code=None, status_code: int = 200):
    """
    Constructs a uniform JSON response envelope:
    {
        "success": true/false,
        "message": "Human readable summary",
        "data": { ... } or null,
        "error_code": "ERROR_CODE" or null
    }
    """
    payload = {
        "success": success,
        "message": message,
        "data": data,
        "error_code": error_code
    }
    return jsonify(payload), status_code