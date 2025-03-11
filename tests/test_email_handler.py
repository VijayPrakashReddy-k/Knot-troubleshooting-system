import pytest
from unittest.mock import patch, MagicMock
from utils.email_handler import EmailHandler

@pytest.fixture
def email_handler():
    """Fixture to create an EmailHandler instance with test configuration"""
    with patch.dict('os.environ', {
        'SMTP_SERVER': 'test.smtp.server',
        'SMTP_PORT': '587',
        'SMTP_USERNAME': 'test_user',
        'SMTP_PASSWORD': 'test_password',
        'SENDER_EMAIL': 'test@example.com'
    }):
        return EmailHandler()

@pytest.mark.parametrize(
    "recipient,subject,body",
    [
        ("test@example.com", "Test Subject", "Test Body"),
        ("another@example.com", "Hello", "Hello World"),
    ]
)
def test_send_email_success(email_handler, recipient, subject, body):
    """Test successful email sending"""
    # Mock the SMTP connection
    mock_smtp = MagicMock()
    
    with patch('smtplib.SMTP') as mock_smtp_class:
        # Configure the mock
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp
        
        # Call the method
        result = email_handler.send_email(recipient, subject, body)
        
        # Verify the result
        assert result["status"] == "success"
        assert result["message"] == "Email sent successfully"
        
        # Verify SMTP interactions
        mock_smtp_class.assert_called_once_with(
            email_handler.smtp_server,
            email_handler.smtp_port
        )
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with(
            email_handler.smtp_username,
            email_handler.smtp_password
        )
        mock_smtp.send_message.assert_called_once()

def test_send_email_failure(email_handler):
    """Test email sending failure"""
    with patch('smtplib.SMTP') as mock_smtp_class:
        # Configure the mock to raise an exception
        mock_smtp_class.return_value.__enter__.side_effect = Exception("SMTP Error")
        
        # Call the method
        result = email_handler.send_email(
            "test@example.com",
            "Test Subject",
            "Test Body"
        )
        
        # Verify the error result
        assert result["status"] == "error"
        assert "SMTP Error" in result["message"]

def test_email_handler_initialization():
    """Test EmailHandler initialization with missing configuration"""
    with patch.dict('os.environ', {}, clear=True):
        handler = EmailHandler()
        
        # Verify default values
        assert handler.smtp_server == "live.smtp.mailtrap.io"
        assert handler.smtp_port == 587
        assert handler.smtp_username == "api"
        assert handler.smtp_password == "your_password_here"
        assert handler.sender_email == "hello@demomailtrap.co"

def test_validate_config_with_missing_vars():
    """Test configuration validation with missing variables"""
    with patch.dict('os.environ', {
        'SMTP_SERVER': '',  # Empty server
        'SMTP_PORT': '587',
        'SMTP_USERNAME': 'test_user',
        'SMTP_PASSWORD': 'your_password_here',  # Default password
        'SENDER_EMAIL': 'test@example.com'
    }):
        with patch('logging.Logger.warning') as mock_warning:
            handler = EmailHandler()
            # Verify that warning was logged for missing configuration
            mock_warning.assert_called_once()
            warning_args = mock_warning.call_args[0][0]
            assert "Missing required email configuration" in warning_args
            assert "SMTP_SERVER" in warning_args
            assert "SMTP_PASSWORD" in warning_args 