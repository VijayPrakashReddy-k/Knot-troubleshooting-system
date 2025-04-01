"""
LLM-based payment flow analyzer
"""
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Union


from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from utils.email_handler import EmailHandler
from .openai_functions import get_email_function
from .config import ModelConfig, ModelProvider
from .prompt_template import SYSTEM_PROMPT, FEW_SHOT_EXAMPLES


logger = logging.getLogger(__name__)

class PaymentFlowAnalyzer:
    def __init__(self):
        """Initialize the analyzer with configuration"""
        self.config = ModelConfig.load_config()
        self._setup_client()
        self.email_handler = EmailHandler()  # Initialize email handler
        
    def _setup_client(self):
        """Setup LLM client based on provider"""
        provider = self.config["provider"]
        
        if provider == ModelProvider.OPENAI.value:
            self.openai_client = OpenAI(api_key=self.config["api_keys"]["openai"])
        elif provider == ModelProvider.GOOGLE.value:
            genai.configure(api_key=self.config["api_keys"]["google"])
            self.model = genai.GenerativeModel(self.config["model"])
        elif provider == ModelProvider.ANTHROPIC.value:
            self.anthropic_client = Anthropic(api_key=self.config["api_keys"]["anthropic"])
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def analyze_flow(self, har_data: List[Dict], log_data: Union[List[Dict], Dict]) -> Dict[str, Any]:
        """
        Analyze payment flow using LLM
        Args:
            har_data: List of HAR entries
            log_data: Log data as dict or list of dicts
        Returns:
            Dict containing analysis results
        """
        try:
            # Group HAR requests by file_id
            transactions = self._group_transactions(har_data)
            
            logger.info(f"Transactions: {transactions}")
            
            logger.info(f"Log Data: {log_data}")
            # Find matching log entry for each transaction
            matched_logs = self._match_logs_to_transaction(log_data, transactions)

            # Prepare LLM context
            context = self._prepare_context(transactions, matched_logs)

            logger.info(f"Context: {context}")
            # Get LLM analysis
            analysis = self._get_llm_analysis(context)

            logger.info(f"Analysis: {analysis}")

            return {
                "timestamp": datetime.now().isoformat(),
                "file_id": log_data.get("file_id", "unknown"),
                "analysis": analysis,
                "transaction_count": len(transactions)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing flow: {str(e)}", exc_info=True)
            raise

    def _group_transactions(self, har_data: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group API requests into transactions based on file_id
        Args:
            har_data: List of HAR entries
        Returns:
            Dict mapping file_id to list of transaction entries
        """
        transactions = {}
        for entry in har_data:
            file_id = entry.get("file_id", "unknown")
            if file_id not in transactions:
                transactions[file_id] = []
            transactions[file_id].append({
                "method": entry.get("method", ""),
                "url": entry.get("url", ""),
                "status": entry.get("status_code", 0),
                "error": entry.get("error_message", None),
                "timestamp": entry.get("timestamp", "")
            })
        
        # Sort transactions by timestamp if available
        for file_id in transactions:
            transactions[file_id].sort(key=lambda x: x.get("timestamp", ""))
        
        return transactions

    def _match_logs_to_transaction(self, log_data: Dict, transactions: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        Find relevant logs for each transaction and include all available log details.

        Args:
            log_data: Log data dictionary.
            transactions: Grouped transactions dictionary.

        Returns:
            Dict containing matched logs, transaction data, and additional details.
        """
        file_id = log_data.get("file_id", "unknown")

        return {
            "file_id": file_id,
            "service": log_data.get("service", "unknown"),
            "task_url": log_data.get("task_url", ""),
            "steps": log_data.get("steps", []),
            "status": log_data.get("status", "unknown"),
            "error_message": log_data.get("error_message", None),
            "error_details": log_data.get("error_details", None),
            "transaction": transactions.get(file_id, []),
        }

    # def _match_logs_to_transaction(self, log_data: Dict, transactions: Dict[str, List[Dict]]) -> Dict[str, Any]:
    #     """
    #     Find relevant logs for each transaction
    #     Args:
    #         log_data: Log data dictionary
    #         transactions: Grouped transactions dictionary
    #     Returns:
    #         Dict containing matched logs and transaction data
    #     """
    #     file_id = log_data.get("file_id", "unknown")
    #     return {
    #         "steps": log_data.get("steps", []),
    #         "status": log_data.get("status", "unknown"),
    #         "error_message": log_data.get("error_message", "none"),
    #         "transaction": transactions.get(file_id, [])
    #     }

    def _prepare_context(self, transactions: Dict[str, List[Dict]], log_data: Dict) -> str:
        """
        Prepare context for LLM analysis with structured format
        Args:
            transactions: Grouped transactions dictionary
            log_data: Matched log data
        Returns:
            Formatted context string for LLM
        """
        # Extract API sequence from transaction
        api_sequence = " → ".join([
            entry["url"].split("/")[-1]
            for entry in log_data["transaction"]
        ])

        # Extract merchant name from log data and format it
        merchant_name = log_data.get("service", "unknown").replace("_", " ").title()

        # Prepare few-shot examples
        examples_text = "\n\n".join([
            f"### Example {i+1} ###\n"
            f"- API Sequence: {ex['har_data']['transaction_sequence']}\n"
            f"- Logs: {ex['log_data']}\n"
            f"- Expected Output:\n{ex['expected_output']}"
            for i, ex in enumerate(FEW_SHOT_EXAMPLES)
        ])

        # Replace merchant_name placeholder in system prompt
        context_prompt = SYSTEM_PROMPT.replace("{{merchant_name}}", merchant_name)

        return f"""
{context_prompt}

### Few-Shot Examples ###
{examples_text}

### New Analysis Request ###
- **API Sequence:** {api_sequence}
- **Transaction Data:** {json.dumps(log_data['transaction'], indent=2)}
- **Log Steps:** {json.dumps(log_data.get('steps', []), indent=2)}
- **Status:** {log_data.get('status', 'unknown')}
- **Error:** {log_data.get('error_message', 'none')}
"""

    def _get_llm_analysis(self, context: str) -> str:
        """
        Get analysis from LLM
        Args:
            context: Prepared context string
        Returns:
            LLM analysis response
        """
        provider = self.config["provider"]
        
        try:
            if provider == ModelProvider.OPENAI.value:
                response = self.openai_client.chat.completions.create(
                    model=self.config["model"],
                    messages=[
                        {"role": "system", "content": "You are a payment flow analysis expert. Always include the merchant name in your analysis. Only suggest email functionality if users explicitly request it."},
                        {"role": "user", "content": context}
                    ],
                    temperature=self.config["temperature"]
                )
                return response.choices[0].message.content
            
            elif provider == ModelProvider.GOOGLE.value:
                response = self.model.generate_content(context)
                return response.text
            
            elif provider == ModelProvider.ANTHROPIC.value:
                response = self.anthropic_client.messages.create(
                    model=self.config["model"],
                    messages=[{"role": "user", "content": context}]
                )
                return response.content

        except Exception as e:
            logger.error(f"Error getting LLM analysis from {provider}: {str(e)}", exc_info=True)
            raise

    def chat_analyze(self, har_data: List[Dict], log_data: Union[List[Dict], Dict], prompt: str) -> Dict:
        """
        Interactive analysis based on user prompt with function calling support
        """
        try:
            # Get initial analysis
            transaction_analyses = self._get_transaction_analyses(har_data, log_data)

            # Extract merchant name from log data
            merchant_name = (
                log_data[0]["service"].replace("_", " ").strip().title()
                if isinstance(log_data, list) 
                else log_data["service"].replace("_", " ").strip().title()
            )

            # merchant_name = log_data[0].get("service", "unknown").replace("_", " ").title() if isinstance(log_data, list) else log_data.get("service", "unknown").replace("_", " ").title()

            # Replace merchant name in system prompt
            context_prompt = SYSTEM_PROMPT.replace("{{merchant_name}}", merchant_name)

            # Prepare chat context with explicit email instructions and merchant info
            chat_context = f"""
                {context_prompt}

                Merchant: {merchant_name}

                Previous Transaction Analyses:
                {self._format_transaction_analyses(transaction_analyses)}

                User Question/Prompt:
                {prompt}

                Instructions:
                - Always begin your response by mentioning the merchant name
                - Analyze the transactions and provide insights
                - Keep the response focused and avoid duplicating information
                """

            # Setup available tools/functions
            tools = [
                get_email_function()
            ]

            # Get LLM response with function calling
            response = self._get_llm_response_with_functions(chat_context, tools)

            # Process any function calls
            function_results = []
            if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
                function_results = self._handle_tool_calls(response.choices[0].message.tool_calls)
                logger.info(f"Function calls processed: {function_results}")
            else:
                logger.info("No tool calls in response")

            return {
                "timestamp": datetime.now().isoformat(),
                "original_analyses": transaction_analyses,
                "chat_response": response.choices[0].message.content,
                "function_results": function_results,
                "needs_email": False
            }

        except Exception as e:
            logger.error(f"Error in chat analysis: {str(e)}", exc_info=True)
            raise

    def _handle_tool_calls(self, tool_calls: List[Any]) -> List[Dict]:
        """
        Handle function calls from the LLM
        """
        results = []
        for tool_call in tool_calls:
            try:
                if tool_call.function.name == "send_email":
                    logger.info(f"Processing email tool call: {tool_call.function.arguments}")
                    args = json.loads(tool_call.function.arguments)
                    result = self.email_handler.send_email(
                        recipient=args["recipient"],
                        subject=args["subject"],
                        body=args["body"]
                    )
                    results.append({
                        "function": "send_email",
                        "result": result
                    })
                    logger.info(f"Email sending result: {result}")
            except Exception as e:
                logger.error(f"Error handling tool call: {str(e)}")
                results.append({
                    "function": tool_call.function.name,
                    "result": {"status": "error", "message": str(e)}
                })
        return results

    def _get_llm_response_with_functions(self, context: str, tools: List[Dict]) -> Any:
        """
        Get LLM response with function calling capability
        """
        provider = self.config["provider"]
        
        try:
            if provider == ModelProvider.OPENAI.value:
                return self.openai_client.chat.completions.create(
                    model=self.config["model"],
                    messages=[
                        {"role": "system", "content": "You are a payment flow analysis expert. Always begin responses by mentioning the merchant name. Only suggest email functionality if users explicitly request it."},
                        {"role": "user", "content": context}
                    ],
                    tools=tools,
                    tool_choice="auto",  # Let the model decide when to use tools
                    temperature=self.config["temperature"]
                )
            else:
                raise ValueError(f"Function calling not supported for provider: {provider}")
            
        except Exception as e:
            logger.error(f"Error getting LLM response: {str(e)}", exc_info=True)
            raise

    def _format_examples(self, examples: List[Dict]) -> str:
        """
        Format few-shot examples for context
        Args:
            examples: List of example dictionaries
        Returns:
            Formatted string of examples
        """
        formatted_examples = []
        for i, example in enumerate(examples, 1):
            formatted_example = f"""
                Example {i}:
                -----------
                API Sequence: {example['har_data']['transaction_sequence']}

                Log Data:
                {json.dumps(example['log_data'], indent=2)}

                Expected Output:
                {example['expected_output']}
                """
            formatted_examples.append(formatted_example)
        
        return "\n\n".join(formatted_examples)

    def _format_transaction_analyses(self, analyses: List[Dict]) -> str:
        """
        Format multiple transaction analyses into a structured string
        Args:
            analyses: List of transaction analysis dictionaries
        Returns:
            Formatted string containing all analyses
        """
        formatted_analyses = []
        for analysis in analyses:
            formatted_analysis = f"""
                Transaction {analysis.get('file_id', 'unknown')}:
                ------------------------
                Initial Analysis:
                {analysis.get('analysis', 'No analysis available')}

                Transaction Details:
                Status: {analysis.get('status', 'unknown')}
                Error: {analysis.get('error_message', 'none')}
                """
            formatted_analyses.append(formatted_analysis)
        
        return "\n\n".join(formatted_analyses)

    def _get_transaction_analyses(self, har_data: List[Dict], log_data: Union[List[Dict], Dict]) -> List[Dict]:
        """
        Get analyses for all transactions
        Args:
            har_data: List of HAR entries
            log_data: Log data as dict or list of dicts
        Returns:
            List of transaction analysis dictionaries
        """
        try:
            # Convert log_data to list if it's a dict
            if isinstance(log_data, dict):
                log_data = [log_data]
            
            analyses = []
            for log_entry in log_data:
                # Get HAR entries for this log entry
                transaction_har = [
                    entry for entry in har_data
                    if entry.get("file_id") == log_entry.get("file_id")
                ]
                
                logger.info(f"Transaction HAR: {transaction_har}")
                # Analyze this transaction
                analysis = self.analyze_flow(transaction_har, log_entry)
                analyses.append(analysis)
                logger.info(f"Analysis: {analysis}")
            return analyses
            
        except Exception as e:
            logger.error(f"Error getting transaction analyses: {str(e)}")
            raise

