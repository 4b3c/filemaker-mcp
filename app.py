# app.py
from flask import Flask, render_template_string, request, abort, url_for
import database
from models import Node
from collections import defaultdict

database.init_db()  # no reset; use your parser first to populate

app = Flask(__name__)

BASE_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{{ title }}</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; line-height: 1.4; }
    a { text-decoration: none; }
    .muted { color: #666; }
    .pill { display:inline-block; padding:2px 8px; border-radius:12px; background:#f1f1f1; font-size:12px; margin-left:6px; }
    .row { margin: 8px 0; }
    pre { background:#f8f8f8; padding:12px; border-radius:8px; overflow:auto; }
    input[type=text]{ padding:8px; width:260px; }
    button{ padding:8px 12px; }
    ul { margin: 6px 0 16px 20px; }
  </style>
</head>
<body>
  <form action="{{ url_for('index') }}" method="get" class="row">
    <input type="text" name="q" placeholder="Search by name..." value="{{ q or '' }}">
    <button>Search</button>
    <a class="muted" href="{{ url_for('index') }}" style="margin-left:8px;">clear</a>
  </form>

  <div class="row">
    <a href="{{ url_for('index') }}">
        <button type="button">← Back to Index</button>
    </a>
  </div>

  {{ body|safe }}
</body>
</html>
"""

NODE_HTML = """
<h2>
  {{ node.name }}
  <span class="pill">{{ node.type.value }}</span>
  <span class="muted">#{{ node.id }}</span>
</h2>

<h3>Details</h3>
<pre>{{ node.details | tojson(indent=2) }}</pre>

<h3>Parents</h3>
{% if parents %}
  <ul>
  {% for p, rel, eid in parents %}
    <li>
      <a href="{{ url_for('node_page', node_id=p.id) }}">{{ p.name }}</a>
      <span class="pill">{{ rel.value }}</span>
      <span class="muted">edge #{{ eid }}</span>
    </li>
  {% endfor %}
  </ul>
{% else %}
  <div class="muted">No parents.</div>
{% endif %}

<h3>Children</h3>
{% if children %}
  <ul>
  {% for c, rel, eid in children %}
    <li>
      <a href="{{ url_for('node_page', node_id=c.id) }}">{{ c.name }}</a>
      <span class="pill">{{ rel.value }}</span>
      <span class="muted">edge #{{ eid }}</span>
    </li>
  {% endfor %}
  </ul>
{% else %}
  <div class="muted">No children.</div>
{% endif %}
"""

INDEX_HTML = """
<h2>Nodes</h2>
{% if grouped %}
  {% for t, group in grouped.items() %}
    <h3>{{ t }} <span class="muted">({{ group|length }})</span></h3>
    <ul>
    {% for r in group %}
      <li>
        <a href="{{ url_for('node_page', node_id=r['id']) }}">{{ r['name'] }}</a>
        <span class="muted">#{{ r['id'] }}</span>
      </li>
    {% endfor %}
    </ul>
  {% endfor %}
{% else %}
  <div class="muted">No nodes found.</div>
{% endif %}
"""

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    rows = database.node_find("name LIKE ?", (f"%{q}%",)) if q else database.node_find()

    # Group by type
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["type"]].append(r)

    # Optional: stable order of sections
    order = ["BaseTable", "Field", "RelTable", "Relationship", "Account", "Unknown"]
    grouped = {t: grouped[t] for t in order if t in grouped} | {t: v for t, v in grouped.items() if t not in order}

    body = render_template_string(INDEX_HTML, grouped=grouped)
    return render_template_string(BASE_HTML, title="Graph Browser", q=q, body=body)


@app.route("/node/<int:node_id>")
def node_page(node_id: int):
    node = Node.load(node_id)
    if not node:
        abort(404)
    parents = node.get_parents()    # [(Node, EdgeType, edge_id)]
    children = node.get_children()  # [(Node, EdgeType, edge_id)]
    body = render_template_string(NODE_HTML, node=node, parents=parents, children=children)
    return render_template_string(BASE_HTML, title=node.name, q="", body=body)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
