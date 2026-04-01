from flask import Flask, render_template, request, g, redirect, url_for, session, abort
import sqlite3, os, datetime, urllib.parse

app = Flask(__name__)
app.config['DATABASE'] = 'products.db'
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-change-me")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123") # change via env

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

def get_cart():
    return session.setdefault('cart', {})

def cart_totals(cart):
    if not cart:
        return [], 0.0
    db = get_db()
    ids = list(map(int, cart.keys()))
    placeholders = ",".join("?" for _ in ids)
    rows = db.execute(f'SELECT * FROM products WHERE id IN ({placeholders})', ids).fetchall()
    items, total = [], 0.0
    for r in rows:
        q = int(cart.get(str(r['id']), cart.get(r['id'], 0)))
        line = float(r['price']) * q
        total += line
        items.append({'product': r, 'qty': q, 'line': line})
    return items, total

def login_required():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    return None

# ---------- Health ----------
@app.get('/healthz')
def healthz():
    return "ok", 200

# ---------- Public site ----------
@app.route('/')
def index():
    db = get_db()
    q = request.args.get('q', '').strip()
    cat = request.args.get('cat', '').strip()
    min_price = request.args.get('min', '').strip()
    max_price = request.args.get('max', '').strip()

    sql = 'SELECT * FROM products WHERE 1=1'
    args = []
    if q:
        sql += ' AND (name LIKE? OR description LIKE?)'
        args.extend([f'%{q}%', f'%{q}%'])
    if cat:
        sql += ' AND category =?'
        args.append(cat)
    if min_price:
        try:
            sql += ' AND price >=?'; args.append(float(min_price))
        except Exception:
            pass
    if max_price:
        try:
            sql += ' AND price <=?'; args.append(float(max_price))
        except Exception:
            pass
    sql += ' ORDER BY name'

    products = db.execute(sql, args).fetchall()
    categories = [r['category'] for r in db.execute('SELECT DISTINCT category FROM products ORDER BY category').fetchall()]
    return render_template('index.html', products=products, search_query=q, cart_count=sum(get_cart().values()),
                           categories=categories, active_cat=cat, min_price=min_price, max_price=max_price)

@app.route('/search')
def search():
    return redirect(url_for('index', q=request.args.get('q',''), cat=request.args.get('cat',''),
                            min=request.args.get('min',''), max=request.args.get('max','')))

@app.post('/cart/add/<int:pid>')
def cart_add(pid):
    cart = get_cart()
    key = str(pid)
    cart[key] = int(cart.get(key, 0)) + 1
    session['cart'] = cart
    return redirect(request.referrer or url_for('index'))

@app.post('/cart/update/<int:pid>')
def cart_update(pid):
    qty = max(0, int(request.form.get('qty', 1)))
    cart = get_cart()
    key = str(pid)
    if qty == 0:
        cart.pop(key, None)
    else:
        cart[key] = qty
    session['cart'] = cart
    return redirect(url_for('cart_view'))

@app.get('/cart')
def cart_view():
    cart = get_cart()
    items, total = cart_totals(cart)
    return render_template('cart.html', items=items, total=total, cart_count=sum(cart.values()))

@app.get('/checkout')
def checkout():
    cart = get_cart()
    items, total = cart_totals(cart)
    if not items:
        return redirect(url_for('index'))
    upi_id = os.environ.get("UPI_ID", "example@upi")
    upi_name = os.environ.get("UPI_NAME", "My Fresh Market")
    upi_params = {"pa": upi_id, "pn": upi_name, "am": f"{total:.2f}", "cu": "INR", "tn": "Order payment"}
    upi_link = "upi://pay?" + urllib.parse.urlencode(upi_params)
    return render_template('checkout.html', items=items, total=total, cart_count=sum(cart.values()),
                           upi_link=upi_link, upi_id=upi_id)

@app.post('/checkout')
def place_order():
    cart = get_cart()
    items, total = cart_totals(cart)
    if not items:
        return redirect(url_for('index'))
    name = request.form.get('name','').strip()
    phone = request.form.get('phone','').strip()
    address = request.form.get('address','').strip()
    if not (name and phone and address):
        return redirect(url_for('checkout'))
    db = get_db()
    cur = db.cursor()
    cur.execute('INSERT INTO orders (customer_name, phone, address, total, status, created_at) VALUES (?,?,?,?,?,?)',
                (name, phone, address, total, 'pending', datetime.datetime.utcnow().isoformat()))
    order_id = cur.lastrowid
    for it in items:
        cur.execute('INSERT INTO order_items (order_id, product_id, qty, price) VALUES (?,?,?,?)',
                    (order_id, it['product']['id'], it['qty'], it['product']['price']))
    db.commit()
    session['cart'] = {}
    return render_template('order_success.html', order_id=order_id, total=total)

@app.get('/orders/<int:oid>')
def order_detail(oid):
    db = get_db()
    order = db.execute('SELECT * FROM orders WHERE id=?', (oid,)).fetchone()
    if not order:
        return redirect(url_for('index'))
    items = db.execute('''SELECT oi.qty, oi.price, p.name, p.unit, p.image_url
                          FROM order_items oi JOIN products p ON p.id=oi.product_id
                          WHERE oi.order_id=?''', (oid,)).fetchall()
    return render_template('order_detail.html', order=order, items=items)

# ---------- Admin ----------
@app.get('/admin/login')
def admin_login():
    if session.get('is_admin'):
        return redirect(url_for('admin_home'))
    return render_template('admin_login.html', error=None)

@app.post('/admin/login')
def admin_login_post():
    pw = request.form.get('password','')
    if pw == ADMIN_PASSWORD:
        session['is_admin'] = True
        return redirect(url_for('admin_home'))
    return render_template('admin_login.html', error="Invalid password")

@app.get('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('index'))

@app.get('/admin')
def admin_home():
    r = login_required()
    if r: return r
    db = get_db()
    products = db.execute('SELECT * FROM products ORDER BY name').fetchall()
    return render_template('admin.html', products=products)

@app.get('/admin/product/new')
def admin_product_new():
    r = login_required()
    if r: return r
    return render_template('product_form.html', product=None)

@app.post('/admin/product/new')
def admin_product_create():
    r = login_required()
    if r: return r
    f = request.form
    db = get_db()
    db.execute('INSERT INTO products (name, description, price, unit, image_url, category) VALUES (?,?,?,?,?,?)',
               (f.get('name'), f.get('description'), float(f.get('price') or 0), f.get('unit'), f.get('image_url'), f.get('category') or 'General'))
    db.commit()
    return redirect(url_for('admin_home'))

@app.get('/admin/product/<int:pid>/edit')
def admin_product_edit(pid):
    r = login_required()
    if r: return r
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
    if not product:
        abort(404)
    return render_template('product_form.html', product=product)

@app.post('/admin/product/<int:pid>/edit')
def admin_product_update(pid):
    r = login_required()
    if r: return r
    f = request.form
    db = get_db()
    db.execute('UPDATE products SET name=?, description=?, price=?, unit=?, image_url=?, category=? WHERE id=?',
               (f.get('name'), f.get('description'), float(f.get('price') or 0), f.get('unit'), f.get('image_url'), f.get('category') or 'General', pid))
    db.commit()
    return redirect(url_for('admin_home'))

@app.post('/admin/product/<int:pid>/delete')
def admin_product_delete(pid):
    r = login_required()
    if r: return r
    db = get_db()
    db.execute('DELETE FROM products WHERE id=?', (pid,))
    db.commit()
    return redirect(url_for('admin_home'))

@app.get('/admin/orders')
def admin_orders():
    r = login_required()
    if r: return r
    db = get_db()
    orders = db.execute('SELECT * FROM orders ORDER BY id DESC').fetchall()
    return render_template('admin_orders.html', orders=orders)

@app.post('/admin/orders/<int:oid>/status')
def admin_order_status(oid):
    r = login_required()
    if r: return r
    status = request.form.get('status','pending')
    db = get_db()
    db.execute('UPDATE orders SET status=? WHERE id=?', (status, oid))
    db.commit()
    return redirect(url_for('admin_orders'))

if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        with app.app_context():
            init_db()
    app.run(debug=True, host='0.0.0.0')