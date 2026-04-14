import os
import json
import time
import re
import uuid
import requests
from datetime import datetime, timedelta
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging

INGESTOR_HOST = os.getenv('INGESTOR_HOST', 'localhost')
INGESTOR_PORT = os.getenv('INGESTOR_PORT', '8000')
DATA_DIR = os.getenv('DATA_DIR', '/app/data')
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '1000'))
INDEX_CHECK_INTERVAL = int(os.getenv('INDEX_CHECK_INTERVAL', '5'))

INGESTOR_URL = f'http://{INGESTOR_HOST}:{INGESTOR_PORT}/logs/batch'

docs_dir = os.path.join(DATA_DIR, 'docs')
index_dir = os.path.join(DATA_DIR, 'index')
os.makedirs(docs_dir, exist_ok=True)
os.makedirs(index_dir, exist_ok=True)

index_file = os.path.join(index_dir, 'inverted_index.json')

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

inverted_index = {}

def load_index():
    global inverted_index
    if os.path.exists(index_file):
        try:
            with open(index_file, 'r') as f:
                inverted_index = json.load(f)
            logger.info(f'Loaded index with {len(inverted_index)} tokens')
        except Exception as e:
            logger.error(f'Error loading index: {e}')
            inverted_index = {}
    else:
        inverted_index = {}

def save_index():
    try:
        temp_file = index_file + '.tmp'
        with open(temp_file, 'w') as f:
            json.dump(inverted_index, f)
        os.replace(temp_file, index_file)
    except Exception as e:
        logger.error(f'Error saving index: {e}')

def tokenize(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    tokens = text.split()
    return [t for t in tokens if len(t) > 0]

def parse_nginx_log(log_line):
    try:
        match = re.match(
            r'(\d+\.\d+\.\d+\.\d+)\s+-\s+-\s+\[(.*?)\]\s+"(\w+)\s+([^\s]+)\s+HTTP\/[\d.]+"\s+(\d+)\s+(\d+)',
            log_line
        )
        if match:
            ip, timestamp_str, method, path, status, bytes_sent = match.groups()
            
            months = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                     'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
            
            parts = timestamp_str.split('/')
            day = int(parts[0])
            month = months.get(parts[1], 1)
            year_and_time = parts[2].split(':')
            year = int(year_and_time[0])
            hour = int(year_and_time[1])
            minute = int(year_and_time[2])
            second = int(year_and_time[3])
            
            dt = datetime(year, month, day, hour, minute, second)
            iso_timestamp = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            level = 'ERROR' if int(status) >= 400 else 'INFO'
            message = f'{method} {path} - {status}'
            
            return {
                'timestamp': iso_timestamp,
                'log_type': 'nginx',
                'level': level,
                'service': 'nginx-ingress',
                'message': message,
                'http_status': int(status),
                'bytes_sent': int(bytes_sent),
                'raw': log_line
            }
    except Exception as e:
        logger.debug(f'Error parsing nginx log: {e}')
    return None

def parse_json_log(log_line):
    try:
        obj = json.loads(log_line)
        timestamp = obj.get('timestamp', datetime.utcnow().isoformat() + 'Z')
        if not timestamp.endswith('Z'):
            timestamp = timestamp.replace('+00:00', 'Z')
            if 'Z' not in timestamp:
                timestamp = timestamp + 'Z'
        
        return {
            'timestamp': timestamp,
            'log_type': 'json',
            'level': obj.get('level', 'INFO'),
            'service': obj.get('service', 'unknown'),
            'message': obj.get('message', ''),
            'raw': log_line
        }
    except Exception as e:
        logger.debug(f'Error parsing JSON log: {e}')
    return None

def parse_syslog_log(log_line):
    try:
        if log_line.startswith('<'):
            match = re.match(
                r'<(\d+)>(\d+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+-\s+-\s+-\s+(.*)',
                log_line
            )
            if match:
                priority, version, timestamp_str, hostname, app_name, message = match.groups()
                
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                iso_timestamp = dt.strftime('%Y-%m-%dT%H:%M:%S') + '.000Z'
                
                level = 'ERROR' if 'error' in message.lower() else 'INFO'
                
                return {
                    'timestamp': iso_timestamp,
                    'log_type': 'syslog',
                    'level': level,
                    'service': app_name,
                    'message': message,
                    'raw': log_line
                }
    except Exception as e:
        logger.debug(f'Error parsing syslog log: {e}')
    return None

def detect_and_parse_log(log_line):
    if log_line.startswith('{'):
        parsed = parse_json_log(log_line)
    elif log_line.startswith('<'):
        parsed = parse_syslog_log(log_line)
    else:
        parsed = parse_nginx_log(log_line)
    
    if parsed is None:
        return None
    
    doc_id = str(uuid.uuid4())
    parsed['id'] = doc_id
    
    return parsed

def update_index(doc_id, message):
    tokens = tokenize(message)
    for token in tokens:
        if token not in inverted_index:
            inverted_index[token] = []
        if doc_id not in inverted_index[token]:
            inverted_index[token].append(doc_id)

def store_document(parsed_log):
    doc_id = parsed_log['id']
    doc_path = os.path.join(docs_dir, f'{doc_id}.json')
    with open(doc_path, 'w') as f:
        json.dump(parsed_log, f)
    return doc_id

def process_batch():
    try:
        response = requests.get(INGESTOR_URL, timeout=5)
        if response.status_code == 200:
            batch = response.json()
            if batch:
                logger.info(f'Fetched batch of {len(batch)} logs')
                for entry in batch:
                    log_line = entry['log']
                    parsed = detect_and_parse_log(log_line)
                    if parsed:
                        doc_id = store_document(parsed)
                        update_index(doc_id, parsed['message'])
                
                save_index()
    except Exception as e:
        logger.error(f'Error processing batch: {e}')

def indexing_loop():
    logger.info('Indexing loop started')
    while True:
        process_batch()
        time.sleep(INDEX_CHECK_INTERVAL)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'healthy'}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

def main():
    load_index()
    
    health_thread = Thread(target=lambda: HTTPServer(('0.0.0.0', 8001), HealthHandler).serve_forever(), daemon=True)
    health_thread.start()
    logger.info('Health check server started on port 8001')
    
    index_thread = Thread(target=indexing_loop, daemon=True)
    index_thread.start()
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info('Indexer stopped')

if __name__ == '__main__':
    main()
