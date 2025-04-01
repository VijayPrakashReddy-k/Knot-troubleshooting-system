import pytest
from app.core.pattern_detector import FailurePatternDetector, FailurePattern

@pytest.fixture
def sample_har_data():
    return [
        {
            'file_id': '1',
            'status_code': 404,
            'url': 'http://api.example.com/endpoint',
            'error_message': 'Endpoint not found'
        },
        {
            'file_id': '2',
            'status_code': 500,
            'url': 'http://api.example.com/another',
            'error_message': 'Internal server error'
        },
        {
            'file_id': '3',
            'status_code': 200,  # Success case
            'url': 'http://api.example.com/success',
        }
    ]

@pytest.fixture
def sample_log_data():
    return [
        {
            'file_id': '1',
            'status': 'failed',
            'steps': ['Cookies sanitized', 'Authentication failed'],
            'error_message': 'Session expired'
        },
        {
            'file_id': '2',
            'status': 'failed',
            'steps': ['Card is not reflected', 'Verification failed'],
            'error_message': 'Card verification error'
        },
        {
            'file_id': '4',
            'status': 'success',  # Should be filtered out
            'steps': ['Success step'],
        }
    ]

class TestFailurePatternDetector:
    def test_initialization(self, sample_har_data, sample_log_data):
        detector = FailurePatternDetector(sample_har_data, sample_log_data)
        assert len(detector.log_data) == 2  # Only failed logs
        assert len(detector.har_data) == 2  # Only HAR entries with matching file_ids

    def test_detect_auth_failures(self, sample_har_data, sample_log_data):
        detector = FailurePatternDetector(sample_har_data, sample_log_data)
        patterns = detector._detect_auth_failures()
        
        assert len(patterns) == 1
        pattern = patterns[0]
        assert isinstance(pattern, FailurePattern)
        assert pattern.type == "cookie_session_failure"
        assert pattern.frequency == 1
        assert "Session expired" in pattern.error_messages

    def test_detect_api_failures(self, sample_har_data, sample_log_data):
        detector = FailurePatternDetector(sample_har_data, sample_log_data)
        patterns = detector._detect_api_failures()
        
        assert len(patterns) == 2  # Should detect both 404 and 500 errors
        
        # Verify 404 pattern
        not_found = next(p for p in patterns if p.type == "endpoint_not_found")
        assert not_found.frequency == 1
        assert "Endpoint not found" in not_found.error_messages
        
        # Verify 500 pattern
        server_error = next(p for p in patterns if p.type == "server_error")
        assert server_error.frequency == 1
        assert "Internal server error" in server_error.error_messages

    def test_detect_verification_failures(self, sample_har_data, sample_log_data):
        detector = FailurePatternDetector(sample_har_data, sample_log_data)
        patterns = detector._detect_verification_failures()
        
        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.type == "card_verification_failure"
        assert pattern.frequency == 1
        assert "Card verification error" in pattern.error_messages

    def test_detect_failure_patterns(self, sample_har_data, sample_log_data):
        detector = FailurePatternDetector(sample_har_data, sample_log_data)
        patterns = detector.detect_failure_patterns()
        
        assert isinstance(patterns, dict)
        assert set(patterns.keys()) == {"authentication", "api", "verification"}
        
        # Verify each category has the expected number of patterns
        assert len(patterns["authentication"]) == 1
        assert len(patterns["api"]) == 2
        assert len(patterns["verification"]) == 1

    def test_generate_summary(self, sample_har_data, sample_log_data):
        detector = FailurePatternDetector(sample_har_data, sample_log_data)
        summary = detector.generate_summary()
        
        assert isinstance(summary, dict)
        assert summary["total_failures"] == 2  # Number of failed logs
        assert summary["pattern_distribution"] == {
            "authentication": 1,
            "api": 2,
            "verification": 1
        }
        assert "patterns" in summary

    def test_empty_data(self):
        detector = FailurePatternDetector([], [])
        patterns = detector.detect_failure_patterns()
        
        assert all(len(p) == 0 for p in patterns.values())
        
        summary = detector.generate_summary()
        assert summary["total_failures"] == 0
        assert all(count == 0 for count in summary["pattern_distribution"].values()) 