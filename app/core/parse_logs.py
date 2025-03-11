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
                        if "Error:" in line), None),
        "location": next((line for line in trace_lines 
                         if "File" in line), None),
        "full_trace": trace_lines  # Added full trace storage
    }

def parse_log_files(files: Union[List[Path], List[UploadedFile]] = None) -> list:
    results = []
    
    if not files:
        # Default behavior - read from LOG_FOLDER
        log_folder = Path("data/log")
        files = list(log_folder.glob("*.log"))
    
    for file in files:
        try:
            if isinstance(file, UploadedFile):
                filename = file.name
                log_lines = file.getvalue().decode('utf-8').splitlines()
            else:
                filename = file.name
                with open(file, 'r', encoding="utf-8") as f:
                    log_lines = f.readlines()
            
            current_entry = None
            error_trace = []
            in_traceback = False

            for line in log_lines:
                line = line.strip()
                
                if "==== Logging started for" in line:
                    current_entry = {
                        "file_id": filename.split('.')[0],
                        "service": line.split("for ")[-1].replace(" ====", ""),
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
