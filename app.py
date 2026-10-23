"""Product Compatibility Checker - Flask + SQLite + rule-based engine."""
import json, sqlite3, os
from flask import Flask, jsonify, request, render_template, g

app = Flask(__name__)
DB = os.path.join(os.path.dirname(__file__), "compat.db")

# ---------- Sample data (None = information not available) ----------
DEVICES = [
    # name, category, specs
    ("iPhone 15", "Phone", dict(connectors=["USB-C"], protocols=["PD", "MagSafe"], max_power_w=27, bluetooth=5.3)),
    ("iPhone 12", "Phone", dict(connectors=["Lightning"], protocols=["PD", "MagSafe"], max_power_w=20, bluetooth=5.0)),
    ("Samsung Galaxy S23", "Phone", dict(connectors=["USB-C"], protocols=["PD", "QC"], max_power_w=25, bluetooth=5.3)),
    ("Redmi Note 10", "Phone", dict(connectors=["USB-C"], protocols=["QC"], max_power_w=33, bluetooth=5.1)),
    ("Moto E7 Power", "Phone", dict(connectors=["Micro-USB"], protocols=["Standard"], max_power_w=10, bluetooth=5.0)),
    ("MacBook Air M2", "Laptop", dict(connectors=["USB-C"], protocols=["PD"], max_power_w=67, bluetooth=5.0)),
    ("Dell Inspiron 15", "Laptop", dict(connectors=["USB-C", "USB-A"], protocols=["PD"], max_power_w=65, bluetooth=None)),
    ("Generic Android Phone", "Phone", dict(connectors=["USB-C"], protocols=None, max_power_w=None, bluetooth=5.0)),
]
ACCESSORIES = [
    # name, category, price (INR), specs
    ("Apple 20W USB-C Charger + USB-C to Lightning Cable", "Charger", 1900, dict(connector="Lightning", protocol="PD", power_w=20)),
    ("Anker 30W USB-C PD Charger + USB-C Cable", "Charger", 1799, dict(connector="USB-C", protocol="PD", power_w=30)),
    ("Mi 33W SonicCharge USB-C Charger", "Charger", 999, dict(connector="USB-C", protocol="QC", power_w=33)),
    ("Ambrane 10W Micro-USB Charger", "Charger", 349, dict(connector="Micro-USB", protocol="Standard", power_w=10)),
    ("Baseus 65W GaN USB-C Charger", "Charger", 2499, dict(connector="USB-C", protocol="PD", power_w=65)),
    ("MagSafe Wireless Charger 15W", "Charger", 3500, dict(connector="USB-C", protocol="MagSafe", power_w=15)),
    ("Boat Rockerz 255 Neckband (Bluetooth 5.2)", "Audio", 1299, dict(connector="Bluetooth", bluetooth_min=5.2)),
    ("Sony WH-CH520 Headphones (Bluetooth 5.2)", "Audio", 3990, dict(connector="Bluetooth", bluetooth_min=5.2)),
    ("Old Bluetooth 4.0 Earbuds", "Audio", 699, dict(connector="Bluetooth", bluetooth_min=4.0)),
    ("Wired Earphones 3.5mm", "Audio", 299, dict(connector="3.5mm")),
    ("Ugreen USB-C Hub 5-in-1", "Hub", 2799, dict(connector="USB-C", protocol="PD", power_w=60)),
    ("Generic USB-A to Micro-USB Cable", "Cable", 149, dict(connector="Micro-USB")),
]

# ---------- DB ----------
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB); g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close(_):
    d = g.pop("db", None)
    if d: d.close()

def init_db():
    c = sqlite3.connect(DB)
    c.executescript("""DROP TABLE IF EXISTS devices; DROP TABLE IF EXISTS accessories;
      CREATE TABLE devices(id INTEGER PRIMARY KEY, name TEXT, category TEXT, specs TEXT);
      CREATE TABLE accessories(id INTEGER PRIMARY KEY, name TEXT, category TEXT, price INTEGER, specs TEXT);""")
    c.executemany("INSERT INTO devices(name,category,specs) VALUES(?,?,?)", [(n, k, json.dumps(s)) for n, k, s in DEVICES])
    c.executemany("INSERT INTO accessories(name,category,price,specs) VALUES(?,?,?,?)", [(n, k, p, json.dumps(s)) for n, k, p, s in ACCESSORIES])
    c.commit(); c.close()

# ---------- Rule engine ----------
# Each rule: (label, weight, critical, device_key, accessory_key, check_fn, pass_msg, fail_msg)
RULES = [
    ("Connector", 40, True, "connectors", "connector",
     lambda d, a: a in d or a == "Bluetooth",
     lambda d, a: f"Device supports {a}",
     lambda d, a: f"Accessory uses {a}, but device only has {', '.join(d)}"),
    ("Charging protocol", 25, False, "protocols", "protocol",
     lambda d, a: a in d or a == "Standard",
     lambda d, a: f"Device supports {a} fast charging",
     lambda d, a: f"Device doesn't support {a}; it will charge at slower standard speed"),
    ("Power", 20, False, "max_power_w", "power_w",
     lambda d, a: d >= a,
     lambda d, a: f"Device can draw {d}W (accessory delivers {a}W)",
     lambda d, a: f"Device accepts max {d}W, accessory is rated {a}W; you won't use its full power"),
    ("Bluetooth version", 15, False, "bluetooth", "bluetooth_min",
     lambda d, a: d >= a,
     lambda d, a: f"Device Bluetooth {d} meets required {a}",
     lambda d, a: f"Device has Bluetooth {d}, accessory needs {a}+"),
]

def check(device, acc):
    ds, as_ = json.loads(device["specs"]), json.loads(acc["specs"])
    rows, warnings, got, known, crit_fail, any_unknown = [], [], 0, 0, False, False
    for label, w, crit, dk, ak, fn, ok_msg, bad_msg in RULES:
        av, dv = as_.get(ak), ds.get(dk)
        if av is None:
            continue  # rule not relevant for this accessory
        if dv is None:
            rows.append(dict(rule=label, result="unknown", detail=f"Device {label.lower()} data is missing"))
            warnings.append(f"Missing device info: {label.lower()}. Verify on the manufacturer's site.")
            any_unknown = True
            continue
        known += w
        passed = fn(dv, av)
        if passed: got += w
        elif crit: crit_fail = True
        rows.append(dict(rule=label, result="pass" if passed else "fail",
                         detail=(ok_msg if passed else bad_msg)(dv, av)))
    score = round(100 * got / known) if known else 0
    if crit_fail: status = "Incompatible"
    elif any_unknown or not known: status = "Insufficient Information"
    elif score == 100: status = "Compatible"
    else: status = "Partially Compatible"
    return dict(status=status, score=score, rules=rows, warnings=warnings)

# ---------- Routes ----------
ICON = {"Charger": "🔌", "Audio": "🎧", "Hub": "🔀", "Cable": "🪢"}

def prods(q=""):
    rows = db().execute("SELECT * FROM accessories WHERE name LIKE ? OR category LIKE ?", (f"%{q}%",) * 2).fetchall()
    return [dict(r, icon=ICON.get(r["category"], "📦"), specs=json.loads(r["specs"]), mrp=int(round(r["price"] * 1.3, -1))) for r in rows]

@app.route("/")
def home():
    q = request.args.get("q", "")
    return render_template("home.html", items=prods(q), q=q)

@app.route("/product/<int:pid>")
def product(pid):
    r = db().execute("SELECT * FROM accessories WHERE id=?", (pid,)).fetchone()
    if not r: return "Product not found", 404
    p = dict(r, icon=ICON.get(r["category"], "📦"), specs=json.loads(r["specs"]), mrp=int(round(r["price"] * 1.3, -1)))
    return render_template("product.html", p=p)

@app.route("/api/devices")
def devices():
    q = f"%{request.args.get('q', '')}%"
    return jsonify([dict(r) for r in db().execute("SELECT id,name,category FROM devices WHERE name LIKE ? LIMIT 8", (q,))])

@app.route("/api/fit")
def api_fit():
    """Fit check: accessory id + free-text device name typed by the shopper."""
    a = db().execute("SELECT * FROM accessories WHERE id=?", (request.args.get("accessory"),)).fetchone()
    q = request.args.get("q", "").strip()
    d = db().execute("SELECT * FROM devices WHERE lower(name)=lower(?)", (q,)).fetchone() or \
        db().execute("SELECT * FROM devices WHERE name LIKE ?", (f"%{q}%",)).fetchone() if q else None
    if not a: return jsonify(error="Product not found"), 404
    if not d:
        return jsonify(status="Insufficient Information", score=0, device=None, rules=[], alternatives=[],
                       warnings=[f"We don't have \"{q}\" yet. Try a model like iPhone 15 or Galaxy S23." if q else "Type your device name to check fit."])
    res = check(d, a); res.update(device=d["name"], device_id=d["id"], alternatives=[])
    if res["status"] != "Compatible":
        for alt in db().execute("SELECT * FROM accessories WHERE category=? AND id!=?", (a["category"], a["id"])):
            r = check(d, alt)
            if r["status"] == "Compatible":
                res["alternatives"].append(dict(id=alt["id"], name=alt["name"], price=alt["price"], score=r["score"], icon=ICON.get(alt["category"], "📦")))
        res["alternatives"].sort(key=lambda x: x["price"])
    return jsonify(res)

@app.route("/api/fit_all")
def fit_all():
    """Fit status of every product for one saved device (powers badges on listing pages)."""
    d = db().execute("SELECT * FROM devices WHERE id=?", (request.args.get("device"),)).fetchone()
    if not d: return jsonify({})
    out = {}
    for a in db().execute("SELECT * FROM accessories"):
        r = check(d, a); out[a["id"]] = dict(status=r["status"], score=r["score"])
    return jsonify(out)

# if __name__ == "__main__":
#     init_db()
#     app.run(debug=True)
if __name__ == "__main__":
    init_db()
    app.run(debug=True)