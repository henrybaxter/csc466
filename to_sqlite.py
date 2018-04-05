import json
import sqlite3
import os


def convert_to_sqlite():
    treatments = json.load(open('data/treatments.json'))
    os.remove('data/treatments.sqlite')
    conn = sqlite3.connect('data/treatments.sqlite')
    c = conn.cursor()
    c.execute("""
        CREATE TABLE treatments (
            protocol, varying, rate_limit, latency, packet_loss,
            object_count, object_size, page_load_time
        )
    """)
    for t in treatments:
        for result in t['results']:
            c.execute(
                'INSERT INTO treatments VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (t['protocol'], t['varying'], t['rate-limit'], t['latency'], t['packet-loss'],
                 t['object-count'], t['object-size'], result)
            )
    conn.commit()


if __name__ == '__main__':
    convert_to_sqlite()
