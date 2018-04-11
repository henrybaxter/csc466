import json
import sqlite3
import os
import csv
import numpy as np


def convert_data():
    for environment in os.listdir('data'):
        if environment == '.DS_Store':
            continue
        print('Converting', environment)
        root = os.path.join('data', environment)
        in_path = os.path.join(root, 'results.json')
        results = json.load(open(in_path))
        csv_path = os.path.join(root, 'results.csv')
        csv_summary_path = os.path.join(root, 'summary.csv')
        sqlite_path = os.path.join(root, 'results.sqlite')
        try:
            os.remove(sqlite_path)
        except FileNotFoundError:
            pass
        fieldnames = ['environment', 'protocol', 'varying',
                      'object-count', 'object-size',
                      'rate-limit',
                      'delay-time', 'delay-jitter', 'delay-correlation', 'delay-distribution',
                      'loss-p', 'loss-r', 'loss-h', 'loss-k',
                      'corrupt-percent', 'corrupt-correlation',
                      'duplicate-percent', 'duplicate-correlation',
                      'page-load-time']

        with open(csv_path, 'w') as ofp:
            writer = csv.DictWriter(ofp, fieldnames=fieldnames)
            writer.writeheader()
            rows = []
            for treatment in results['treatments']:
                for page_load_time in treatment['page-load-times']:
                    row = treatment.copy()
                    row.pop('page-load-times')
                    row['page-load-time'] = page_load_time
                    rows.append(row)
            writer.writerows(rows)

        with open(csv_summary_path, 'w') as ofp:
            writer = csv.DictWriter(ofp, fieldnames=fieldnames + ['page-load-time-standard-deviation'])
            writer.writeheader()
            rows = []
            for treatment in results['treatments']:
                row = treatment.copy()
                row.pop('page-load-times')
                row['page-load-time'] = np.mean(treatment['page-load-times'])
                row['page-load-time-standard-deviation'] = np.std(treatment['page-load-times'])
                rows.append(row)
            writer.writerows(rows)

        '''
        conn = sqlite3.connect(sqlite_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE treatments (
                protocol, varying, rate_limit, latency, packet_loss,
                object_count, object_size, page_load_time
            )
        """)
        for t in results['treatments']:
            for page_load_time in t['page-load-times']:
                c.execute(
                    'INSERT INTO treatments VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (t['protocol'], t['varying'], t['rate-limit'], t['latency'], t['packet-loss'],
                     t['object-count'], t['object-size'], page_load_time)
                )
        conn.commit()
        '''


if __name__ == '__main__':
    convert_data()
