import os
import time
import random
import requests
import uuid
from datetime import datetime, timedelta
import socket

INGESTOR_HOST = os.getenv('INGESTOR_HOST', 'localhost')
INGESTOR_PORT = os.getenv('INGESTOR_PORT', '8000')
LOG_GENERATION_INTERVAL = float(os.getenv('LOG_GENERATION_INTERVAL', '0.1'))
TIME_JITTER_SECONDS = int(os.getenv('TIME_JITTER_SECONDS', '30'))

INGESTOR_URL = f'http://{INGESTOR_HOST}:{INGESTOR_PORT}/logs'

SERVICES = ['payment-service', 'api-gateway', 'user-service', 'auth-service', 'database-service']
LOG_LEVELS = ['INFO', 'ERROR', 'WARNING', 'DEBUG']
NGINX_STATUS_CODES = [200, 201, 400, 401, 403, 404, 500, 502, 503]
NGINX_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
NGINX_PATHS = ['/api/v2/users', '/api/v1/auth', '/health', '/metrics', '/logs', '/data', '/admin']
USER_AGENTS = ['Mozilla/5.0', 'curl/7.68.0', 'Python-requests/2.28.0', 'Go-http-client/1.1']

ERROR_MESSAGES = [
    'Database connection timed out',
    'Failed to authenticate user',
    'Request timeout',
    'Invalid request format',
    'Service unavailable',
    'Internal server error',
    'Connection refused',
    'Permission denied',
]

hostname = socket.gethostname()

def generate_nginx_log():
    timestamp = datetime.utcnow() + timedelta(seconds=random.randint(-TIME_JITTER_SECONDS, TIME_JITTER_SECONDS))
    timestamp_str = timestamp.strftime('%d/%b/%Y:%H:%M:%S +0000')
    
    method = random.choice(NGINX_METHODS)
    path = random.choice(NGINX_PATHS)
    status = random.choice(NGINX_STATUS_CODES)
    bytes_sent = random.randint(100, 10000)
    user_agent = random.choice(USER_AGENTS)
    
    log = f'127.0.0.1 - - [{timestamp_str}] "{method} {path} HTTP/1.1" {status} {bytes_sent} "-" "{user_agent}"'
    return log, timestamp

def generate_json_log():
    timestamp = datetime.utcnow() + timedelta(seconds=random.randint(-TIME_JITTER_SECONDS, TIME_JITTER_SECONDS))
    timestamp_str = timestamp.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    service = random.choice(SERVICES)
    level = random.choice(LOG_LEVELS)
    trace_id = f'trace-{uuid.uuid4().hex[:12]}'
    message = random.choice(ERROR_MESSAGES) if level == 'ERROR' else f'Request processed: {uuid.uuid4().hex[:8]}'
    
    log = f'{{"timestamp": "{timestamp_str}", "level": "{level}", "service": "{service}", "trace_id": "{trace_id}", "message": "{message}"}}'
    return log, timestamp

def generate_syslog_log():
    timestamp = datetime.utcnow() + timedelta(seconds=random.randint(-TIME_JITTER_SECONDS, TIME_JITTER_SECONDS))
    timestamp_str = timestamp.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    service = random.choice(SERVICES)
    message = random.choice(ERROR_MESSAGES)
    priority = random.randint(16, 63)
    
    log = f'<{priority}>1 {timestamp_str} {hostname} {service} - - - {message}'
    return log, timestamp

def send_log(log_line, event_timestamp):
    try:
        request_id = str(uuid.uuid4())
        headers = {'X-Request-ID': request_id}
        response = requests.post(INGESTOR_URL, data=log_line, headers=headers, timeout=5)
        if response.status_code in [200, 202]:
            print(f'[{datetime.utcnow().isoformat()}] Sent log: {log_line[:80]}...')
        else:
            print(f'[{datetime.utcnow().isoformat()}] Failed to send log: {response.status_code}')
    except Exception as e:
        print(f'[{datetime.utcnow().isoformat()}] Error sending log: {str(e)}')

def main():
    print(f'Log Generator started. Ingestor URL: {INGESTOR_URL}')
    print(f'Time Jitter: ±{TIME_JITTER_SECONDS} seconds')
    
    log_generators = [generate_nginx_log, generate_json_log, generate_syslog_log]
    
    while True:
        try:
            generator = random.choice(log_generators)
            log_line, event_timestamp = generator()
            send_log(log_line, event_timestamp)
            time.sleep(LOG_GENERATION_INTERVAL)
        except KeyboardInterrupt:
            print('Log Generator stopped')
            break
        except Exception as e:
            print(f'Error in main loop: {str(e)}')
            time.sleep(1)

if __name__ == '__main__':
    main()
