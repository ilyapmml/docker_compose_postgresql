import os
import time
import numpy as np 
import seaborn as sns
import redis
import psycopg2
from flask import Flask, jsonify
from flask import request

app = Flask(__name__)
redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'))


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'appdb'),
        user=os.getenv('POSTGRES_USER', 'app_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'secret'))


def initilization():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS visits (
            id SERIAL PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
    ''')
    cur.execute("INSERT INTO visits (count) SELECT 0 WHERE NOT EXISTS (SELECT 1 FROM visits)")
    conn.commit()
    cur.close()
    conn.close()

initilization()

@app.route('/')
def home():
    app_name = os.getenv('APP_NAME', 'MyApp')
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>{app_name}</title></head>
    <body>
        <h1>{app_name}</h1>
        <p>my homework is glad to see you))</p>
        <ul>
            <li><a href="/visits">/visits</a> — счётчик посещений</li>
            <li><a href="/health">/health</a> — статус сервисов</li>
        </ul>
    </body>
    </html>
    '''

@app.route('/visits')
def visits():
    cached_count = redis_client.get('visit_count')
    if cached_count is not None:
        return jsonify({'total': int(cached_count), 'cached': True})
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE visits SET count = count + 1 RETURNING count")
    new_count = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    
    redis_client.setex('visit_count', 10, new_count)
    a = jsonify({'total': new_count, 'cached': False})
    return a
@app.route('/health')
def health():
    status = {'status': 'ok', 'db': 'disconnected', 'redis': 'disconnected'}
    
    #  Postgre
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.close()
        conn.close()
        status['db'] = 'connected'
    except Exception as e:
        status['status'] = 'degraded'
    try:
        redis_client.ping()
        status['redis'] = 'connected'
    except Exception as e:
        status['status'] = 'degraded'
    
    return jsonify(status)





if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)






