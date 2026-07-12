1|import os
2|import json
import zipfile
import shutil
import io
3|import sqlite3
4|import uuid
5|from datetime import datetime
6|from pathlib import Path
7|from flask import Flask, render_template, request, jsonify, send_from_directory, g, send_file
8|
9|app = Flask(__name__)
10|app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
11|DATA_DIR = Path(os.environ.get('DATA_DIR', '/data'))
12|UPLOAD_DIR = DATA_DIR / 'uploads'
13|UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
14|DB_PATH = DATA_DIR / 'inventory_v2.db'
15|
16|def get_db():
17|    if 'db' not in g:
18|        g.db = sqlite3.connect(str(DB_PATH))
19|        g.db.row_factory = sqlite3.Row
20|        g.db.execute("PRAGMA journal_mode=WAL")
21|        g.db.execute("PRAGMA foreign_keys=ON")
22|    return g.db
23|
24|@app.teardown_appcontext
25|def close_db(_e=None):
26|    db = g.pop('db', None)
27|    if db: db.close()
28|
29|def init_db():
30|    db = sqlite3.connect(str(DB_PATH))
31|    # State snapshot table (replaces the complex hierarchy for canvas data)
32|    # We store the ENTIRE canvas and table state as a single JSON blob for reliable undo/redo and perfect sync
33|    db.execute('''CREATE TABLE IF NOT EXISTS system_state (
34|        id INTEGER PRIMARY KEY,
35|        state_json TEXT NOT NULL,
36|        updated_at TEXT
37|    )''')
38|    
39|    # Store images metadata separately to avoid massive JSON blobs
40|    db.execute('''CREATE TABLE IF NOT EXISTS images (
41|        item_id TEXT PRIMARY KEY,
42|        filename TEXT NOT NULL
43|    )''')
44|    
45|    # Init empty state if not exists
46|    if not db.execute("SELECT 1 FROM system_state WHERE id=1").fetchone():
47|        empty_state = {
48|            "items": [],
49|            "nodes": [
50|                {"id": "root_home", "name": "家", "type": "家", "x": 50, "y": 50, "width": 1400, "height": 900, "color": "#f8f9fa", "parentId": None}
51|            ]
52|        }
53|        db.execute("INSERT INTO system_state (id, state_json) VALUES (1, ?)", (json.dumps(empty_state),))
54|    db.commit()
55|    db.close()
56|
57|# --- API Endpoints ---
58|
59|@app.route('/api/state', methods=['GET'])
60|def get_state():
61|    db = get_db()
62|    row = db.execute("SELECT state_json FROM system_state WHERE id=1").fetchone()
63|    state = json.loads(row['state_json'])
64|    
65|    # Inject images into items
66|    images = {r['item_id']: r['filename'] for r in db.execute("SELECT * FROM images").fetchall()}
67|    for item in state.get('items', []):
68|        item['image'] = images.get(item['id'], None)
69|        
70|    return jsonify(state)
71|
72|@app.route('/api/state', methods=['POST'])
73|def save_state():
74|    db = get_db()
75|    new_state = request.get_json()
76|    
77|    # We strip images from the state JSON before saving to keep it lightweight, 
78|    # since images are managed separately via the upload API.
79|    for item in new_state.get('items', []):
80|        item.pop('image', None)
81|        
82|    db.execute("UPDATE system_state SET state_json=?, updated_at=datetime('now','localtime') WHERE id=1", 
83|               (json.dumps(new_state),))
84|    db.commit()
85|    return jsonify({"ok": True})
86|
87|@app.route('/api/upload/<item_id>', methods=['POST'])
88|def upload_image(item_id):
89|    db = get_db()
90|    f = request.files.get('image')
91|    if not f: return jsonify({"error": "no file"}), 400
92|    
93|    ext = Path(f.filename).suffix or '.jpg'
94|    fn = f"{uuid.uuid4().hex}{ext}"
95|    f.save(UPLOAD_DIR / fn)
96|    
97|    # Cleanup old image
98|    old = db.execute("SELECT filename FROM images WHERE item_id=?", (item_id,)).fetchone()
99|    if old and old['filename']:
100|        op = UPLOAD_DIR / old['filename']
101|        if op.exists(): op.unlink()
102|        
103|    db.execute("INSERT INTO images (item_id, filename) VALUES (?, ?) ON CONFLICT(item_id) DO UPDATE SET filename=excluded.filename", (item_id, fn))
104|    db.commit()
105|    return jsonify({"image": fn})
106|
107|@app.route('/uploads/<filename>')
108|def uploaded_file(filename):
109|    return send_from_directory(str(UPLOAD_DIR), filename)
110|
111|@app.route('/')
112|def index():
113|    return render_template('index.html')
114|
115|init_db()
116|
@app.route('/api/export', methods=['GET'])
def export_data():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        if DB_PATH.exists():
            zf.write(str(DB_PATH), 'inventory_v2.db')
        if UPLOAD_DIR.exists():
            for root, _, files in os.walk(str(UPLOAD_DIR)):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join('uploads', os.path.relpath(file_path, str(UPLOAD_DIR)))
                    zf.write(file_path, arcname)
    memory_file.seek(0)
    return send_file(memory_file, download_name='nestly_backup.zip', as_attachment=True)

@app.route('/api/import', methods=['POST'])
def import_data():
    if 'backup' not in request.files: return jsonify({'error': 'No file'}), 400
    file = request.files['backup']
    if not file.filename.endswith('.zip'): return jsonify({'error': 'Must be zip'}), 400
    
    tmp_dir = DATA_DIR / 'tmp_import'
    tmp_dir.mkdir(exist_ok=True)
    zip_path = tmp_dir / 'backup.zip'
    file.save(str(zip_path))
    
    with zipfile.ZipFile(str(zip_path), 'r') as zf:
        zf.extractall(str(tmp_dir))
    
    extracted_db = tmp_dir / 'inventory_v2.db'
    if extracted_db.exists():
        if DB_PATH.exists(): DB_PATH.unlink()
        shutil.copy(str(extracted_db), str(DB_PATH))
    
    extracted_uploads = tmp_dir / 'uploads'
    if extracted_uploads.exists():
        for f in os.listdir(str(extracted_uploads)):
            shutil.copy(os.path.join(str(extracted_uploads), f), os.path.join(str(UPLOAD_DIR), f))
            
    shutil.rmtree(str(tmp_dir))
    return jsonify({'success': True})

if __name__ == '__main__':

117|    app.run(host='0.0.0.0', port=8088, debug=False)
118|