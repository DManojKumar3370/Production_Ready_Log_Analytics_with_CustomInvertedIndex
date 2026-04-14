import os
import sys
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict
import argparse

DATA_DIR = os.getenv('DATA_DIR', '/app/data')
docs_dir = os.path.join(DATA_DIR, 'docs')
index_dir = os.path.join(DATA_DIR, 'index')
index_file = os.path.join(index_dir, 'inverted_index.json')

def load_index():
    if os.path.exists(index_file):
        try:
            with open(index_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def load_document(doc_id):
    doc_path = os.path.join(docs_dir, f'{doc_id}.json')
    if os.path.exists(doc_path):
        try:
            with open(doc_path, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def tokenize(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    tokens = text.split()
    return [t for t in tokens if len(t) > 0]

def search_inverted_index(keywords):
    index = load_index()
    tokens = tokenize(keywords)
    
    if not tokens:
        return []
    
    doc_sets = []
    for token in tokens:
        if token in index:
            doc_sets.append(set(index[token]))
        else:
            return []
    
    result_ids = set.intersection(*doc_sets) if doc_sets else set()
    return list(result_ids)

def filter_documents(level=None, service=None, from_time=None, to_time=None):
    docs = []
    if not os.path.exists(docs_dir):
        return docs
    
    try:
        for filename in os.listdir(docs_dir):
            if filename.endswith('.json'):
                doc = load_document(filename[:-5])
                if not doc:
                    continue
                
                if level and doc.get('level') != level:
                    continue
                if service and doc.get('service') != service:
                    continue
                
                if from_time or to_time:
                    try:
                        doc_timestamp = datetime.fromisoformat(doc.get('timestamp', '').replace('Z', '+00:00'))
                        if from_time and doc_timestamp < from_time:
                            continue
                        if to_time and doc_timestamp > to_time:
                            continue
                    except:
                        continue
                
                docs.append(doc)
    except:
        pass
    
    return docs

def search_command(keywords, level=None, service=None, from_time=None, to_time=None, limit=100):
    doc_ids = search_inverted_index(keywords)
    
    results = []
    for doc_id in doc_ids:
        doc = load_document(doc_id)
        if not doc:
            continue
        
        if level and doc.get('level') != level:
            continue
        if service and doc.get('service') != service:
            continue
        
        if from_time or to_time:
            try:
                doc_timestamp = datetime.fromisoformat(doc.get('timestamp', '').replace('Z', '+00:00'))
                if from_time and doc_timestamp < from_time:
                    continue
                if to_time and doc_timestamp > to_time:
                    continue
            except:
                continue
        
        results.append(doc)
    
    results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return results[:limit]

def filter_command(level=None, service=None, from_time=None, to_time=None, limit=100):
    docs = filter_documents(level=level, service=service, from_time=from_time, to_time=to_time)
    docs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return docs[:limit]

def aggregate_command(fields, duration_str, group_by_fields):
    duration_mapping = {
        's': 'seconds',
        'm': 'minutes',
        'h': 'hours',
        'd': 'days',
        'w': 'weeks'
    }
    
    match = re.match(r'(\d+)([smhdw])', duration_str)
    if not match:
        print('Invalid duration format. Use format like 1h, 30m, 7d')
        return
    
    value, unit = match.groups()
    value = int(value)
    unit = duration_mapping.get(unit, 'hours')
    
    if unit == 'seconds':
        delta = timedelta(seconds=value)
    elif unit == 'minutes':
        delta = timedelta(minutes=value)
    elif unit == 'hours':
        delta = timedelta(hours=value)
    elif unit == 'days':
        delta = timedelta(days=value)
    else:
        delta = timedelta(weeks=value)
    
    from_time = datetime.utcnow() - delta
    
    docs = filter_documents(from_time=from_time)
    
    counters = defaultdict(int)
    for doc in docs:
        key_parts = []
        for field in group_by_fields:
            key_parts.append(doc.get(field, 'unknown'))
        key = tuple(key_parts)
        counters[key] += 1
    
    print(f'\n{"| " + " | ".join(group_by_fields + ["count"]) + " |"}')
    print(f'|{"-" * (sum(max(len(str(f)), 10) for f in group_by_fields) + len(group_by_fields) * 3 + 10)}|')
    
    sorted_results = sorted(counters.items(), key=lambda x: x[1], reverse=True)
    for key, count in sorted_results:
        row_parts = list(key) + [str(count)]
        print(f'| {" | ".join(str(p).ljust(10) for p in row_parts)} |')
    print()

def parse_iso_duration(duration_str):
    match = re.match(r'(\d+)([smhdw])', duration_str)
    if not match:
        return None
    value, unit = match.groups()
    value = int(value)
    
    if unit == 's':
        return timedelta(seconds=value)
    elif unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    elif unit == 'w':
        return timedelta(weeks=value)
    return None

def main():
    parser = argparse.ArgumentParser(prog='query', description='Query logs')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    search_parser = subparsers.add_parser('search', help='Search for keywords')
    search_parser.add_argument('keywords', help='Keywords to search')
    search_parser.add_argument('--level', help='Filter by level')
    search_parser.add_argument('--service', help='Filter by service')
    search_parser.add_argument('--from', dest='from_time', help='From timestamp (ISO 8601)')
    search_parser.add_argument('--to', dest='to_time', help='To timestamp (ISO 8601)')
    search_parser.add_argument('--limit', type=int, default=100, help='Limit results')
    
    filter_parser = subparsers.add_parser('filter', help='Filter logs')
    filter_parser.add_argument('--level', help='Filter by level')
    filter_parser.add_argument('--service', help='Filter by service')
    filter_parser.add_argument('--from', dest='from_time', help='From timestamp (ISO 8601)')
    filter_parser.add_argument('--to', dest='to_time', help='To timestamp (ISO 8601)')
    filter_parser.add_argument('--limit', type=int, default=100, help='Limit results')
    
    agg_parser = subparsers.add_parser('aggregate', help='Aggregate logs')
    agg_parser.add_argument('agg_type', help='Aggregation type (count)')
    agg_parser.add_argument('--by', dest='group_by', required=True, help='Group by fields (comma-separated)')
    agg_parser.add_argument('--last', required=True, help='Time duration (1h, 30m, 7d, etc)')
    
    if len(sys.argv) < 2:
        parser.print_help()
        return
    
    args = parser.parse_args()
    
    if args.command == 'search':
        from_time = None
        to_time = None
        if args.from_time:
            from_time = datetime.fromisoformat(args.from_time.replace('Z', '+00:00'))
        if args.to_time:
            to_time = datetime.fromisoformat(args.to_time.replace('Z', '+00:00'))
        
        results = search_command(
            args.keywords,
            level=args.level,
            service=args.service,
            from_time=from_time,
            to_time=to_time,
            limit=args.limit
        )
        
        print(f'Found {len(results)} results:\n')
        for doc in results:
            print(json.dumps(doc, indent=2))
            print()
    
    elif args.command == 'filter':
        from_time = None
        to_time = None
        if args.from_time:
            from_time = datetime.fromisoformat(args.from_time.replace('Z', '+00:00'))
        if args.to_time:
            to_time = datetime.fromisoformat(args.to_time.replace('Z', '+00:00'))
        
        results = filter_command(
            level=args.level,
            service=args.service,
            from_time=from_time,
            to_time=to_time,
            limit=args.limit
        )
        
        print(f'Found {len(results)} results:\n')
        for doc in results:
            print(json.dumps(doc, indent=2))
            print()
    
    elif args.command == 'aggregate':
        if args.agg_type != 'count':
            print('Only count aggregation is supported')
            return
        
        group_by_fields = [f.strip() for f in args.group_by.split(',')]
        aggregate_command('count', args.last, group_by_fields)

if __name__ == '__main__':
    main()
