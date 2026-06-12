from flask import Flask, request, redirect, render_template_string, jsonify
import sqlite3, random, string, os

app = Flask(__name__)
DB = os.path.join(os.path.dirname(__file__), 'links.db')

# ── Banco de dados ─────────────────────────────────────────────────────
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
                cliente  TEXT NOT NULL DEFAULT 'Geral',
                criado   DATETIME DEFAULT CURRENT_TIMESTAMP,
                cliques  INTEGER DEFAULT 0
            )
        ''')
        # Migração: adiciona coluna cliente se não existir (banco antigo)
        try:
            db.execute("ALTER TABLE links ADD COLUMN cliente TEXT NOT NULL DEFAULT 'Geral'")
        except Exception:
            pass

def gerar_codigo(n=6):
    chars = string.ascii_letters + string.digits
    with get_db() as db:
        for _ in range(10):
            codigo = ''.join(random.choices(chars, k=n))
            if not db.execute('SELECT 1 FROM links WHERE codigo=?', (codigo,)).fetchone():
                return codigo
    return ''.join(random.choices(chars, k=8))

# ── CSS compartilhado ──────────────────────────────────────────────────
CSS = '''
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       background: #0f0f1a; min-height: 100vh; }
a { color: #6c63ff; text-decoration: none; }
a:hover { text-decoration: underline; }
.btn {
  background: linear-gradient(135deg,#6c63ff,#a855f7);
  border: none; border-radius: 12px; padding: 14px 22px;
  color: #fff; font-size: 15px; font-weight: 700; cursor: pointer;
  transition: opacity .2s; white-space: nowrap;
}
.btn:hover { opacity: .88; }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn-sm {
  background: transparent; border: 1px solid #2a2a4a; border-radius: 6px;
  padding: 5px 12px; color: #9090aa; font-size: 12px; cursor: pointer;
  transition: all .2s; white-space: nowrap;
}
.btn-sm:hover { border-color: #6c63ff; color: #a78bfa; }
.btn-sm.ok { border-color: #4ade80; color: #4ade80; }
.badge { display:inline-block; background:#6c63ff22; color:#a78bfa;
         border-radius:20px; padding:2px 10px; font-size:11px; font-weight:700; }
input, select {
  background: #0f0f1a; border: 1px solid #2a2a4a; border-radius: 12px;
  padding: 12px 16px; color: #fff; font-size: 14px; outline: none;
  transition: border-color .2s; width: 100%;
}
input:focus, select:focus { border-color: #6c63ff; }
input::placeholder { color: #3a3a5a; }
select option { background: #1a1a2e; }
label { display: block; color: #9090aa; font-size: 11px; font-weight: 700;
        text-transform: uppercase; letter-spacing: .5px; margin-bottom: 6px; }
'''

# ── Página principal ───────────────────────────────────────────────────
HTML = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Encurtador de Links</title>
  <style>
    ''' + CSS + '''
    body { display:flex; align-items:flex-start; justify-content:center; padding:40px 20px; }
    .card {
      background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 20px;
      padding: 48px 40px; width: 100%; max-width: 580px;
      box-shadow: 0 20px 60px rgba(0,0,0,.5);
    }
    .logo { text-align:center; margin-bottom:24px; }
    .logo-icon { font-size:44px; }
    h1 { color:#fff; font-size:26px; font-weight:700; text-align:center; margin:8px 0 4px; }
    .subtitle { color:#6b6b8a; text-align:center; font-size:14px; margin-bottom:6px; }
    .nav-link { display:block; text-align:center; margin-bottom:28px; font-size:13px; }
    .form-row { display:flex; gap:10px; margin-bottom:14px; }
    .form-row input[type=url] { flex:1; }
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
    .btn-copy { background:#2a2a4a; border:none; border-radius:8px;
                padding:8px 16px; color:#9090aa; font-size:13px; cursor:pointer;
                transition:background .2s,color .2s; white-space:nowrap; }
    .btn-copy:hover { background:#3a3a5a; color:#fff; }
    .btn-copy.ok { background:#1a3a1a; color:#4ade80; }
    .error { background:#1a0f0f; border:1px solid #4a2a2a; border-radius:12px;
             padding:14px 18px; color:#f87171; font-size:14px; margin-top:4px; display:none; }
    .error.visible { display:block; }
    .spinner { display:inline-block; width:15px; height:15px;
               border:2px solid rgba(255,255,255,.3); border-top-color:#fff;
               border-radius:50%; animation:spin .6s linear infinite;
               vertical-align:middle; margin-right:6px; }
    @keyframes spin { to { transform:rotate(360deg); } }
    .sess { margin-top:32px; }
    .sess h2 { color:#6b6b8a; font-size:11px; text-transform:uppercase;
               letter-spacing:.5px; margin-bottom:12px; font-weight:700; }
    .sess-list { list-style:none; display:flex; flex-direction:column; gap:8px; }
    .sess-item { background:#0f0f1a; border:1px solid #1e1e35; border-radius:10px;
                 padding:12px 16px; display:flex; justify-content:space-between;
                 align-items:center; gap:12px; }
    .sess-urls { flex:1; min-width:0; }
    .sess-orig { color:#4a4a6a; font-size:11px; white-space:nowrap;
                 overflow:hidden; text-overflow:ellipsis; }
    .sess-cli { color:#6c63ff; font-size:11px; margin-bottom:2px; }
    .sess-short { color:#a78bfa; font-size:13px; font-weight:700; text-decoration:none; }
    .sess-short:hover { text-decoration:underline; }
    .empty { color:#3a3a5a; font-size:13px; text-align:center; padding:16px; }
  </style>
</head>
<body>
<div class="card">
  <div class="logo">
    <div class="logo-icon">🔗</div>
    <h1>Encurtador de Links</h1>
    <p class="subtitle">Seu encurtador pessoal — sem limites, sem custo</p>
    <a class="nav-link" href="/historico">📋 Ver histórico por cliente →</a>
  </div>

  <label>Cliente</label>
  <div style="margin-bottom:14px; display:flex; gap:10px;">
    <input type="text" id="cliente" placeholder="Ex: Empresa ABC" list="clientes-lista" style="flex:1">
    <datalist id="clientes-lista"></datalist>
  </div>

  <label>Link longo</label>
  <div class="form-row">
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

  <div class="sess">
    <h2>Sessão atual</h2>
    <ul class="sess-list" id="hist">
      <li class="empty">Nenhum link encurtado ainda.</li>
    </ul>
  </div>
</div>

<script>
const sessao = [];

// Carrega lista de clientes existentes para autocomplete
fetch('/clientes').then(r=>r.json()).then(lista=>{
  const dl = document.getElementById('clientes-lista');
  lista.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c;
    dl.appendChild(opt);
  });
});

async function encurtar() {
  const url     = document.getElementById('inp').value.trim();
  const cliente = document.getElementById('cliente').value.trim() || 'Geral';
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
      body: JSON.stringify({url, cliente})
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.erro || 'Erro');

    document.getElementById('short').textContent = d.curto;
    document.getElementById('short').href = d.curto;
    res.classList.add('visible');
    document.getElementById('inp').value = '';

    sessao.unshift({original: url, curto: d.curto, cliente});
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
  ul.innerHTML = sessao.map(it => `
    <li class="sess-item">
      <div class="sess-urls">
        <div class="sess-cli">📁 ${esc(it.cliente)}</div>
        <div class="sess-orig">${esc(it.original)}</div>
        <a class="sess-short" href="${esc(it.curto)}" target="_blank">${esc(it.curto)}</a>
      </div>
      <button class="btn-sm" onclick="copiar('${esc(it.curto)}', this)">Copiar</button>
    </li>`).join('');
}

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

document.getElementById('inp').addEventListener('keydown', e => {
  if (e.key === 'Enter') encurtar();
});
</script>
</body>
</html>'''

# ── Página de histórico ────────────────────────────────────────────────
HIST_HTML = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Histórico — Encurtador</title>
  <style>
    ''' + CSS + '''
    .layout { display:flex; min-height:100vh; }
    .sidebar {
      width: 220px; min-width:220px; background:#13132a; border-right:1px solid #1e1e35;
      padding:28px 0; position:sticky; top:0; height:100vh; overflow-y:auto;
    }
    .sidebar-title { color:#6b6b8a; font-size:11px; font-weight:700;
                     text-transform:uppercase; letter-spacing:.5px;
                     padding:0 20px 12px; }
    .cli-item {
      display:block; padding:10px 20px; color:#9090aa; font-size:14px;
      cursor:pointer; transition:background .15s, color .15s;
      text-decoration:none; border-left:3px solid transparent;
    }
    .cli-item:hover { background:#1a1a2e; color:#fff; text-decoration:none; }
    .cli-item.active { background:#1a1a2e; color:#a78bfa; border-left-color:#6c63ff; font-weight:600; }
    .cli-count { float:right; background:#2a2a4a; border-radius:20px;
                 padding:1px 8px; font-size:11px; color:#6b6b8a; }
    .main { flex:1; padding:36px 40px; }
    .top { display:flex; align-items:center; justify-content:space-between; margin-bottom:24px; }
    h1 { color:#fff; font-size:20px; font-weight:700; }
    .back { font-size:13px; }
    .stats { color:#6b6b8a; font-size:13px; margin-bottom:24px; }
    table { width:100%; border-collapse:collapse; }
    thead th { text-align:left; color:#6b6b8a; font-size:11px; text-transform:uppercase;
               letter-spacing:.5px; padding:0 14px 10px; font-weight:700; }
    tbody tr { background:#1a1a2e; border-bottom:1px solid #0f0f1a; transition:background .15s; }
    tbody tr:hover { background:#222240; }
    td { padding:12px 14px; vertical-align:middle; }
    .td-orig { color:#4a4a6a; font-size:12px; max-width:260px;
               white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .td-short a { color:#a78bfa; font-size:13px; font-weight:600; text-decoration:none; }
    .td-short a:hover { text-decoration:underline; }
    .td-date { color:#4a4a6a; font-size:12px; white-space:nowrap; }
    .td-clicks { text-align:center; }
    .empty-state { color:#4a4a6a; text-align:center; padding:80px 0; font-size:15px; }
    @media(max-width:600px) {
      .layout { flex-direction:column; }
      .sidebar { width:100%; height:auto; position:relative; padding:16px 0; }
      .main { padding:20px; }
    }
  </style>
</head>
<body>
<div class="layout">
  <!-- Sidebar de clientes -->
  <nav class="sidebar">
    <div class="sidebar-title">📁 Clientes</div>
    <a class="cli-item {{ 'active' if not cliente_atual else '' }}" href="/historico">
      Todos <span class="cli-count">{{ total_geral }}</span>
    </a>
    {% for c in clientes %}
    <a class="cli-item {{ 'active' if cliente_atual == c.nome else '' }}"
       href="/historico?cliente={{ c.nome | urlencode }}">
      {{ c.nome }} <span class="cli-count">{{ c.qtd }}</span>
    </a>
    {% endfor %}
  </nav>

  <!-- Conteúdo principal -->
  <div class="main">
    <div class="top">
      <h1>{{ cliente_atual or "Todos os links" }}</h1>
      <a class="back" href="/">← Encurtar novo link</a>
    </div>
    <p class="stats">{{ links|length }} link{{ "s" if links|length != 1 else "" }} • {{ cliques_total }} clique{{ "s" if cliques_total != 1 else "" }}</p>

    {% if links %}
    <table>
      <thead>
        <tr>
          <th>Link original</th>
          <th>Link curto</th>
          <th style="text-align:center">Cliques</th>
          <th>Data</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
      {% for l in links %}
        <tr>
          <td class="td-orig" title="{{ l.url }}">{{ l.url }}</td>
          <td class="td-short"><a href="/{{ l.codigo }}" target="_blank">{{ base }}/{{ l.codigo }}</a></td>
          <td class="td-clicks"><span class="badge">{{ l.cliques }}</span></td>
          <td class="td-date">{{ l.criado[:16].replace("T"," ") }}</td>
          <td><button class="btn-sm" onclick="copiar('{{ base }}/{{ l.codigo }}', this)">Copiar</button></td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}
    <p class="empty-state">Nenhum link encurtado para este cliente.</p>
    {% endif %}
  </div>
</div>
<script>
function copiar(url, btn) {
  navigator.clipboard.writeText(url).then(() => {
    const orig = btn.textContent;
    btn.textContent = '✓';
    btn.classList.add('ok');
    setTimeout(() => { btn.textContent = orig; btn.classList.remove('ok'); }, 2000);
  });
}
</script>
</body>
</html>'''

# ── Rotas ──────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/clientes')
def listar_clientes():
    with get_db() as db:
        rows = db.execute("SELECT DISTINCT cliente FROM links ORDER BY cliente").fetchall()
    return jsonify([r['cliente'] for r in rows])

@app.route('/encurtar', methods=['POST'])
def encurtar():
    data    = request.get_json(silent=True) or {}
    url     = (data.get('url') or '').strip()
    cliente = (data.get('cliente') or 'Geral').strip() or 'Geral'

    if not url:
        return jsonify({'erro': 'URL não informada'}), 400
    if not url.startswith(('http://', 'https://')):
        return jsonify({'erro': 'URL deve começar com http:// ou https://'}), 400

    with get_db() as db:
        # Reutiliza se mesma URL + mesmo cliente
        row = db.execute('SELECT codigo FROM links WHERE url=? AND cliente=?',
                         (url, cliente)).fetchone()
        if row:
            codigo = row['codigo']
        else:
            codigo = gerar_codigo()
            db.execute('INSERT INTO links (codigo, url, cliente) VALUES (?,?,?)',
                       (codigo, url, cliente))

    base = request.host_url.rstrip('/')
    return jsonify({'curto': f'{base}/{codigo}'})

@app.route('/<codigo>')
def redirecionar(codigo):
    if codigo in ('', 'encurtar', 'historico', 'clientes', 'favicon.ico'):
        return '', 404
    with get_db() as db:
        row = db.execute('SELECT url FROM links WHERE codigo=?', (codigo,)).fetchone()
        if not row:
            return 'Link não encontrado.', 404
        db.execute('UPDATE links SET cliques = cliques + 1 WHERE codigo=?', (codigo,))
    return redirect(row['url'], code=302)

@app.route('/historico')
def historico():
    cliente_atual = request.args.get('cliente', '').strip()
    base = request.host_url.rstrip('/')

    with get_db() as db:
        # Lista de clientes com contagem
        clientes_raw = db.execute(
            "SELECT cliente as nome, COUNT(*) as qtd FROM links GROUP BY cliente ORDER BY cliente"
        ).fetchall()
        total_geral = db.execute("SELECT COUNT(*) FROM links").fetchone()[0]

        if cliente_atual:
            links = db.execute(
                'SELECT * FROM links WHERE cliente=? ORDER BY id DESC', (cliente_atual,)
            ).fetchall()
        else:
            links = db.execute('SELECT * FROM links ORDER BY id DESC').fetchall()

    cliques_total = sum(l['cliques'] for l in links)
    return render_template_string(HIST_HTML,
        links=links, clientes=clientes_raw, cliente_atual=cliente_atual,
        cliques_total=cliques_total, total_geral=total_geral, base=base)

# ── Inicialização ──────────────────────────────────────────────────────
init_db()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
