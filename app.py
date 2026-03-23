from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from datetime import date
import os

app = Flask(__name__, static_folder='.')
CORS(app)

# ─── DB CONFIG ─────────────────────────────────────────────
DB_CONFIG = {
    'host': os.environ.get('MYSQLHOST', 'localhost'),
    'port': int(os.environ.get('MYSQLPORT', 3306)),
    'database': os.environ.get('MYSQLDATABASE', 'habit_tracker_db'),
    'user': os.environ.get('MYSQLUSER', 'root'),
    'password': os.environ.get('MYSQLPASSWORD', 'Pass@8898')
}
def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

# ─── INIT DATABASE ─────────────────────────────────────────
def init_db():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                category VARCHAR(50) DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                activity_id INT NOT NULL,
                duration_minutes INT NOT NULL,
                notes TEXT,
                log_date DATE NOT NULL,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sleep_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sleep_date DATE NOT NULL UNIQUE,
                bedtime VARCHAR(10),
                wake_time VARCHAR(10),
                duration_hours FLOAT,
                quality ENUM('poor', 'fair', 'good', 'excellent') DEFAULT 'good',
                notes TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                learn_date DATE NOT NULL,
                topic VARCHAR(200) NOT NULL,
                description TEXT,
                category VARCHAR(50) DEFAULT 'general',
                time_spent_minutes INT DEFAULT 0,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        print("✅ Database initialized successfully")
    except Error as e:
        print(f"❌ DB Error: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# ─── SERVE FRONTEND ────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# ═══════════════════════════════════════════════════════════
#  ACTIVITIES
# ═══════════════════════════════════════════════════════════

@app.route('/api/activities', methods=['GET'])
def get_activities():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM activities ORDER BY name")
        return jsonify(cursor.fetchall())
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/activities', methods=['POST'])
def add_activity():
    conn = None
    data = request.json
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO activities (name, category) VALUES (%s, %s)",
            (data['name'], data.get('category', 'general'))
        )
        conn.commit()
        return jsonify({'id': cursor.lastrowid, 'message': 'Activity added'}), 201
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/activities/<int:aid>', methods=['DELETE'])
def delete_activity(aid):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM activities WHERE id=%s", (aid,))
        conn.commit()
        return jsonify({'message': 'Deleted'})
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# ─── ACTIVITY LOGS ─────────────────────────────────────────

@app.route('/api/activity-logs', methods=['POST'])
def log_activity():
    conn = None
    data = request.json
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO activity_logs (activity_id, duration_minutes, notes, log_date) VALUES (%s,%s,%s,%s)",
            (data['activity_id'], data['duration_minutes'],
             data.get('notes', ''), data.get('log_date', str(date.today())))
        )
        conn.commit()
        return jsonify({'message': 'Logged'}), 201
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/activity-logs', methods=['GET'])
def get_activity_logs():
    conn = None
    days = int(request.args.get('days', 7))
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT al.*, a.name as activity_name, a.category
            FROM activity_logs al
            JOIN activities a ON al.activity_id = a.id
            WHERE al.log_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            ORDER BY al.log_date DESC, al.logged_at DESC
        """, (days,))
        rows = cursor.fetchall()
        for r in rows:
            if hasattr(r.get('log_date'), 'isoformat'):
                r['log_date'] = r['log_date'].isoformat()
            if hasattr(r.get('logged_at'), 'isoformat'):
                r['logged_at'] = r['logged_at'].isoformat()
        return jsonify(rows)
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/activity-stats', methods=['GET'])
def get_activity_stats():
    conn = None
    days = int(request.args.get('days', 7))
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.name, a.category,
                   SUM(al.duration_minutes) as total_minutes,
                   COUNT(*) as sessions,
                   AVG(al.duration_minutes) as avg_minutes
            FROM activity_logs al
            JOIN activities a ON al.activity_id = a.id
            WHERE al.log_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY a.id, a.name, a.category
            ORDER BY total_minutes DESC
        """, (days,))
        return jsonify(cursor.fetchall())
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/activity-daily', methods=['GET'])
def get_daily_activity():
    conn = None
    days = int(request.args.get('days', 7))
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT al.log_date, a.name,
                   SUM(al.duration_minutes) as total_minutes
            FROM activity_logs al
            JOIN activities a ON al.activity_id = a.id
            WHERE al.log_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY al.log_date, a.id, a.name
            ORDER BY al.log_date ASC
        """, (days,))
        rows = cursor.fetchall()
        for r in rows:
            if hasattr(r.get('log_date'), 'isoformat'):
                r['log_date'] = r['log_date'].isoformat()
        return jsonify(rows)
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# ═══════════════════════════════════════════════════════════
#  SLEEP
# ═══════════════════════════════════════════════════════════

@app.route('/api/sleep', methods=['POST'])
def log_sleep():
    conn = None
    data = request.json
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sleep_logs (sleep_date, bedtime, wake_time, duration_hours, quality, notes)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
            bedtime=%s, wake_time=%s, duration_hours=%s, quality=%s, notes=%s
        """, (
            data.get('sleep_date', str(date.today())),
            data.get('bedtime'), data.get('wake_time'),
            data.get('duration_hours'), data.get('quality', 'good'),
            data.get('notes', ''),
            data.get('bedtime'), data.get('wake_time'),
            data.get('duration_hours'), data.get('quality', 'good'),
            data.get('notes', '')
        ))
        conn.commit()
        return jsonify({'message': 'Sleep logged'}), 201
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/sleep', methods=['GET'])
def get_sleep():
    conn = None
    days = int(request.args.get('days', 14))
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM sleep_logs
            WHERE sleep_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            ORDER BY sleep_date ASC
        """, (days,))
        rows = cursor.fetchall()
        for r in rows:
            if hasattr(r.get('sleep_date'), 'isoformat'):
                r['sleep_date'] = r['sleep_date'].isoformat()
            if hasattr(r.get('logged_at'), 'isoformat'):
                r['logged_at'] = r['logged_at'].isoformat()
        return jsonify(rows)
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# ═══════════════════════════════════════════════════════════
#  LEARNING
# ═══════════════════════════════════════════════════════════

@app.route('/api/learning', methods=['POST'])
def log_learning():
    conn = None
    data = request.json
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO learning_logs (learn_date, topic, description, category, time_spent_minutes)
            VALUES (%s,%s,%s,%s,%s)
        """, (
            data.get('learn_date', str(date.today())),
            data['topic'], data.get('description', ''),
            data.get('category', 'general'),
            data.get('time_spent_minutes', 0)
        ))
        conn.commit()
        return jsonify({'id': cursor.lastrowid, 'message': 'Learning logged'}), 201
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/learning', methods=['GET'])
def get_learning():
    conn = None
    days = int(request.args.get('days', 7))
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM learning_logs
            WHERE learn_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            ORDER BY learn_date DESC, logged_at DESC
        """, (days,))
        rows = cursor.fetchall()
        for r in rows:
            if hasattr(r.get('learn_date'), 'isoformat'):
                r['learn_date'] = r['learn_date'].isoformat()
            if hasattr(r.get('logged_at'), 'isoformat'):
                r['logged_at'] = r['logged_at'].isoformat()
        return jsonify(rows)
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/learning/<int:lid>', methods=['DELETE'])
def delete_learning(lid):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM learning_logs WHERE id=%s", (lid,))
        conn.commit()
        return jsonify({'message': 'Deleted'})
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# ═══════════════════════════════════════════════════════════
#  DASHBOARD SUMMARY
# ═══════════════════════════════════════════════════════════

@app.route('/api/summary/today', methods=['GET'])
def today_summary():
    conn = None
    today = str(date.today())
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT COALESCE(SUM(al.duration_minutes),0) as total_activity_mins,
                   COUNT(DISTINCT al.activity_id) as activities_done
            FROM activity_logs al WHERE al.log_date=%s
        """, (today,))
        activity = cursor.fetchone()

        cursor.execute("SELECT * FROM sleep_logs WHERE sleep_date=%s", (today,))
        sleep = cursor.fetchone()
        if sleep and hasattr(sleep.get('sleep_date'), 'isoformat'):
            sleep['sleep_date'] = sleep['sleep_date'].isoformat()

        cursor.execute("""
            SELECT COUNT(*) as topics_learned,
                   COALESCE(SUM(time_spent_minutes),0) as learning_mins
            FROM learning_logs WHERE learn_date=%s
        """, (today,))
        learning = cursor.fetchone()

        return jsonify({
            'date': today,
            'activity': activity,
            'sleep': sleep,
            'learning': learning
        })
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# ─── RUN ───────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)