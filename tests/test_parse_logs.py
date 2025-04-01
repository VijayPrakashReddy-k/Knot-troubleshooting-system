import pytest
from pathlib import Path
from unittest.mock import mock_open, patch, MagicMock
from app.core.parse_logs import parse_log_files, parse_error_trace

# Sample log content with proper newlines
SAMPLE_LOG_CONTENT = """==== Logging started for PaymentService ====
Task URL: https://api.example.com/payment/123
Starting payment processing
Validating payment details
Payment processed successfully
==== Logging ended ===="""

SAMPLE_ERROR_LOG = """==== Logging started for PaymentService ====
Task URL: https://api.example.com/payment/456
Starting payment processing
Traceback (most recent call last):
  File "payment.py", line 123, in process_payment
    raise PaymentError("Invalid card number")
commons.exceptions.PaymentError: Invalid card number
==== Logging ended ===="""

@pytest.fixture
def mock_file_operations():
    """Fixture to mock file operations"""
    with patch('pathlib.Path.mkdir') as mock_mkdir:
        with patch('builtins.open', mock_open()) as mock_file:
            yield mock_mkdir, mock_file

def test_parse_error_trace():
    """Test error trace parsing"""
    trace_lines = [
        "Traceback (most recent call last):",
        'File "payment.py", line 123, in process_payment',
        "commons.exceptions.PaymentError: Invalid card number"
    ]
    
    result = parse_error_trace(trace_lines)
    
    assert result["type"] == "commons.exceptions.PaymentError: Invalid card number"
    assert "Invalid card number" in result["message"]
    assert 'File "payment.py"' in result["location"]
    assert result["full_trace"] == trace_lines

def test_parse_log_files_success(mock_file_operations):
    """Test parsing successful log file"""
    mock_file = MagicMock()
    mock_file.name = "test.log"
    
    # Create a mock for decoded content
    decoded_content = MagicMock()
    decoded_content.splitlines.return_value = SAMPLE_LOG_CONTENT.splitlines()
    
    # Create a mock for decode method
    decode_mock = MagicMock()
    decode_mock.return_value = decoded_content
    
    # Setup the chain of mocks
    mock_file.getvalue.return_value = MagicMock()
    mock_file.getvalue.return_value.decode = decode_mock

    with patch('streamlit.error'):
        results = parse_log_files([mock_file])

    assert len(results) == 1
    entry = results[0]
    assert entry["file_id"] == "test"
    assert entry["service"] == "PaymentService"
    assert entry["task_url"] == "https://api.example.com/payment/123"
    assert len(entry["steps"]) == 3
    assert entry["status"] == "success"
    assert entry["error_message"] is None

def test_parse_log_files_with_error(mock_file_operations):
    """Test parsing log file with error"""
    mock_file = MagicMock()
    mock_file.name = "error.log"
    
    # Create a mock for decoded content
    decoded_content = MagicMock()
    decoded_content.splitlines.return_value = SAMPLE_ERROR_LOG.splitlines()
    
    # Create a mock for decode method
    decode_mock = MagicMock()
    decode_mock.return_value = decoded_content
    
    # Setup the chain of mocks
    mock_file.getvalue.return_value = MagicMock()
    mock_file.getvalue.return_value.decode = decode_mock

    with patch('streamlit.error'):
        results = parse_log_files([mock_file])

    assert len(results) == 1
    entry = results[0]
    assert entry["file_id"] == "error"
    assert entry["service"] == "PaymentService"
    assert entry["status"] == "failed"
    assert "Invalid card number" in entry["error_message"]

def test_parse_log_files_with_local_files(mock_file_operations):
    """Test parsing local log files"""
    mock_mkdir, mock_file = mock_file_operations
    mock_file.return_value.read.return_value = SAMPLE_LOG_CONTENT
    mock_file.return_value.readlines.return_value = SAMPLE_LOG_CONTENT.splitlines()

    with patch('pathlib.Path.glob') as mock_glob:
        mock_glob.return_value = [Path("test.log")]
        results = parse_log_files()

    assert len(results) == 1
    entry = results[0]
    assert entry["service"] == "PaymentService"
    assert entry["status"] == "success"

def test_parse_log_files_with_multiple_entries(mock_file_operations):
    """Test parsing multiple log entries"""
    multiple_logs = f"{SAMPLE_LOG_CONTENT}\n{SAMPLE_ERROR_LOG}"
    
    mock_file = MagicMock()
    mock_file.name = "multiple.log"
    
    # Create a mock for decoded content
    decoded_content = MagicMock()
    decoded_content.splitlines.return_value = multiple_logs.splitlines()
    
    # Create a mock for decode method
    decode_mock = MagicMock()
    decode_mock.return_value = decoded_content
    
    # Setup the chain of mocks
    mock_file.getvalue.return_value = MagicMock()
    mock_file.getvalue.return_value.decode = decode_mock

    with patch('streamlit.error'):
        results = parse_log_files([mock_file])

    assert len(results) == 2
    assert results[0]["status"] == "success"
    assert results[1]["status"] == "failed"

def test_parse_log_files_with_invalid_content(mock_file_operations):
    """Test parsing invalid log content"""
    invalid_content = "Invalid log content\nNo proper structure"
    
    mock_file = MagicMock()
    mock_file.name = "invalid.log"
    mock_file.getvalue.return_value = invalid_content.encode('utf-8')
    mock_file.read.return_value = invalid_content

    with patch('streamlit.error') as mock_error:
        results = parse_log_files([mock_file])
        assert len(results) == 0

def test_parse_log_files_with_empty_file(mock_file_operations):
    """Test parsing empty log file"""
    mock_file = MagicMock()
    mock_file.name = "empty.log"
    mock_file.getvalue.return_value = "".encode('utf-8')
    mock_file.read.return_value = ""

    results = parse_log_files([mock_file])
    assert len(results) == 0

def test_parse_log_files_save_output(mock_file_operations):
    """Test saving parsed results to file"""
    mock_mkdir, mock_file = mock_file_operations
    mock_file.return_value.read.return_value = SAMPLE_LOG_CONTENT

    mock_input_file = MagicMock()
    mock_input_file.name = "test.log"
    mock_input_file.getvalue.return_value = SAMPLE_LOG_CONTENT.encode('utf-8')
    mock_input_file.read.return_value = SAMPLE_LOG_CONTENT

    with patch('streamlit.error'):
        results = parse_log_files([mock_input_file])
        
        # Verify directory creation
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        
        # Verify file writing occurred
        assert mock_file.call_count >= 1

def test_parse_error_trace_empty():
    """Test error trace parsing with empty input"""
    result = parse_error_trace([])
    assert result["type"] is None
    assert result["message"] is None
    assert result["location"] is None
    assert result["full_trace"] == [] 