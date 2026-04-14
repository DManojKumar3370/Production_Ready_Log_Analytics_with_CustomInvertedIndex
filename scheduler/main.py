import os
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Thread
import schedule
import logging

DATA_DIR = os.getenv('DATA_DIR', '/app/data')
REPORTS_DIR = os.getenv('REPORTS_DIR', '/app/reports')
REPORT_TIME = os.getenv('REPORT_TIME', '00:00')

docs_dir = os.path.join(DATA_DIR, 'docs')
os.makedirs(REPORTS_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

def load_document(doc_id):
    doc_path = os.path.join(docs_dir, f'{doc_id}.json')
    if os.path.exists(doc_path):
        try:
            with open(doc_path, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def generate_daily_report():
    logger.info('Generating daily report')
    
    today = datetime.utcnow().date()
    today_dir = os.path.join(REPORTS_DIR, today.strftime('%Y-%m-%d'))
    os.makedirs(today_dir, exist_ok=True)
    
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())
    
    service_stats = defaultdict(lambda: {
        'total_events': 0,
        'error_count': 0,
        'error_messages': defaultdict(int),
        'ingestion_latencies': []
    })
    
    if not os.path.exists(docs_dir):
        logger.warning('Documents directory does not exist')
        return
    
    try:
        for filename in os.listdir(docs_dir):
            if filename.endswith('.json'):
                doc = load_document(filename[:-5])
                if not doc:
                    continue
                
                try:
                    doc_timestamp = datetime.fromisoformat(doc.get('timestamp', '').replace('Z', '+00:00'))
                    if not (start_of_day <= doc_timestamp <= end_of_day):
                        continue
                except:
                    continue
                
                service = doc.get('service', 'unknown')
                level = doc.get('level', 'INFO')
                message = doc.get('message', '')
                
                service_stats[service]['total_events'] += 1
                
                if level == 'ERROR':
                    service_stats[service]['error_count'] += 1
                    service_stats[service]['error_messages'][message] += 1
                
                ingestion_latency = 0
                service_stats[service]['ingestion_latencies'].append(ingestion_latency)
        
        for service, stats in service_stats.items():
            total_events = stats['total_events']
            error_count = stats['error_count']
            error_rate = error_count / total_events if total_events > 0 else 0
            
            top_errors = sorted(
                stats['error_messages'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            p95_latency = 0
            if stats['ingestion_latencies']:
                sorted_latencies = sorted(stats['ingestion_latencies'])
                p95_index = int(len(sorted_latencies) * 0.95)
                p95_latency = sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else 0
            
            report = {
                'service_name': service,
                'report_date': today.isoformat(),
                'total_events': total_events,
                'error_rate': round(error_rate, 4),
                'top_10_error_messages': [
                    {'message': msg, 'count': count}
                    for msg, count in top_errors
                ],
                'p95_ingestion_latency_ms': p95_latency
            }
            
            report_file = os.path.join(today_dir, f'{service}.json')
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f'Generated report for {service}')
    
    except Exception as e:
        logger.error(f'Error generating report: {e}')

def schedule_daily_report():
    logger.info(f'Scheduled daily report at {REPORT_TIME}')
    schedule.every().day.at(REPORT_TIME).do(generate_daily_report)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def main():
    logger.info('Scheduler service started')
    logger.info(f'Reports directory: {REPORTS_DIR}')
    
    report_thread = Thread(target=schedule_daily_report, daemon=True)
    report_thread.start()
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info('Scheduler stopped')

if __name__ == '__main__':
    main()
