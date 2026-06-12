from flask import Flask, request, redirect, render_template_string, jsonify
import sqlite3, random, string, os

app = Flask(__name__)
DB = os.path.join(os.path.dirname(__file__), 'links.db')

# ── Banco de dados ────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS links (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo   TEXT UNIQUE NOT NULL,
                url      TEXT NOT NULL,
                criado   DATETIME DEFAULT CURRENT_TIMESTAMP,
                cliques  INTEGER DEFAULT 0
            )
        ''')

def gerar_codigo(n=6):
    chars = string.ascii_letters + string.digits
    with get_db() as db:
        for _ in range(10):
            codigo = ''.join(random.choices(chars, k=n))
            if not db.execute('SELECT 1 FROM links WHERE codigo=?', (codigo,)).fetchone():
                return codigo
    return ''.join(random.choices(chars, k=8))

# ── HTML da interface ─────────────────────────────────────────────────
HTML = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Encurtador de Links</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0f0f1a;
      min-height: 100vh;
      display: flex;
      align-items: flex-start;
      justify-content: center;
      padding: 40px 20px;
    }
    .card {
      background: #1a1a2e;
      border: 1px solid #2a2a4a;
      border-radius: 20px;
      padding: 48px 40px;
      width: 100%;
      max-width: 580px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    }
    .logo { text-align: center; margin-bottom: 28px; }
    .logo-icon { font-size: 48px; }
    h1 { color: #fff; font-size: 26px; font-weight: 700; text-align: center; margin: 8px 0 4px; }
    .subtitle { color: #6b6b8a; text-align: center; font-size: 14px; margin-bottom: 32px; }
    label { display: block; color: #9090aa; font-size: 12px; font-weight: 700;
            text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
    .input-row { display: flex; gap: 10px; margin-bottom: 16px; }
    input[type=url] {
      flex: 1; background: #0f0f1a; border: 1px solid #2a2a4a;
      border-radius: 12px; padding: 14px 18px; color: #fff; font-size: 15px; outline: none;
      transition: border-color .2s;
    }
    input[type=url]:focus { border-color: #6c63ff; }
    input[type=url]::placeholder { color: #3a3a5a; }
    .btn {
      background: linear-gradient(135deg,#6c63ff,#a855f7);
      border: none; border-radius: 12px; padding: 14px 22px;
      color: #fff; font-size: 15px; font-weight: 700; cursor: pointer;
      transition: opacity .2s; white-space: nowrap;
    }
    .btn:hover { opacity: .88; }
    .btn:disabled { opacity: .5; cursor: not-allowed; }
    .result-box {
      display:none; background:#0f0f1a; border:1px solid #2a2a4a;
      border-radius:12px; padding:16px 18px; margin-top:4px;
    }
    .result-box.visible { display:block; }
    .result-label { color:#6b6b8a; font-size:12px; margin-bottom:8px; }
    .result-row { display:flex; align-items:center; gap:10px; }
    .short-url { flex:1; color:#a78bfa; font-size:16px; font-weight:700;
                 text-decoration:none; word-break:break-all; }
    .short-url:hover { text-decoration:underline; }
    .btn-copy {
      background:#2a2a4a; border:none; border-radius:8px;
      padding:8px 16px; color:#9090aa; font-size:13px; cursor:pointer;
      transition:background .2s,color .2s; white-space:nowrap;
    }
    .btn-copy:hover { background:#3a3a5a; color:#fff; }
    .btn-copy.ok { background:#1a3a1a; color:#4ade80; }
    .error { background:#1a0f0f; border:1px solid #4a2a2a; border-radius:12px;
             padding:14px 18px; color:#f87171; font-size:14px; margin-top:4px; display:none; }
    .error.visible { display:block; }
    .spinner {
      display:inline-block; width:15px; height:15px;
      border:2px solid rgba(255,255,255,.3); border-top-color:#fff;
      border-radius:50%; animation:spin .6s linear infinite;
      vertical-align:middle; margin-right:6px;
    }
    @keyframes spin { to { transform:rotate(360deg); } }
    .hist { margin-top:36px; }
    .hist h2 { color:#6b6b8a; font-size:12px; text-transform:uppercase;
               letter-spacing:.5px; margin-bottom:12px; font-weight:700; }
    .hist-list { list-style:none; display:flex; flex-direction:column; gap:8px; }
    .hist-item {
      background:#0f0f1a; border:1px solid #1e1e35;
      border-radius:10px; padding:12px 16px;
      display:flex; justify-content:space-between; align-items:center; gap:12px;
    }
    .hist-urls { flex:1; min-width:0; }
    .hist-orig { color:#4a4a6a; font-size:12px; white-space:nowrap;
                 overflow:hidden; text-overflow:ellipsis; }
    .hist-short { color:#a78bfa; font-size:14px; font-weight:700; text-decoration:none; }
    .hist-short:hover { text-decoration:underline; }
    .hist-clicks { color:#6b6b8a; font-size:11px; margin-top:2px; }
    .btn-sm {
      background:transparent; border:1px solid #2a2a4a; border-radius:6px;
      padding:5px 10px; color:#6b6b8a; font-size:12px; cursor:pointer;
      transition:all .2s; flex-shrink:0;
    }
    .btn-sm:hover { border-color:#6c63ff; color:#a78bfa; }
    .btn-sm.ok { border-color:#4ade80; color:#4ade80; }
    .empty { color:#3a3a5a; font-size:13px; text-align:center; padding:16px; }
  </style>
</head>
<body>
<div class="card">
  <div class="logo">
    <div class="logo-icon">🔗</div>
    <h1>Encurtador de Links</h1>
    <p class="subtitle">Seu encurtador pessoal &mdash; sem limites, sem custo</p>
  </div>

  <label>Seu link longo</label>
  <div class="input-row">
    <input type="url" id="inp" placeholder="https://exemplo.com/link/muito/longo...">
    <button class="btn" id="btn" onclick="encurtar()">Encurtar</button>
  </div>

  <div class="result-box" id="res">
    <div class="result-label">✅ Link encurtado!</div>
    <div class="result-row">
      <a class="short-url" id="short" href="#" target="_blank"></a>
      <button class="btn-copy" id="btnCopy" onclick="copiar()">Copiar</button>
    </div>
  </div>
  <div class="error" id="err"></div>

  <div class="hist">
    <h2>Histórico desta sessão</h2>
    <ul class="hist-list" id="hist">
      <li class="empty">Nenhum link encurtado ainda.</li>
    </ul>
  </div>
</div>

<script>
const sessao = [];

async function encurtar() {
  const url = document.getElementById('inp').value.trim();
  const btn = document.getElementById('btn');
  const res = document.getElementById('res');
  const err = document.getElementById('err');

  if (!url) { mostrarErro('Cole um link antes de encurtar.'); return; }
  if (!/^https?:\\/\\//.test(url)) { mostrarErro('O link deve começar com http:// ou https://'); return; }

  res.classList.remove('visible');
  err.classList.remove('visible');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Encurtando...';

  try {
    const r = await fetch('/encurtar', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url})
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.erro || 'Erro');

    document.getElementById('short').textContent = d.curto;
    document.getElementById('short').href = d.curto;
    res.classList.add('visible');
    document.getElementById('inp').value = '';

    sessao.unshift({original: url, curto: d.curto});
    renderHist();
  } catch(e) {
    mostrarErro(e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Encurtar';
  }
}

function mostrarErro(msg) {
  const el = document.getElementById('err');
  el.textContent = '⚠️ ' + msg;
  el.classList.add('visible');
}

function copiar(url, btn) {
  const u = url || document.getElementById('short').textContent;
  const b = btn || document.getElementById('btnCopy');
  navigator.clipboard.writeText(u).then(() => {
    const orig = b.textContent;
    b.textContent = '✓ Copiado!';
    b.classList.add('ok');
    setTimeout(() => { b.textContent = orig; b.classList.remove('ok'); }, 2000);
  });
}

function renderHist() {
  const ul = document.getElementById('hist');
  if (!sessao.length) { ul.innerHTML = '<li class="empty">Nenhum link encurtado ainda.</li>'; return; }
  ul.innerHTML = sessao.map((it, i) => `
    <li class="hist-item">
      <div class="hist-urls">
        <div class="hist-orig">${esc(it.original)}</div>
        <a class="hist-short" href="${esc(it.curto)}" target="_blank">${esc(it.curto)}</a>
      </div>
      <button class="btn-sm" onclick="copiar('${esc(it.curto)}', this)">Copiar</button>
    </li>`).join('');
}

function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

document.getElementById('inp').addEventListener('keydown', e => {
  if (e.key === 'Enter') encurtar();
});
</script>
</body>
</html>'''

# ── Rotas ─────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/encurtar', methods=['POST'])
def encurtar():
    data = request.get_json(silent=True) or {}
    url  = (data.get('url') or '').strip()

    if not url:
        return jsonify({'erro': 'URL não informada'}), 400
    if not url.startswith(('http://', 'https://')):
        return jsonify({'erro': 'URL deve começar com http:// ou https://'}), 400

    with get_db() as db:
        # Reutiliza se já existe
        row = db.execute('SELECT codigo FROM links WHERE url=?', (url,)).fetchone()
        if row:
            codigo = row['codigo']
        else:
            codigo = gerar_codigo()
            db.execute('INSERT INTO links (codigo, url) VALUES (?,?)', (codigo, url))

    base = request.host_url.rstrip('/')
    return jsonify({'curto': f'{base}/r/{codigo}'})

@app.route('/r/<codigo>')
def redirecionar(codigo):
    with get_db() as db:
        row = db.execute('SELECT url FROM links WHERE codigo=?', (codigo,)).fetchone()
        if not row:
            return 'Link não encontrado.', 404
        db.execute('UPDATE links SET cliques = cliques + 1 WHERE codigo=?', (codigo,))
    return redirect(row['url'], code=302)

# ── Inicialização ──────────────────────────────────────────────────────
init_db()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
