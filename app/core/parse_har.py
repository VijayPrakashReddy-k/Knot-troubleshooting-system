import json
import logging
from pathlib import Path
from typing import List, Union, Dict
from streamlit.runtime.uploaded_file_manager import UploadedFile
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


logger = logging.getLogger(__name__)

def sanitize_header_value(name: str, value: str) -> str:
    """Sanitize sensitive header values"""
    sensitive_headers = {'cookie', 'authorization', 'x-csrf-token'}
    return '[REDACTED]' if name.lower() in sensitive_headers else value

# def sanitize_url(url: str) -> str:
#     """Remove sensitive information from URLs"""
#     try:
#         parsed = urlparse(url)
#         params = parse_qs(parsed.query)
        
#         # Remove sensitive parameters
#         sensitive_params = {'key', 'token', 'api_key', 'secret', 'password', 'auth'}
#         sanitized_params = {
#             k: ['[REDACTED]'] if k.lower() in sensitive_params else v
#             for k, v in params.items()
#         }
        
#         return urlunparse(parsed._replace(
#             query=urlencode(sanitized_params, doseq=True)
#         ))
#     except:
#         return url

def get_route_sequence(url: str) -> Dict[str, str]:
    """Extract route components in a generic way"""
    try:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.strip('/').split('/') if p]
        
        return {
            'base': path_parts[0] if path_parts else 'root',
            'full_path': '/'.join(path_parts),
            'depth': len(path_parts)
        }
    except Exception as e:
        logger.error(f"Error parsing URL route: {e}")
        return {'base': 'unknown', 'full_path': 'unknown', 'depth': 0}

def parse_har_files(files: Union[List[Path], List[UploadedFile]] = None) -> list:
    results = []
    
    if not files:
        har_folder = Path("data/har")
        files = list(har_folder.glob("*.har"))
    
    for file in files:
        try:
            # Read file content
            if isinstance(file, UploadedFile):
                filename = file.name
                content = file.read()
                har_data = json.loads(content)
            else:
                filename = file.name
                with open(file, 'r', encoding="utf-8") as f:
                    content = f.read()
                    har_data = json.loads(content)
            
            file_id = filename.split('.')[0]
            logger.info(f"Processing HAR file: {filename}")
            
            # Process entries
            for entry in har_data['log']['entries']:
                try:
                    request = entry['request']
                    response = entry['response']
                    timings = entry['timings']

                    response_time = timings.get('total')
                    if not isinstance(response_time, (int, float)):
                        response_time = None

                    headers = {
                        h["name"]: sanitize_header_value(h["name"], h["value"])
                        for h in request.get("headers", [])
                    }

                    status_code = response.get("status")
                    error_message = None
                    if status_code is not None and status_code >= 400:
                        error_message = f"HTTP {status_code}: {response.get('statusText', 'Error')}"
                    elif status_code == 302:
                        error_message = f"Redirect to: {response.get('redirectURL', 'unknown')}"

                    results.append({
                        "file_id": file_id,
                        "url": request.get("url", ""),
                        "method": request.get("method", ""),
                        "status_code": status_code,
                        "response_time": response_time,
                        "response_size": response.get("bodySize", 0),
                        "request_headers": headers,
                        "error_message": error_message
                    })

                except KeyError as e:
                    logger.error(f"Missing required field in HAR entry: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing HAR entry: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error processing HAR file {filename}: {e}")
            continue

    # Save processed data
    if results:
        output_file = Path("data/processed/parsed_har.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding="utf-8") as f:
            json.dump(results, f, indent=4)
        
        logger.info(f"Successfully processed {len(results)} HAR entries")
    else:
        logger.warning("No HAR entries were processed")

    return results
    
