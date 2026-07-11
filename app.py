import os
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory, g

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
DATA_DIR = Path(os.environ.get('DATA_DIR', '/data'))
UPLOAD_DIR = DATA_DIR / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / 'inventory_v2.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(str(DB_PATH))
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(_e=None):
    db = g.pop('db', None)
    if db: db.close()

def init_db():
    db = sqlite3.connect(str(DB_PATH))
    # State snapshot table (replaces the complex hierarchy for canvas data)
    # We store the ENTIRE canvas and table state as a single JSON blob for reliable undo/redo and perfect sync
    db.execute('''CREATE TABLE IF NOT EXISTS system_state (
        id INTEGER PRIMARY KEY,
        state_json TEXT NOT NULL,
        updated_at TEXT
    )''')
    
    # Store images metadata separately to avoid massive JSON blobs
    db.execute('''CREATE TABLE IF NOT EXISTS images (
        item_id TEXT PRIMARY KEY,
        filename TEXT NOT NULL
    )''')
    
    # Init empty state if not exists
    if not db.execute("SELECT 1 FROM system_state WHERE id=1").fetchone():
        empty_state = {
            "items": [],
            "nodes": [
                {"id": "root_home", "name": "家", "type": "家", "x": 50, "y": 50, "width": 1400, "height": 900, "color": "#f8f9fa", "parentId": None}
            ]
        }
        db.execute("INSERT INTO system_state (id, state_json) VALUES (1, ?)", (json.dumps(empty_state),))
    db.commit()
    db.close()

# --- API Endpoints ---

@app.route('/api/state', methods=['GET'])
def get_state():
    db = get_db()
    row = db.execute("SELECT state_json FROM system_state WHERE id=1").fetchone()
    state = json.loads(row['state_json'])
    
    # Inject images into items
    images = {r['item_id']: r['filename'] for r in db.execute("SELECT * FROM images").fetchall()}
    for item in state.get('items', []):
        item['image'] = images.get(item['id'], None)
        
    return jsonify(state)

@app.route('/api/state', methods=['POST'])
def save_state():
    db = get_db()
    new_state = request.get_json()
    
    # We strip images from the state JSON before saving to keep it lightweight, 
    # since images are managed separately via the upload API.
    for item in new_state.get('items', []):
        item.pop('image', None)
        
    db.execute("UPDATE system_state SET state_json=?, updated_at=datetime('now','localtime') WHERE id=1", 
               (json.dumps(new_state),))
    db.commit()
    return jsonify({"ok": True})

@app.route('/api/upload/<item_id>', methods=['POST'])
def upload_image(item_id):
    db = get_db()
    f = request.files.get('image')
    if not f: return jsonify({"error": "no file"}), 400
    
    ext = Path(f.filename).suffix or '.jpg'
    fn = f"{uuid.uuid4().hex}{ext}"
    f.save(UPLOAD_DIR / fn)
    
    # Cleanup old image
    old = db.execute("SELECT filename FROM images WHERE item_id=?", (item_id,)).fetchone()
    if old and old['filename']:
        op = UPLOAD_DIR / old['filename']
        if op.exists(): op.unlink()
        
    db.execute("INSERT INTO images (item_id, filename) VALUES (?, ?) ON CONFLICT(item_id) DO UPDATE SET filename=excluded.filename", (item_id, fn))
    db.commit()
    return jsonify({"image": fn})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(str(UPLOAD_DIR), filename)

@app.route('/')
def index():
    return render_template('index.html')

init_db()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8088, debug=False)
