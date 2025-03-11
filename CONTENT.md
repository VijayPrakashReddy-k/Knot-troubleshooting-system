
<h1>1. Log Parsing</h1>

<p align="center" id="log-parsing-success">
    <h3>1.1 Log Parsing - Success</h3>
</p>

**`Input:`** 
```plaintext
File: 1.log
==== Logging started for Service X ====
Task URL: http://example.com/task/101
Initializing process
Connecting to database
==== Logging ended ====

File: 2.log
==== Logging started for Service Y ====
Task URL: http://example.com/task/202
Fetching data
Traceback (most recent call last):
    File "script.py", line 18, in <module>
    raise ValueError("Invalid input data")
ValueError: Invalid input data
==== Logging ended ====
```

**`Output:`**
```json
[
    {
        "file_id": "1",
        "filename": "1.log",
        "service": "Service X",
        "task_url": "http://example.com/task/101",
        "steps": [
            "Initializing process",
            "Connecting to database"
        ],
        "status": "success",
        "error_message": null,
        "error_details": null
    },
    {
        "file_id": "2",
        "filename": "2.log",
        "service": "Service Y",
        "task_url": "http://example.com/task/202",
        "steps": [
            "Fetching data"
        ],
        "status": "failed",
        "error_message": "ValueError: Invalid input data",
        "error_details": {
            "type": "ValueError: Invalid input data",
            "message": "ValueError: Invalid input data",
            "location": "File \"script.py\", line 18, in <module>",
            "full_trace": [
                "Traceback (most recent call last):",
                "File \"script.py\", line 18, in <module>",
                "raise ValueError(\"Invalid input data\")",
                "ValueError: Invalid input data"
            ]
        }
    }
]

```
<p align="center" id="log-parsing-limitations">
    <h3>1.2 Log Parsing - Limitations</h3>
</p>

**`Input:`**  
```plaintext
File: 3.log
==== Logging started for Service A ====
Task URL: http://example.com/task/123
Initializing process
Connecting to database
==== Logging ended ====

==== Logging started for Service B ====
Task URL: http://example.com/task/456
Fetching data
==== Logging ended ====

File: 4.log
==== Logging started for Service C ====
Task URL: http://example.com/task/789
Connecting to API
Error: Connection timed out
==== Logging ended ====

File: 5.log
==== Logging started for Service D ====
Fetching user details
Response:
{
    "user": {
        "id": 123,
        "name": "John Doe"
    }
}
==== Logging ended ====
```

**`Output:`**
```json

[
    {
        "file_id": "3",
        "filename": "3.log",
        "service": "Service A",
        "task_url": "http://example.com/task/123",
        "steps": [
            "Initializing process",
            "Connecting to database"
        ],
        "status": "success",
        "error_message": null,
        "error_details": null
    },
    {
        "file_id": "4",
        "filename": "4.log",
        "service": "Service C",
        "task_url": "http://example.com/task/789",
        "steps": [
            "Connecting to API"
        ],
        "status": "success",
        "error_message": null,
        "error_details": null
    },
    {
        "file_id": "5",
        "filename": "5.log",
        "service": "Service D",
        "task_url": null,
        "steps": [
            "Fetching user details"
        ],
        "status": "success",
        "error_message": null,
        "error_details": null
    }
]
```

**`Issues:`**

- **Single Log Capture per File** - Service B log entry is ignored because the script does not correctly handle multiple logs in one file.
- **Error Detection Dependency** - "Error: Connection timed out" is missing in the parsed output because it is not inside a "Traceback" block.
- **Multi-line Data Handling** - The JSON response in Service D is not captured correctly, resulting in missing structured data.

<p align="center" id="har-parsing-success">
    <h3>2.1 HAR Parsing - Success</h3>
</p>

**`Input:`**  
```json
{
    "log": {
        "entries": [
            {
                "request": {
                    "method": "GET",
                    "url": "https://api.example.com/data?api_key=12345",
                    "headers": [
                        {"name": "Authorization", "value": "Bearer token123"},
                        {"name": "User-Agent", "value": "Mozilla/5.0"}
                    ]
                },
                "response": {
                    "status": 200,
                    "statusText": "OK",
                    "bodySize": 512
                },
                "timings": {
                    "total": 150
                }
            }
        ]
    }
}
```

**`Output:`**
```json


[
    {
        "file_id": "1",
        "url": "https://api.example.com/data?api_key=[REDACTED]",
        "method": "GET",
        "status_code": 200,
        "response_time": 150,
        "response_size": 512,
        "request_headers": {
            "Authorization": "[REDACTED]",
            "User-Agent": "Mozilla/5.0"
        },
        "error_message": null
    }
]
```

<p align="center" id="har-parsing-limitations">
    <h3>2.2 HAR Parsing - Limitations</h3>
</p>

**`Input:`**  
```json
{
    "log": {
        "entries": [
            {
                "request": {
                    "method": "POST",
                    "url": "https://api.example.com/upload",
                    "headers": [
                        {"name": "Cookie", "value": "session=abcd1234"}
                    ]
                },
                "response": {
                    "status": 500,
                    "statusText": "Internal Server Error",
                    "bodySize": 0
                },
                "timings": {
                    "total": null
                }
            }
        ]
    }
}
```

**`Output:`**
```json
[
    {
        "file_id": "2",
        "url": "https://api.example.com/upload",
        "method": "POST",
        "status_code": 500,
        "response_time": null,
        "response_size": 0,
        "request_headers": {
            "Cookie": "[REDACTED]"
        },
        "error_message": "HTTP 500: Internal Server Error"
    }
]
```


---

##### Limitations  
- **Missing `response_time` in Most HAR Files:** The script relies on the `"total"` field inside `"timings"` to extract response time. However, most HAR files either lack this field or set it to `null`, resulting in incomplete performance data and making request performance analysis unreliable. 

