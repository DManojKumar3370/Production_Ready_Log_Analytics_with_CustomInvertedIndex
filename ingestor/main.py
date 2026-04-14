import os
import json
import time
from datetime import datetime, timedelta, timezone
from collections import deque
from threading import Lock
from http.server import HTTPServer, BaseHTTPRequestHandler
import re

BUFFER_WINDOW_SECONDS = int(os.getenv('BUFFER_WINDOW_SECONDS', '60'))
DATA_DIR = os.getenv('DATA_DIR', '/app/data')

log_buffer = {}
seen_ids = {}
buffer_lock = Lock()

def parse_timestamp(log_line):
    try:
        if log_line.startswith('{'):
            log_obj = json.loads(log_line)
            timestamp_str = log_obj.get('timestamp', '')
            if timestamp_str:
                if timestamp_str.endswith('Z'):
                    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(timestamp_str)
        elif log_line.startswith('<'):
            match = re.search(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})', log_line)
            if match:
                ts_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}T{match.group(4)}:{match.group(5)}:{match.group(6)}"
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                return ts
        else:
            match = re.search(r'\[(\d{2})/(\w{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2})', log_line)
            if match:
                day, month_str, year, hour, minute, second = match.groups()
                months = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                         'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
                month = months.get(month_str, 1)
                ts = datetime(int(year), month, int(day), int(hour), int(minute), int(second), tzinfo=timezone.utc)
                return ts
    except:
        pass
    return datetime.now(timezone.utc)

class LogIngestorHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/logs':
            content_length = int(self.headers.get('Content-Length', 0))
            log_line = self.rfile.read(content_length).decode('utf-8').strip()
            request_id = self.headers.get('X-Request-ID', '')
            
            timestamp = parse_timestamp(log_line)
            
            with buffer_lock:
                if request_id and request_id in seen_ids:
                    self.send_response(202)
                    self.end_headers()
                    return
                
                if request_id:
                    seen_ids[request_id] = time.time()
                
                log_buffer[request_id] = {
                    'log': log_line,
                    'timestamp': timestamp,
                    'received_at': datetime.now(timezone.utc),
                    'request_id': request_id
                }
            
            self.send_response(202)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'accepted'}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        if self.path == '/logs/batch':
            with buffer_lock:
                now = datetime.now(timezone.utc)
                window_start = now - timedelta(seconds=BUFFER_WINDOW_SECONDS)
                
                ready_logs = []
                for req_id, entry in list(log_buffer.items()):
                    if entry['timestamp'] < window_start:
                        ready_logs.append(entry)
                        del log_buffer[req_id]
                
                ready_logs.sort(key=lambda x: x['timestamp'])
                
                response = [
                    {
                        'log': item['log'],
                        'timestamp': item['timestamp'].isoformat() + 'Z',
                        'request_id': item['request_id']
                    }
                    for item in ready_logs
                ]
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        
        elif self.path == '/health':
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
    port = 8000
    server = HTTPServer(('0.0.0.0', port), LogIngestorHandler)
    print(f'Ingestor service started on port {port}')
    print(f'Buffer window: {BUFFER_WINDOW_SECONDS} seconds')
    server.serve_forever()

if __name__ == '__main__':
    main()
