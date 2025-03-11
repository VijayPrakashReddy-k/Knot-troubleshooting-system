import json
import pytest
from pathlib import Path
from unittest.mock import mock_open, patch, MagicMock
from app.core.parse_har import (
    sanitize_header_value,
    sanitize_url,
    parse_har_files
)

# Test data
SAMPLE_HAR_DATA = {
    "log": {
        "entries": [{
            "request": {
                "url": "https://api.example.com/data?key=secret123&name=test",
                "method": "GET",
                "headers": [
                    {"name": "Authorization", "value": "Bearer token123"},
                    {"name": "Content-Type", "value": "application/json"},
                ]
            },
            "response": {
                "status": 200,
                "statusText": "OK",
                "bodySize": 1234
            },
            "timings": {
                "total": 100
            }
        }]
    }
}

@pytest.mark.parametrize("header_name,header_value,expected", [
    ("authorization", "Bearer token123", "[REDACTED]"),
    ("cookie", "session=abc123", "[REDACTED]"),
    ("x-csrf-token", "xyz789", "[REDACTED]"),
    ("content-type", "application/json", "application/json"),
    ("accept", "*/*", "*/*"),
])
def test_sanitize_header_value(header_name, header_value, expected):
    """Test header value sanitization"""
    result = sanitize_header_value(header_name, header_value)
    assert result == expected

@pytest.mark.parametrize("url,expected", [
    (
        "https://api.example.com/data?key=secret123&name=test",
        "https://api.example.com/data?key=%5BREDACTED%5D&name=test"
    ),
    (
        "https://api.example.com/data?token=abc&user=john",
        "https://api.example.com/data?token=%5BREDACTED%5D&user=john"
    ),
    (
        "https://api.example.com/data",
        "https://api.example.com/data"
    ),
    (
        "invalid-url",
        "invalid-url"
    ),
])
def test_sanitize_url(url, expected):
    """Test URL sanitization"""
    result = sanitize_url(url)
    assert result == expected

def test_parse_har_files_with_uploaded_file():
    """Test parsing uploaded HAR file"""
    mock_file = MagicMock()
    mock_file.name = "test.har"
    # Fix: Return bytes directly instead of using lambda
    mock_file.read.return_value = json.dumps(SAMPLE_HAR_DATA).encode('utf-8')
    mock_file.content_type = 'application/json'
    mock_file.seek = MagicMock()

    results = parse_har_files([mock_file])

    assert len(results) == 1
    entry = results[0]
    assert entry["file_id"] == "test"
    assert entry["method"] == "GET"
    assert entry["status_code"] == 200
    assert entry["response_time"] == 100
    assert entry["response_size"] == 1234
    assert "[REDACTED]" in entry["request_headers"]["Authorization"]

def test_parse_har_files_with_local_file():
    """Test parsing local HAR file"""
    mock_content = json.dumps(SAMPLE_HAR_DATA)
    
    with patch("builtins.open", mock_open(read_data=mock_content)):
        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [Path("test.har")]
            results = parse_har_files()

    assert len(results) == 1
    entry = results[0]
    assert entry["file_id"] == "test"
    assert entry["status_code"] == 200

def test_parse_har_files_with_error_entry():
    """Test parsing HAR entry with error status code"""
    error_har_data = {
        "log": {
            "entries": [{
                "request": {
                    "url": "https://api.example.com/error",
                    "method": "GET",
                    "headers": []
                },
                "response": {
                    "status": 404,
                    "statusText": "Not Found",
                    "bodySize": 0
                },
                "timings": {
                    "total": 50
                }
            }]
        }
    }

    mock_file = MagicMock()
    mock_file.name = "error.har"
    # Fix: Return bytes directly
    mock_file.read.return_value = json.dumps(error_har_data).encode('utf-8')
    mock_file.content_type = 'application/json'
    mock_file.seek = MagicMock()

    results = parse_har_files([mock_file])

    assert len(results) == 1
    entry = results[0]
    assert entry["status_code"] == 404
    assert "HTTP 404: Not Found" in entry["error_message"]

def test_parse_har_files_with_invalid_data():
    """Test parsing invalid HAR data"""
    invalid_har_data = {"log": {"entries": [{}]}}  # Missing required fields
    
    mock_file = MagicMock()
    mock_file.name = "invalid.har"
    mock_file.read.return_value = json.dumps(invalid_har_data).encode()

    results = parse_har_files([mock_file])
    
    # Should handle the error gracefully and return empty results
    assert len(results) == 0

def test_parse_har_files_with_redirect():
    """Test parsing HAR entry with redirect"""
    redirect_har_data = {
        "log": {
            "entries": [{
                "request": {
                    "url": "https://api.example.com/old",
                    "method": "GET",
                    "headers": []
                },
                "response": {
                    "status": 302,
                    "statusText": "Found",
                    "redirectURL": "https://api.example.com/new",
                    "bodySize": 0
                },
                "timings": {
                    "total": 30
                }
            }]
        }
    }

    mock_file = MagicMock()
    mock_file.name = "redirect.har"
    # Fix: Return bytes directly
    mock_file.read.return_value = json.dumps(redirect_har_data).encode('utf-8')
    mock_file.content_type = 'application/json'
    mock_file.seek = MagicMock()

    results = parse_har_files([mock_file])

    assert len(results) == 1
    entry = results[0]
    assert entry["status_code"] == 302
    assert "Redirect to: https://api.example.com/new" in entry["error_message"] 