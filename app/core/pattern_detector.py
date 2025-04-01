from typing import Dict, List
from dataclasses import dataclass

@dataclass
class FailurePattern:
    type: str
    description: str
    severity: str
    frequency: int
    affected_files: List[str]
    error_messages: List[str]
    recommendation: str

class FailurePatternDetector:
    def __init__(self, har_data: List[Dict], log_data: List[Dict]):
        # self.har_data = har_data
        # self.log_data = [log for log in log_data if log.get('status') == 'failed']

        self.log_data = [log for log in log_data if log.get('status') == 'failed']
        self.har_data = [har for har in har_data if har.get('file_id') in {log.get('file_id') for log in self.log_data}]
                
    def detect_failure_patterns(self) -> Dict[str, List[FailurePattern]]:
        """Analyze failed transactions and identify patterns"""
        patterns = {
            "authentication": self._detect_auth_failures(),
            "api": self._detect_api_failures(),
            "verification": self._detect_verification_failures()
        }
        return patterns

    def _detect_auth_failures(self) -> List[FailurePattern]:
        """Detect authentication and session-related failures"""
        patterns = []
        
        # Group authentication failures by error message
        auth_failures = []
        for log in self.log_data:
            steps = log.get('steps', [])
            steps_str = ' '.join(str(step) for step in steps)
            
            if any(indicator in steps_str for indicator in [
                "cookies required",
                "Valid cookies",
                "Cookies sanitized",
                "session"
            ]):
                auth_failures.append({
                    'file_id': log.get('file_id'),
                    'error_message': log.get('error_message'),
                    'steps': steps
                })

        if auth_failures:
            patterns.append(FailurePattern(
                type="cookie_session_failure",
                description="Authentication failures due to cookie/session issues",
                severity="high",
                frequency=len(auth_failures),
                affected_files=[f['file_id'] for f in auth_failures],
                error_messages=list(set(f['error_message'] for f in auth_failures if f['error_message'])),
                recommendation="Review session management and cookie handling process"
            ))

        return patterns

    def _detect_api_failures(self) -> List[FailurePattern]:
        """Detect API-related failures"""
        patterns = []
        
        # Group API failures by status code
        api_failures = {}
        for entry in self.har_data:
            if entry.get('status_code', 0) >= 400:
                status = entry['status_code']
                if status not in api_failures:
                    api_failures[status] = []
                api_failures[status].append({
                    'file_id': entry['file_id'],
                    'url': entry['url'],
                    'error_message': entry.get('error_message')
                })

        # Analyze 404 errors (Not Found)
        if 404 in api_failures:
            patterns.append(FailurePattern(
                type="endpoint_not_found",
                description="API endpoints returning 404 errors",
                severity="high",
                frequency=len(api_failures[404]),
                affected_files=list(set(f['file_id'] for f in api_failures[404])),
                error_messages=list(set(f['error_message'] for f in api_failures[404] if f['error_message'])),
                recommendation="Verify API endpoint URLs and routing configuration"
            ))

        # Analyze 500 errors (Server Error)
        if 500 in api_failures:
            patterns.append(FailurePattern(
                type="server_error",
                description="Internal server errors in API responses",
                severity="high",
                frequency=len(api_failures[500]),
                affected_files=list(set(f['file_id'] for f in api_failures[500])),
                error_messages=list(set(f['error_message'] for f in api_failures[500] if f['error_message'])),
                recommendation="Investigate server-side error logs and exception handling"
            ))

        return patterns

    def _detect_verification_failures(self) -> List[FailurePattern]:
        """Detect card verification and reflection failures"""
        patterns = []
        
        # Analyze card verification failures
        verification_failures = []
        for log in self.log_data:
            steps = log.get('steps', [])
            steps_str = ' '.join(str(step) for step in steps)
            
            if any(indicator in steps_str for indicator in [
                "Card is not reflected",
                "card is not reflected",
                "Card verification failed",
                "Update card error"
            ]):
                verification_failures.append({
                    'file_id': log.get('file_id'),
                    'error_message': log.get('error_message'),
                    'steps': steps
                })

        if verification_failures:
            patterns.append(FailurePattern(
                type="card_verification_failure",
                description="Card verification or reflection failures",
                severity="high",
                frequency=len(verification_failures),
                affected_files=[f['file_id'] for f in verification_failures],
                error_messages=list(set(f['error_message'] for f in verification_failures if f['error_message'])),
                recommendation="Implement robust card verification checks and retry mechanism"
            ))

        return patterns

    def generate_summary(self) -> Dict:
        """Generate a summary of failure patterns"""
        patterns = self.detect_failure_patterns()
        
        total_failures = len(self.log_data)
        pattern_counts = {
            category: len(items) for category, items in patterns.items()
        }
        
        return {
            "total_failures": total_failures,
            "pattern_distribution": pattern_counts,
            "patterns": patterns
        } 