# Knot Troubleshooting System

- [Knot Troubleshooting System](#knot-troubleshooting-system)
  - [1. Description](#1-description)
  - [2. Core Features](#2-core-features)
      - [2.1.1 Log Parser](#211-log-parser)
        - [Limitations:](#limitations)
      - [2.1.2 HAR Parser](#212-har-parser)
        - [Limitations](#limitations-1)
      - [2.2 Analysis Engine](#22-analysis-engine)
      - [2.3 LLM-Powered Transaction Analysis and Recommendation System](#23-llm-powered-transaction-analysis-and-recommendation-system)
      - [2.4 User Interface](#24-user-interface)
      - [2.5 Notification \& Alert System](#25-notification--alert-system)
  - [3. Architecture Diagram](#3-architecture-diagram)
  - [4. Installation](#4-installation)
  - [5. Improvements](#5-improvements)

## 1. Description

The **Knot Troubleshooting System** is designed to efficiently analyze **Application Logs** and **HTTP Archive (HAR) files**, extract meaningful insights, and provide automated recommendations for issue resolution. It integrates log parsing, network request analysis, and an intelligent recommendation engine to enhance debugging workflows and improve system performance.

## 2. Core Features

- **Creates a `file_id` for Mapping HAR and Log Files:** The script assigns a unique `file_id` to each HAR and log file. This allows seamless correlation between network requests and log events, making it easier to track issues, analyze system behavior, and generate recommendations.


#### 2.1.1 Log Parser
- **Detects and Organizes Log Entries:** The script identifies when a log starts (`"==== Logging started for"`) and initializes a structured entry. It extracts details like the service name, task URL, and step-by-step execution logs. Each log entry is stored in a structured format, making it easier to analyze later.

- **Captures and Analyzes Errors:** The script monitors for `"Traceback"` occurrences and switches to error-tracking mode. It records all traceback lines until it finds an actual error message (e.g., `"Exception:"` or `"KeyError:"`). The captured error is stored along with details like its type, location, and full trace.

- **Saves Parsed Logs for Future Use:** After processing all logs, the structured data is saved in a JSON file (`"data/processed/parsed_logs.json"`). This ensures that parsed logs can be reviewed later, integrated into other tools, or used for debugging.

- [Example of Log Parsing](./CONTENT.md/#log-parsing-success)

 ##### Limitations:
- **Single Log Capture per File:** If multiple logs exist in one file, only the first entry is processed, and subsequent logs are ignored.

- **Error Detection Dependency:** The script only recognizes errors following a `"Traceback"` section, missing standalone error messages.

- **Multi-line Data Handling:** Logs containing JSON responses or multi-line messages are not parsed correctly, leading to potential data loss.

- [Example of Log Parsing Limitations](./CONTENT.md/#log-parsing-failure)

#### 2.1.2 HAR Parser

- **Extracts and Organizes HTTP Requests:** The script reads `.har` files and processes each HTTP request entry. It extracts details like the request URL, method, status code, response time, and response size. The structured data makes it easier to analyze network requests and responses.

- **Sanitizes Sensitive Data:** The script removes sensitive headers (`Authorization`, `Cookie`, `X-CSRF-Token`) and query parameters (`api_key`, `password`, `auth`) from URLs. This ensures that security-related information is not exposed in logs or outputs.

- **Saves Processed HAR Data for Analysis:** After processing all entries, the structured data is saved in a JSON file (`"data/processed/parsed_har.json"`). This allows further debugging, performance analysis, and integration with other tools.

- [Example of HAR Parsing](./CONTENT.md/#har-parsing-success)

##### Limitations
- **Incomplete Request or Response Data:** Some HAR files may have missing fields (`status`, `headers`, `bodySize`), leading to incomplete parsing.

- [Example of HAR Parsing Limitations](./CONTENT.md/#har-parsing-failure)


#### 2.2 Analysis Engine

- **Smart Failure Detection**
  - The engine scans HAR files and logs to identify authentication, API, and verification failures automatically. It filters out failed logs and cross-references them with HAR data to focus only on problematic transactions, reducing noise.

- **Grouping Issues & Finding Root Causes**

  - Authentication Issues: Detects missing cookies, session failures, and login problems.
  - API Failures: Flags broken endpoints (404) and server errors (500).
  - Card Verification Failures: Identifies cases where payments fail despite successful API responses.
  - By analyzing error messages and frequency, the engine pinpoints recurring problems.
- **Actionable Insights & Recommendations**
  - Instead of just listing errors, the engine assigns severity levels, tracks failure frequency, and provides clear solutions. It helps teams prioritize fixes—whether it's session handling, API debugging, or improving payment processing.

#### 2.3 LLM-Powered Transaction Analysis and Recommendation System
- **AI-Powered Transaction Analysis**
  - The system automates debugging of payment transactions using LLMs (OpenAI, Anthropic, Google GenAI).  
  - It processes HAR logs and system logs, detecting errors, failures, and anomalies in payment workflows.  
  - The LLM provides context-aware insights to help diagnose and resolve issues efficiently.

- **Structured Data Processing and Context Preparation**
  - **Transaction Grouping**: Aggregates transactions by `file_id`, ensuring log-to-transaction mapping.  
  - **Error Identification**: Filters logs for failed requests, categorizing them based on status codes (4xx, 5xx).  
  - **Few-Shot Learning**: Formats logs and transaction sequences as structured LLM prompts to generate accurate debugging recommendations.

- **Scalable and Extendable with Function Calling**
  - Supports interactive analysis via `chat_analyze()`, enabling follow-up questions and deeper insights.  
  - Integrates function calling, allowing the LLM to trigger email alerts (`send_email`) for critical failures.  
  - Optimizations like log filtering, database storage, and summarization ensure scalability for large datasets without overwhelming the system.


#### 2.4 User Interface

- **Streamlit-Based Payment Flow Analysis UI**
  - This script builds an interactive UI using Streamlit to analyze payment transaction flows.
  - It supports file uploads (HAR, log files) and also enables **batch processing** by automatically retrieving data from the data folder. The system efficiently analyzes transactions and delivers detailed visual insights into payment flow anomalies.
  - The interface enables chat-based troubleshooting, where users can ask questions and receive LLM-generated responses.

- **Data Processing and Error Detection**
  - HAR & Log File Handling: Reads and parses transaction data from files.
  - Failure Analysis: Detects authentication failures, API errors, and payment verification issues.
  - Pattern Matching: Uses `FailurePatternDetector` to categorize and summarize common failure types.

- **LLM-Powered Chat & Function Calling**
  - Supports natural language queries for analyzing transaction issues.
  - Utilizes LLM function calling to send email alerts (`send_email`).
  - Provides clickable suggested prompts, enabling quick access to common troubleshooting scenarios.

- [Example of User Interface](https://knot-troubleshoot.streamlit.app/)

#### 2.5 Notification & Alert System

- **Email & Slack Alerts**
  - The system can send **email alerts** when critical failures occur.
  - It leverages **LLM function calling** to trigger email notifications.
  - **Note:** Instead of email, the system can also be configured to send **Slack notifications** for real-time alerts.

- [Example of Notification & Alert System](./Gmail%20-%20Knot%20API%20Transaction%20Analysis%20for%20Uber%20Eats.pdf)

## 3. Architecture Diagram
  
![Image](https://github.com/user-attachments/assets/7a3dbfd7-f3f5-4d6e-a456-017f09b80ee1)

## 4. Installation

1. Clone the repository
```bash
git clone https://github.com/VijayPrakashReddy-k/Knot-troubleshooting.git
cd Knot-troubleshooting
```

2. Install Poetry
```bash
# For Unix/macOS/WSL
curl -sSL https://install.python-poetry.org | python3 -

# For Windows PowerShell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

3. Create and activate virtual environment

```bash
# Create a new virtual environment
python -m venv .venv

# Activate the virtual environment
# For Unix/macOS/WSL
source .venv/bin/activate

# For Windows cmd.exe
.venv\Scripts\activate.bat

# For Windows PowerShell
.venv\Scripts\Activate.ps1
```

4. Install dependencies using Poetry
```bash
# Install dependencies without installing the project as a package
poetry install --no-root

# If you only need production dependencies
poetry install --no-root --no-dev
```

5. Create a `.env.local` file in the `env` directory with the following template:
```env:env/.env.local
# LLM Configuration
LLM_PROVIDER=openai  # openai, google, or anthropic
LLM_MODEL=gpt-4o  # model name from AVAILABLE_MODELS
LLM_TEMPERATURE=0.3

# API Keys (replace with your encoded keys)
OPENAI_API_KEY=sk-************************************
GOOGLE_API_KEY=your_google_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# SMTP Configuration
SMTP_SERVER=live.smtp.mailtrap.io
SMTP_PORT=587
SMTP_USERNAME=api
SMTP_PASSWORD=************************************
SENDER_EMAIL=your_sender_email@example.com
```

6. Run the Streamlit interface
```bash
streamlit run app/web/streamlit_app.py
```

## 5. Improvements

- Integrating database and creating indexes for har and log files based on `"file_id"` for efficiency and query performance and streamlining into Troubleshooting system and Slack integration for real-time alerts, anomaly detection, and severity-based notifications.

- Strengthen prompt instructions to effectively handle all possible failure conditions and capture detailed failure context to enhance troubleshooting and resolution.
