from typing import Dict

def get_email_function() -> Dict:
    """
    Returns the email function definition for OpenAI
    """
    return {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Sends an email with analysis results",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body containing analysis results"
                    }
                },
                "required": ["recipient", "subject", "body"]
            }
        }
    } 