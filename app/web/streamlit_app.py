import sys
import json
import base64
import logging
import pandas as pd
import streamlit as st
from pathlib import Path
from typing import List, Dict

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from utils.email_handler import EmailHandler
from app.core.data_handler import DataHandler
from models.analyzer import PaymentFlowAnalyzer
from app.core.pattern_detector import FailurePatternDetector


st.set_page_config(
    page_title="Payment Flow Analyzer",
    layout="wide",
    initial_sidebar_state="collapsed"
)

logger = logging.getLogger(__name__)

# Define suggested prompts at module level
suggested_prompts = {
    "Transaction Analysis": [
        "Transaction status and errors",
        "Compare successful vs failed transaction flows",
        "Show me all failed transactions",
        "What went wrong in failed transaction?",
    ]
}

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_png_as_page_bg(png_file):
    bin_str = get_base64_of_bin_file(png_file)
    page_bg_img = f'''
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    
    /* Make the background image darker */
    .stApp::before {{
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);  /* Black overlay with 50% opacity */
        z-index: -1;
    }}

    /* Style containers for better visibility */
    .stMarkdown, 
    .stButton,
    .stSelectbox,
    .stFileUploader,
    [data-testid="stJson"] {{
        background-color: rgba(255, 255, 255, 0.9) !important;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }}

    /* Style tabs */
    .stTabs [data-baseweb="tab-panel"] {{
        background-color: rgba(255, 255, 255, 0.9);
        padding: 20px;
        border-radius: 5px;
    }}

    /* Style title */
    h1 {{
        color: black !important;
        text-shadow: 2px 2px 4px rgba(255, 255, 255, 0.5);
    }}

    /* Style subheaders */
    h2, h3 {{
        color: black !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.5);
    }}
    </style>
    '''
    st.markdown(page_bg_img, unsafe_allow_html=True)

def load_parsed_data():
    har_file = Path("data/processed/parsed_har.json")
    log_file = Path("data/processed/parsed_logs.json")
    
    har_data = []
    log_data = []
    
    if har_file.exists():
        with open(har_file, 'r') as f:
            har_data = json.load(f)
            
    if log_file.exists():
        with open(log_file, 'r') as f:
            log_data = json.load(f)
            
    return har_data, log_data

def analyze_payment_flows(har_data, log_data):
    """Analyze payment flows from HAR and log data"""
    results = []
    
    # Group HAR entries by file
    har_by_file = {}
    for entry in har_data:
        file_id = entry["file_id"]
        if file_id not in har_by_file:
            har_by_file[file_id] = []
        har_by_file[file_id].append(entry)
    
    # Match with log entries
    for log_entry in log_data:
        log_file_id = log_entry["file_id"]
        har_entries = har_by_file.get(log_file_id, [])
        
        # Sort entries by step number to maintain sequence
        har_entries.sort(key=lambda x: x.get('step_number', 0))
        
        # Get the flow sequence
        api_sequence = []
        for entry in har_entries:
            base_route = entry.get('base_route', 'unknown')
            full_path = entry.get('full_path', 'unknown')
            api_sequence.append({
                'route': base_route,
                'path': full_path,
                'status': entry.get('status_code', 0),
                'method': entry.get('method', 'unknown')
            })
        
        # Determine status - default to 'unknown' if not present
        status = log_entry.get("status", "unknown")
        if status not in ["success", "failed", "unknown"]:
            status = "unknown"
        
        flow_analysis = {
            "file_id": log_file_id,
            "status": status,
            "error_message": log_entry.get("error_message"),
            "api_calls": len(har_entries),
            "total_response_size": sum(e.get("response_size", 0) for e in har_entries),
            "steps_completed": len(log_entry.get("steps", [])),
            "flow_sequence": " -> ".join(step['route'] for step in api_sequence),
            "detailed_flow": " -> ".join(step['path'] for step in api_sequence),
            "flow_status": " -> ".join(f"{step['route']}({step['status']})" for step in api_sequence)
        }
        results.append(flow_analysis)
    
    df = pd.DataFrame(results)
    
    # Ensure status column exists with default value
    if "status" not in df.columns:
        df["status"] = "unknown"
    
    return df

def display_processing_results(results):
    """Display processing results with detailed breakdown"""
    # Summary message
    st.success(f"Processing completed!")
    
    # Detailed breakdown in an expander
    with st.expander("View Processing Details"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### HAR Files")
            st.markdown(f"✓ Processed: **{results['har']['processed']}**")
            if results['har']['errors'] > 0:
                st.markdown(f"❌ Errors: **:red[{results['har']['errors']}]**")
            else:
                st.markdown(f"✓ Errors: **{results['har']['errors']}**")
                
        with col2:
            st.markdown("### Log Files")
            st.markdown(f"✓ Processed: **{results['log']['processed']}**")
            if results['log']['errors'] > 0:
                st.markdown(f"❌ Errors: **:red[{results['log']['errors']}]**")
            else:
                st.markdown(f"✓ Errors: **{results['log']['errors']}**")

def display_function_results(function_results: List[Dict]):
    """Display results of function calls in a structured way"""
    for result in function_results:
        if result["function"] == "send_email":
            if result["result"]["status"] == "success":
                st.success(f"✉️ {result['result']['message']}")
            else:
                st.error(f"📫 Email Error: {result['result']['message']}")

def display_suggested_prompts():
    """Display clickable suggested prompts"""
    st.markdown("#### 💡 Suggested Questions")
    
    # Initialize used_prompts in session state if not exists
    if "used_prompts" not in st.session_state:
        st.session_state.used_prompts = set()
    
    # Create columns for each category
    cols = st.columns(len(suggested_prompts))
    
    # Display prompts by category in columns
    for col, (category, prompts) in zip(cols, suggested_prompts.items()):
        with col:
            st.markdown(f"**{category}**")
            for prompt in prompts:
                # Check if prompt has been used
                is_used = prompt in st.session_state.used_prompts
                
                # Create button with different style based on whether it's been used
                if is_used:
                    # Display used prompt as disabled
                    st.markdown(f"<button disabled style='width:100%;opacity:0.6;background-color:#E0E0E0;color:#666;padding:8px;border:none;border-radius:4px;margin:2px 0;'>{prompt}</button>", unsafe_allow_html=True)
                else:
                    # Create clickable button for unused prompt
                    if st.button(prompt, key=f"suggest_{prompt}"):
                        # Add to used prompts when clicked
                        st.session_state.used_prompts.add(prompt)
                        return prompt
    return None

def display_failure_patterns(har_data, log_data):
    """Display failure pattern analysis in Streamlit"""
    st.subheader("🔍 Failure Pattern Analysis")
    
    # Create detector and get analysis
    detector = FailurePatternDetector(har_data, log_data)
    analysis = detector.generate_summary()
    
    # Display summary metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Failures", analysis["total_failures"])
    with col2:
        auth_count = analysis["pattern_distribution"].get("authentication", 0)
        st.metric("Auth Failures", auth_count)
    with col3:
        api_count = analysis["pattern_distribution"].get("api", 0)
        st.metric("API Failures", api_count)
    with col4:
        verify_count = analysis["pattern_distribution"].get("verification", 0)
        st.metric("Verification Failures", verify_count)
    
    # Display detailed patterns
    st.markdown("### Detailed Failure Analysis")
    
    tabs = st.tabs(["Authentication", "API", "Verification"])
    
    # Authentication tab
    with tabs[0]:
        if analysis["patterns"]["authentication"]:
            for pattern in analysis["patterns"]["authentication"]:
                with st.expander(f"🔐 {pattern.type.replace('_', ' ').title()}", expanded=True):
                    col1, col2 = st.columns([2,1])
                    with col1:
                        st.markdown(f"**Description:** {pattern.description}")
                        st.markdown(f"**Affected Files:** {', '.join(pattern.affected_files)}")
                        st.markdown("**Error Messages:**")
                        for msg in pattern.error_messages:
                            st.markdown(f"- {msg}")
                    with col2:
                        st.markdown(f"**Severity:** {pattern.severity.upper()}")
                        st.markdown(f"**Frequency:** {pattern.frequency} occurrences")
                    st.markdown(f"**Recommendation:** {pattern.recommendation}")
        else:
            st.info("No authentication failures detected")
    
    # API tab
    with tabs[1]:
        if analysis["patterns"]["api"]:
            for pattern in analysis["patterns"]["api"]:
                with st.expander(f"🌐 {pattern.type.replace('_', ' ').title()}", expanded=True):
                    col1, col2 = st.columns([2,1])
                    with col1:
                        st.markdown(f"**Description:** {pattern.description}")
                        st.markdown(f"**Affected Files:** {', '.join(pattern.affected_files)}")
                        st.markdown("**Error Messages:**")
                        for msg in pattern.error_messages:
                            st.markdown(f"- {msg}")
                    with col2:
                        st.markdown(f"**Severity:** {pattern.severity.upper()}")
                        st.markdown(f"**Frequency:** {pattern.frequency} occurrences")
                    st.markdown(f"**Recommendation:** {pattern.recommendation}")
        else:
            st.info("No API failures detected")
    
    # Verification tab
    with tabs[2]:
        if analysis["patterns"]["verification"]:
            for pattern in analysis["patterns"]["verification"]:
                with st.expander(f"💳 {pattern.type.replace('_', ' ').title()}", expanded=True):
                    col1, col2 = st.columns([2,1])
                    with col1:
                        st.markdown(f"**Description:** {pattern.description}")
                        st.markdown(f"**Affected Files:** {', '.join(pattern.affected_files)}")
                        st.markdown("**Error Messages:**")
                        for msg in pattern.error_messages:
                            st.markdown(f"- {msg}")
                    with col2:
                        st.markdown(f"**Severity:** {pattern.severity.upper()}")
                        st.markdown(f"**Frequency:** {pattern.frequency} occurrences")
                    st.markdown(f"**Recommendation:** {pattern.recommendation}")
        else:
            st.info("No verification failures detected")

def main():
    # Set background image
    set_png_as_page_bg('assets/knot.jpeg')
    
    st.title("Knot Troubleshooting System")
    
    # Initialize session state for toggles if not exists
    if 'show_analysis' not in st.session_state:
        st.session_state.show_analysis = False
    if 'show_raw_data' not in st.session_state:
        st.session_state.show_raw_data = False
    if 'files_processed' not in st.session_state:
        st.session_state.files_processed = False
    
    # Initialize data variables
    har_data = None
    log_data = None
    
    # Create a container for better organization
    with st.container():
        # File upload section
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Upload HAR Files")
            har_files = st.file_uploader("Choose HAR files", 
                                       type=['har'], 
                                       accept_multiple_files=True)
            
        with col2:
            st.subheader("Upload Log Files")
            log_files = st.file_uploader("Choose LOG files (supports both .log and .json)", 
                                        type=['log', 'json'], 
                                        accept_multiple_files=True)
        
        # Process button section
        col3, col4 = st.columns(2)
        
        with col3:
            # Disable button if no files are uploaded
            if st.button("Process Uploaded Files", 
                        key="upload_btn",
                        disabled=not (har_files or log_files)):
                with st.spinner("Processing uploaded files..."):
                    handler = DataHandler()
                    results = handler.process_files(har_files, log_files)
                    display_processing_results(results)
                    st.session_state.files_processed = True
                    # Load processed data
                    har_data, log_data = load_parsed_data()
                    # Automatically enable chat and analysis after processing
                    st.session_state.show_chat = True
                    st.session_state.show_analysis = True
                        
        with col4:
            if st.button("Process Files from Data Folder", key="folder_btn"):
                with st.spinner("Processing files from data folder..."):
                    handler = DataHandler()
                    results = handler.process_files()
                    display_processing_results(results)
                    st.session_state.files_processed = True
                    # Load processed data
                    har_data, log_data = load_parsed_data()
                    # Automatically enable chat and analysis after processing
                    st.session_state.show_chat = True
                    st.session_state.show_analysis = True
        
        # Toggle for data analysis
        show_analysis = st.toggle('Show Analysis', value=st.session_state.get('show_analysis', False))
        
        if show_analysis:
            if not st.session_state.files_processed:
                st.warning("⚠️ Please process files first by either uploading files or using data folder files.")
            else:
                st.subheader("Payment Flow Data Metrics")
                
                # Load data if not already loaded
                if har_data is None or log_data is None:
                    har_data, log_data = load_parsed_data()
                
                if har_data and log_data:
                    # Generate analysis
                    df = analyze_payment_flows(har_data, log_data)
                    
                    # Display metrics with source format
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Flows", len(df))
                    with col2:
                        success_count = (df["status"] == "success").sum()
                        total_count = len(df)
                        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
                        st.metric("Success Rate", f"{success_rate:.1f}%")
                        st.caption(f"Success: {success_count}, Total: {total_count}")
                    with col3:
                        avg_calls = df["api_calls"].mean() if "api_calls" in df.columns else 0
                        st.metric("Average API Calls", f"{avg_calls:.1f}")
                    with col4:
                        # Add status distribution
                        status_counts = df["status"].value_counts()
                        status_str = ", ".join(f"{k}: {v}" for k, v in status_counts.items())
                        st.metric("Status Distribution", status_str)
                    
                    # Display detailed analysis
                    st.subheader("Flow Details")
                    st.dataframe(df, use_container_width=True)
                    
                    # Add failure pattern analysis
                    st.markdown("---")
                    display_failure_patterns(har_data, log_data)
                    
                else:
                    st.info("No data available for analysis. Please process some files first.")
        
        # Toggle for raw data
        st.session_state.show_raw_data = st.toggle('Show Raw Data', 
                                                 value=st.session_state.show_raw_data)
        
        if st.session_state.show_raw_data:
            if not st.session_state.files_processed:
                st.warning("⚠️ Please process files first by either uploading files or using data folder files.")
            else:
                st.subheader("Raw Data")
                
                # Load data if not already loaded
                if har_data is None or log_data is None:
                    har_data, log_data = load_parsed_data()
                    
                tab1, tab2 = st.tabs(["HAR Data", "Log Data"])
                
                with tab1:
                    if har_data:
                        st.json(har_data)
                    else:
                        st.info("No HAR data available")
                    
                with tab2:
                    if log_data:
                        # Add format selector
                        log_format = st.radio("Select Log Format", ["Processed", "Original"], horizontal=True)
                        
                        if log_format == "Processed":
                            st.json(log_data)
                        else:
                            # Display original format with better JSON formatting
                            for idx, entry in enumerate(log_data):
                                with st.expander(f"Log Entry {idx + 1} - {entry.get('service', 'Unknown Service')}"):
                                    st.json(entry)
                    else:
                        st.info("No log data available")

    # Add Chat Interface with automatic showing after processing
    show_chat = st.toggle('Show Chat Analysis', 
                        value=st.session_state.get('show_chat', False),
                        key='chat_toggle')
    
    if show_chat:
        if not st.session_state.files_processed:
            st.warning("⚠️ Please process files first by either uploading files or using data folder files.")
        else:
            st.subheader("Chat Analysis")
            
            # Initialize chat history in session state if not exists
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
                st.session_state.used_prompts = set()
                # Add initial system message to guide the user
                st.info("""
                🤖 I've analyzed your payment flow transactions. You can ask me questions about:
                - Transaction status and errors
                - API sequence analysis
                - Payment flow issues
                - Recommendations for fixes
                """)
            
            # Always display suggested prompts
            selected_prompt = display_suggested_prompts()
            
            # Display chat messages from history
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    if message["role"] == "assistant":
                        # Display structured analysis results
                        st.markdown("#### Analysis Results")
                        st.markdown(message["content"]["chat_response"])
                        
                        # Display function results if any
                        if message["content"].get("function_results"):
                            display_function_results(message["content"]["function_results"])
                        
                        # Show original transaction analyses in expander
                        with st.expander("View Individual Transaction Analyses"):
                            for analysis in message["content"]["original_analyses"]:
                                st.markdown(f"**Transaction {analysis['file_id']}**")
                                st.markdown(analysis["analysis"])
                                st.markdown("---")
                    else:
                        # Display user message normally
                        st.markdown(message["content"])
            
            # Accept user input - either from text input or selected prompt
            user_input = st.chat_input("Ask about the payment flows or request email reports...")
            
            # Process either the selected prompt or user input
            prompt_to_process = selected_prompt or user_input
            
            if prompt_to_process:
                # Add user message to chat history
                st.session_state.chat_history.append({"role": "user", "content": prompt_to_process})
                
                # Display user message
                with st.chat_message("user"):
                    st.markdown(prompt_to_process)
                
                # Load data if not already loaded
                if har_data is None or log_data is None:
                    har_data, log_data = load_parsed_data()
                
                # Process the prompt and get response
                if har_data and log_data:
                    with st.chat_message("assistant"):
                        with st.spinner("Analyzing transactions..."):
                            # Display file count information
                            har_count = len(har_data) if isinstance(har_data, list) else 1
                            log_count = len(log_data) if isinstance(log_data, list) else 1
                            st.info(f"📊 Analyzing {har_count} HAR entries and {log_count} log files...")
                            
                            analyzer = PaymentFlowAnalyzer()
                            try:
                                log_data_list = log_data if isinstance(log_data, list) else [log_data]
                                response = analyzer.chat_analyze(har_data, log_data_list, prompt_to_process)
                                
                                # Display response
                                st.markdown("#### Analysis Results")
                                st.markdown(response["chat_response"])
                                
                                if response.get("function_results"):
                                    display_function_results(response["function_results"])
                                
                                with st.expander("View Individual Transaction Analyses"):
                                    for analysis in response["original_analyses"]:
                                        st.markdown(f"**Transaction {analysis['file_id']}**")
                                        st.markdown(analysis["analysis"])
                                        st.markdown("---")
                                
                                # Add assistant response to chat history
                                st.session_state.chat_history.append({
                                    "role": "assistant",
                                    "content": response
                                })
                                
                                # Rerun to update the display
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Error analyzing transactions: {str(e)}")
                else:
                    st.info("No data available for analysis. Please process some files first.")
            
            # Add a button to clear chat history and reset suggested prompts
            if st.session_state.chat_history:
                if st.button("Clear Chat History"):
                    st.session_state.chat_history = []
                    st.session_state.used_prompts = set()  # Reset used prompts
                    st.rerun()

if __name__ == "__main__":
    main() 