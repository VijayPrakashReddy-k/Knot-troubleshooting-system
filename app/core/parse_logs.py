import json
import streamlit as st
from pathlib import Path
from typing import List, Union
from streamlit.runtime.uploaded_file_manager import UploadedFile


def parse_error_trace(trace_lines):
    """Extract meaningful information from traceback"""
    return {
        "type": trace_lines[-1] if trace_lines else None,
        "message": next((line for line in reversed(trace_lines) 
                        if "Error:" in line or "Exception:" in line), None),
        "location": next((line for line in trace_lines 
                         if "File" in line), None),
        "full_trace": trace_lines
    }

def convert_json_to_traditional(json_logs):
    """Convert JSON format logs to traditional format"""
    traditional_lines = []
    
    # Sort logs by timestamp if available
    if all('timestamp' in log for log in json_logs):
        json_logs = sorted(json_logs, key=lambda x: x['timestamp'])
    
    current_service = None
    for log in json_logs:
        message = log.get("jsonPayload", {}).get("message", "")
        labels = log.get("jsonPayload", {}).get("labels", {})
        
        # Start of new service log
        if "==== Logging started for" in message:
            current_service = message.split("for ")[-1].replace(" ====", "").strip()
            traditional_lines.append(message)
            
        # Task URL
        elif "Task URL:" in message:
            traditional_lines.append(message)
            
        # Error handling
        elif "error" in log.get("jsonPayload", {}):
            error = log["jsonPayload"]["error"]
            if "stacktrace" in log["jsonPayload"]:
                traditional_lines.append("Traceback (most recent call last):")
                traditional_lines.extend(log["jsonPayload"]["stacktrace"].split("\n"))
            traditional_lines.append(error)
            
        # Regular message
        elif message and not message.startswith("===="):
            traditional_lines.append(message)
            
        # End of service log
        elif "==== Logging ended" in message and current_service:
            traditional_lines.append(message)
            current_service = None
            
    return "\n".join(traditional_lines)

def parse_log_files(files: Union[List[Path], List[UploadedFile]] = None) -> list:
    results = []
    
    if not files:
        # Default behavior - read from LOG_FOLDER
        log_folder = Path("data/log")
        files = list(log_folder.glob("*.log")) + list(log_folder.glob("*.json"))
    
    for file in files:
        try:
            if isinstance(file, UploadedFile):
                filename = file.name
                content = file.getvalue().decode('utf-8')
            else:
                filename = file.name
                with open(file, 'r', encoding="utf-8") as f:
                    content = f.read()

            # Try parsing as JSON first
            try:
                json_logs = json.loads(content)
                if isinstance(json_logs, list):
                    # Convert JSON format to traditional format
                    content = convert_json_to_traditional(json_logs)
            except json.JSONDecodeError:
                # If not JSON, use content as is
                pass

            # Process as traditional format
            log_lines = content.splitlines()
            current_entry = None
            error_trace = []
            in_traceback = False

            for line in log_lines:
                line = line.strip()
                
                if "==== Logging started for" in line:
                    current_entry = {
                        "file_id": filename.split('.')[0],
                        "service": line.split("for ")[-1].replace(" ====", "").strip(),
                        "task_url": None,
                        "steps": [],
                        "status": "success",
                        "error_message": None,
                        "error_details": None
                    }
                
                elif current_entry:
                    if "Task URL:" in line:
                        current_entry["task_url"] = line.replace("Task URL:", "").strip()
                    
                    elif "Traceback" in line:
                        in_traceback = True
                        error_trace = [line]
                    
                    elif in_traceback:
                        error_trace.append(line)
                        if line.startswith(("commons.exceptions", "Exception")):
                            current_entry["error_message"] = line
                            current_entry["error_details"] = parse_error_trace(error_trace)
                            current_entry["status"] = "failed"
                            in_traceback = False
                    
                    elif not in_traceback and line and not line.startswith("===="):
                        current_entry["steps"].append(line)
                    
                    elif "==== Logging ended" in line and current_entry:
                        results.append(current_entry)
                        current_entry = None
                        
        except Exception as e:
            st.error(f"Error processing {filename}: {e}")
            continue

    # Save processed data
    output_file = Path("data/processed/parsed_logs.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding="utf-8") as f:
        json.dump(results, f, indent=4)
        
    return results

if __name__ == "__main__":
    parse_log_files()
