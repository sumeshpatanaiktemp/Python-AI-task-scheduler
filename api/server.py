from flask import Flask, jsonify
from database.db import DatabaseManager

app = Flask(__name__)
db = DatabaseManager()

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    tasks = db.get_all_tasks()
    return jsonify(tasks)


def start_api_server():
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
