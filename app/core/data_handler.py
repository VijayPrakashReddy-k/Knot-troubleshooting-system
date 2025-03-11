import logging
from pathlib import Path
from app.core.parse_har import parse_har_files
from app.core.parse_logs import parse_log_files

logger = logging.getLogger(__name__)

class DataHandler:
    def __init__(self):
        """Initialize data handler"""
        pass

    def process_files(self, har_files=None, log_files=None):
        """Process HAR and log files"""
        try:
            results = {
                'har': {'processed': 0, 'skipped': 0, 'errors': 0},
                'log': {'processed': 0, 'errors': 0}
            }

            # Process HAR files
            har_entries = parse_har_files(har_files)
            for entry in har_entries:
                try:
                    results['har']['processed'] += 1
                except Exception as e:
                    logger.error(f"Error processing HAR entry: {e}")
                    results['har']['errors'] += 1

            # Process log files
            log_entries = parse_log_files(log_files)
            for entry in log_entries:
                try:
                    results['log']['processed'] += 1
                except Exception as e:
                    logger.error(f"Error processing log entry: {e}")
                    results['log']['errors'] += 1

            return results

        except Exception as e:
            logger.error(f"Error in process_files: {e}")
            raise 