from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure secret key

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'

# SQLite database configuration
DATABASE = 'menu.db'

def create_table():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL
        )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        menu_id INTEGER,
        quantity INTEGER,
        FOREIGN KEY (menu_id) REFERENCES menu (id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT NOT NULL,
        address TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        menu_id INTEGER,
        quantity INTEGER,
        total_amount REAL,  -- Add this line
        FOREIGN KEY (menu_id) REFERENCES menu (id)
    )''')

    conn.commit()
    conn.close()

# Initialize the database table
create_table()

# Route to display the menu with an option to add items to the cart
@app.route('/')
def show_menu():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM menu')
    menu_items = cursor.fetchall()
    conn.close()
    return render_template('menu.html', menu_items=menu_items)

# ========================ADMIN PORTAL==================================================

# Route to display menu items and transaction history in admin portal
@app.route('/admin_portal', methods=['GET', 'POST'])
def admin_portal():
    if 'username' not in session:
        return redirect(url_for('admin_login'))
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, price FROM menu')
    menu_items = cursor.fetchall()

    cursor.execute('''
        SELECT orders.id, user_name, address, phone_number, menu.name, orders.quantity,orders.total_amount
        FROM orders
        JOIN menu ON orders.menu_id = menu.id
    ''')
    transaction_history = cursor.fetchall()
    conn.close()
    return render_template('admin_portal.html', menu_items=menu_items, transaction_history=transaction_history)

# Route to handle admin login
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['username'] = username
            return redirect(url_for('admin_portal'))
        else:
            return render_template('admin_login.html', error='Invalid credentials')

    return render_template('admin_login.html')

# Route to log out the admin user
@app.route('/admin_logout')
def admin_logout():
    session.pop('username', None)
    return redirect(url_for('show_menu'))


# Route to handle adding a new product
@app.route('/add_product', methods=['POST'])
def add_product():
    name = request.form['name']
    price = float(request.form['price'])

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO menu (name, price) VALUES (?,  ?)', (name, price))
    conn.commit()
    conn.close()

    # Redirect back to the admin portal after adding the product
    return redirect(url_for('admin_portal'))

@app.route('/delete_product/<int:item_id>', methods=['POST'])
def delete_product(item_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM menu WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()

    # Redirect back to the admin portal after deleting the product
    return redirect(url_for('admin_portal'))

# Route to handle logout
@app.route('/logout')
def logout():
    # Perform any logout-related actions if needed
    # For simplicity, this example just clears the session
    session.clear()
    return redirect(url_for('show_menu'))  # Redirect to the menu or another appropriate route


#============================================VIEW CART========================================

@app.route('/view_cart')
def view_cart():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT menu.name, menu.price, cart.quantity
        FROM cart
        JOIN menu ON cart.menu_id = menu.id
    ''')
    cart_items = cursor.fetchall()
    conn.close()
    return render_template('view_cart.html', cart_items=cart_items)

@app.route('/add_to_cart/<int:menu_id>', methods=['POST'])
def add_to_cart(menu_id):
    quantity = 1  # Fixed quantity

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM cart WHERE menu_id = ?', (menu_id,))
    existing_cart_item = cursor.fetchone()

    if existing_cart_item:
        # Update quantity if the item is already in the cart
        cursor.execute('UPDATE cart SET quantity = quantity + ? WHERE id = ?', (quantity, existing_cart_item[0]))
    else:
        # Add a new item to the cart
        cursor.execute('INSERT INTO cart (menu_id, quantity) VALUES (?, ?)', (menu_id, quantity))

    conn.commit()
    conn.close()

    return redirect(url_for('show_menu'))

@app.route('/remove_from_cart/<int:menu_id>', methods=['POST'])
def remove_from_cart(menu_id):
    quantity = -1  # Fixed quantity

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM cart WHERE menu_id = ?', (menu_id,))
    existing_cart_item = cursor.fetchone()

    if existing_cart_item:
        # Update quantity if the item is already in the cart
        cursor.execute('UPDATE cart SET quantity = quantity + ? WHERE id = ?', (quantity, existing_cart_item[0]))
    else:
        # Add a new item to the cart
        cursor.execute('INSERT INTO cart (menu_id, quantity) VALUES (?, ?)', (menu_id, quantity))

    conn.commit()
    conn.close()

    return redirect(url_for('show_menu'))

# ========================CHECKOUT==================================================

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        user_name = request.form['user_name']
        address = request.form['address']
        phone_number = request.form['phone_number']

        # Get items from the cart
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT menu_id, quantity FROM cart')
        cart_items = cursor.fetchall()

        # Calculate the total amount
        total_amount = 0
        for menu_id, quantity in cart_items:
            cursor.execute('SELECT price FROM menu WHERE id = ?', (menu_id,))
            price = cursor.fetchone()[0]
            total_amount += price * quantity

        # Save order details and items in the orders table
        for menu_id, quantity in cart_items:
            cursor.execute('INSERT INTO orders (user_name, address, phone_number, menu_id, quantity, total_amount) VALUES (?, ?, ?, ?, ?, ?)',
                           (user_name, address, phone_number, menu_id, quantity, total_amount))

        # Clear the cart after placing the order
        cursor.execute('DELETE FROM cart')
        conn.commit()
        conn.close()

        return redirect(url_for('show_bill'))  # Redirect to the bill page after placing the order

    return render_template('checkout.html')

@app.route('/bill')
def show_bill():
    # Get user details and items from the last order
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_name, address, phone_number, total_amount FROM orders ORDER BY id DESC LIMIT 1')
    order_details = cursor.fetchone()

    if order_details:
        user_name, address, phone_number, total_amount = order_details

        cursor.execute('''
            SELECT menu.name, orders.quantity, menu.price
            FROM orders
            JOIN menu ON orders.menu_id = menu.id
            WHERE orders.id = (SELECT MAX(id) FROM orders)
        ''')
        cart_items = cursor.fetchall()

        conn.close()

        return render_template('bill.html', user_name=user_name, address=address,
                               phone_number=phone_number,
                               cart_items=cart_items, total_amount=total_amount)

    # Redirect to the menu if no order is found
    conn.close()
    return redirect(url_for('show_menu'))

if __name__ == '__main__':
    app.run(debug=True)
