#!/usr/bin/env python3
"""Lightweight SQLite Database Viewer - Single File"""
import sqlite3
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import os

DB_PATH = os.getenv("DB_PATH", "/home/ubuntu/vpn-bot/src/db/vpn_bot.db")
PORT = 8088

HTML = """<!DOCTYPE html>
<html>
<head>
    <title>MMVPN Database</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, sans-serif; }
        body { margin: 0; padding: 20px; background: #1a1a2e; color: #eee; }
        h1 { color: #00d9ff; margin-bottom: 20px; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab { padding: 10px 20px; background: #16213e; border: none; color: #fff; cursor: pointer; border-radius: 5px; }
        .tab:hover, .tab.active { background: #00d9ff; color: #000; }
        table { width: 100%; border-collapse: collapse; background: #16213e; border-radius: 8px; overflow: hidden; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #0f3460; }
        th { background: #0f3460; color: #00d9ff; }
        tr:hover { background: #1f4068; }
        .count { color: #888; font-size: 14px; }
        .refresh { float: right; padding: 8px 16px; background: #00d9ff; border: none; border-radius: 5px; cursor: pointer; }
        #query { width: 100%; padding: 10px; background: #16213e; border: 1px solid #0f3460; color: #fff; border-radius: 5px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <h1>MMVPN Database <button class="refresh" onclick="loadTable(currentTable)">Refresh</button></h1>
    <div class="tabs" id="tabs"></div>
    <input type="text" id="query" placeholder="Custom SQL query (e.g., SELECT * FROM users WHERE is_active=1)" onkeypress="if(event.key==='Enter')runQuery()">
    <div id="content"></div>
    <script>
        let currentTable = 'users';
        const tables = ['users', 'vpn_keys', 'payment_transactions', 'usage_logs'];
        
        function loadTabs() {
            document.getElementById('tabs').innerHTML = tables.map(t => 
                `<button class="tab ${t===currentTable?'active':''}" onclick="loadTable('${t}')">${t}</button>`
            ).join('');
        }
        
        async function loadTable(name) {
            currentTable = name;
            loadTabs();
            const res = await fetch('/api/table/' + name);
            const data = await res.json();
            renderTable(data.rows, data.columns, name);
        }
        
        async function runQuery() {
            const q = document.getElementById('query').value;
            const res = await fetch('/api/query?q=' + encodeURIComponent(q));
            const data = await res.json();
            if (data.error) alert(data.error);
            else renderTable(data.rows, data.columns, 'Query Result');
        }
        
        function renderTable(rows, cols, title) {
            if (!rows || rows.length === 0) {
                document.getElementById('content').innerHTML = `<p>No data in ${title}</p>`;
                return;
            }
            let html = `<p class="count">${title}: ${rows.length} rows</p><table><tr>`;
            cols.forEach(c => html += `<th>${c}</th>`);
            html += '</tr>';
            rows.forEach(r => {
                html += '<tr>';
                cols.forEach(c => html += `<td>${r[c] !== null ? r[c] : '-'}</td>`);
                html += '</tr>';
            });
            html += '</table>';
            document.getElementById('content').innerHTML = html;
        }
        
        loadTable('users');
    </script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path.startswith('/api/table/'):
            table = self.path.split('/')[-1]
            self.send_json(self.get_table(table))
        elif self.path.startswith('/api/query'):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('q', [''])[0]
            self.send_json(self.run_query(query))
        else:
            self.send_error(404)
    
    def get_table(self, table):
        allowed = ['users', 'vpn_keys', 'payment_transactions', 'usage_logs']
        if table not in allowed:
            return {"error": "Invalid table"}
        return self.run_query(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 100")
    
    def run_query(self, query):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description] if cursor.description else []
            conn.close()
            return {"columns": cols, "rows": [dict(r) for r in rows]}
        except Exception as e:
            return {"error": str(e)}
    
    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        pass  # Suppress logs

if __name__ == '__main__':
    print(f"DB Viewer running at http://0.0.0.0:{PORT}")
    HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
