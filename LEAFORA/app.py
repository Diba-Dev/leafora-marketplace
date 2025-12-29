from flask import Flask, render_template, redirect, url_for, session, request, flash
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from utils.db import get_db_connection
import sqlite3
import random
import string

app = Flask(__name__)
app.secret_key = "leafora_secret_key"  # change in production

# =============================
# CONTENT STRUCTURE
# =============================
# 1. AUTHENTICATION & DECORATORS
# 2. HOME & BOOK LISTING
# 3. BOOK DETAILS & REVIEWS
# 4. USER AUTHENTICATION (SIGNUP/LOGIN/LOGOUT)
# 5. ORDERS MANAGEMENT (CREATE, ACCEPT, REJECT)
# 6. USER PROFILE & NOTIFICATIONS
# 7. BOOK MANAGEMENT (ADD, EDIT, DELETE)
# 8. ADMIN DASHBOARD & USER MANAGEMENT
# =============================

# =============================
# 1. AUTHENTICATION & DECORATORS
# =============================
# Purpose: Protect routes that require user login

def login_required(f):
    """Decorator to check if user is logged in before accessing a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# =============================
# 2. HOME & BOOK LISTING
# =============================
# Purpose: Display homepage with latest books and book search/filter functionality
# http://127.0.0.1:5000/
@app.route("/")
def home():
    """Display homepage."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, buy_price, image
        FROM books
        ORDER BY created_at DESC
        LIMIT 8
    """)
    new_books = cursor.fetchall()

    conn.close()
    return render_template("index.html", new_books=new_books)


@app.route("/books")
def books():
    """Display all books with filters (name, author, category, price)."""
    name = request.args.get("name", "")
    author = request.args.get("author", "")
    category = request.args.get("category", "")
    max_price = int(request.args.get("max_price", 1500))

    conn = get_db_connection()
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT category FROM books")
    categories = [row["category"] for row in cursor.fetchall()]

    query = "SELECT * FROM books WHERE 1=1"
    params = []

    if name:
        query += " AND title LIKE ?"
        params.append(f"%{name}%")
    if author:
        query += " AND author LIKE ?"
        params.append(f"%{author}%")
    if category:
        query += " AND category = ?"
        params.append(category)
    if max_price:
        query += " AND buy_price <= ?"
        params.append(max_price)

    cursor.execute(query, params)
    books = cursor.fetchall()
    conn.close()

    return render_template(
        "books.html",
        books=books,
        categories=categories,
        name=name,
        author=author,
        category=category,
        max_price=max_price
    )


@app.route("/books_ajax")
def books_ajax():
    """AJAX endpoint for dynamic book filtering without page reload."""
    name = request.args.get("name", "")
    author = request.args.get("author", "")
    category = request.args.get("category", "")
    max_price = int(request.args.get("max_price", 1500))

    conn = get_db_connection()
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()

    query = "SELECT * FROM books WHERE 1=1"
    params = []

    if name:
        query += " AND title LIKE ?"
        params.append(f"%{name}%")
    if author:
        query += " AND author LIKE ?"
        params.append(f"%{author}%")
    if category:
        query += " AND category = ?"
        params.append(category)
    if max_price:
        query += " AND buy_price <= ?"
        params.append(max_price)

    cursor.execute(query, params)
    books = cursor.fetchall()
    conn.close()

    return render_template("books_grid.html", books=books)


@app.route("/contact")
def contact():
    """Display contact page."""
    return render_template("contact.html")


# =============================
# 3. BOOK DETAILS & REVIEWS
# =============================
# Purpose: Display individual book details and manage book reviews

@app.route("/book/<int:book_id>")
def book(book_id):
    """Display book details with reviews."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    book = cursor.fetchone()

    if not book:
        flash("Book not found.", "error")
        conn.close()
        return redirect(url_for("books"))

    cursor.execute("""
        SELECT r.rating, r.comment, u.full_name
        FROM reviews r
        JOIN users u ON r.user_id = u.id
        WHERE r.book_id = ?
        ORDER BY r.created_at DESC
    """, (book_id,))
    reviews = cursor.fetchall()
    conn.close()
    return render_template("book.html", book=book, reviews=reviews)


@app.route("/book/<int:book_id>/review", methods=["POST"])
@login_required
def add_review(book_id):
    """Add a review (rating and comment) to a book."""
    rating = request.form.get("rating")
    comment = request.form.get("comment", "").strip()

    if not rating or not comment:
        flash("Please provide both rating and comment.", "error")
        return redirect(url_for("book", book_id=book_id))

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError
    except ValueError:
        flash("Invalid rating value.", "error")
        return redirect(url_for("book", book_id=book_id))

    conn = get_db_connection()
    cursor = conn.cursor()
    conn.execute("PRAGMA journal_mode=WAL;")

    try:
        cursor.execute("""
            INSERT INTO reviews (book_id, user_id, rating, comment)
            VALUES (?, ?, ?, ?)
        """, (book_id, session["user_id"], rating, comment))
        conn.commit()
        flash("Review submitted successfully.", "success")
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if "UNIQUE" in str(e):
            flash("You have already reviewed this book.", "error")
        else:
            flash(f"Database error: {e}", "error")
    finally:
        conn.close()

    return redirect(url_for("book", book_id=book_id))


# =============================
# 4. USER AUTHENTICATION
# =============================
# Purpose: Handle user signup, login, and logout
# http://127.0.0.1:5000/signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Register a new user account."""
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"] #admin@email.com
        phone = request.form["phone"]
        address = request.form["address"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("signup"))

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        # admin@email.com
        if cursor.fetchone():
            flash("Email already registered.", "error")
            conn.close()
            return redirect(url_for("signup"))

        password_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (full_name, email, password_hash, phone, address, role)
            VALUES (?, ?, ?, ?, ?, 'user')
        """, (name, email, password_hash, phone, address))
        conn.commit()
        conn.close()

        flash("Account created successfully. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate user and create session."""
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return redirect(url_for("login"))

        user_dict = dict(user)

        session["user_id"] = user_dict["id"]
        session["user_name"] = user_dict["full_name"]
        session["role"] = user_dict["role"]
        session["user_email"] = user_dict["email"]
        session["user_phone"] = user_dict["phone"]
        session["user_address"] = user_dict["address"]

        flash("Logged in successfully.", "success")
        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Clear session and logout user."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


# =============================
# 5. ORDERS MANAGEMENT
# =============================
# Purpose: Create, accept, and reject book orders (buy/rent)

# http://127.0.0.1:5000/order/4/buy
@app.route("/order/<int:book_id>/<string:order_type>", methods=["POST"])
@login_required
def create_order(book_id, order_type):
    """Create a new buy/rent order for a book."""
    conn = get_db_connection()
    cursor = conn.cursor()
    conn.execute("PRAGMA journal_mode=WAL;")

    try:
        cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        book = cursor.fetchone()
        if not book:
            flash("Book not found.", "error")
            return redirect(url_for("books"))

        rent_months = int(request.form.get("rent_months", 1)) if order_type == "rent" else None
        total_price = book["buy_price"] if order_type == "buy" else book["rent_price"] * rent_months

        transaction_code = f"LF{datetime.now().strftime('%Y%m%d')}{random.randint(1000,9999)}"

        cursor.execute("""
            INSERT INTO orders (book_id, buyer_id, order_type, rent_months, total_price, transaction_code, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (book_id, session["user_id"], order_type, rent_months, total_price, transaction_code))
        order_id = cursor.lastrowid

        buyer_email = session.get("user_email", "Unknown")
        message = f"{buyer_email} placed an order for your book '{book['title']}'."
        cursor.execute("""
            INSERT INTO notifications (sender_id, receiver_id, book_id, order_id, message, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        """, (session["user_id"], book["owner_id"], book_id, order_id, message))

        cursor.execute("SELECT full_name, email, phone FROM users WHERE id = ?", (book["owner_id"],))
        owner = cursor.fetchone()

        order = {
            "id": order_id,
            "transaction_code": transaction_code,
            "created_at": datetime.now(),
            "order_type": order_type,
            "rent_months": rent_months,
            "total_price": total_price,
            "title": book["title"],
            "author": book["author"],
            "category": book["category"],
            "condition": book["condition"],
            "image": book["image"],
            "buyer_email": session.get("user_email"),
            "buyer_phone": session.get("user_phone"),
            "buyer_address": session.get("user_address"),
            "owner_name": owner["full_name"],
            "owner_email": owner["email"],
            "owner_phone": owner["phone"],
            "qr_code": None
        }

        conn.commit()
        flash("Order placed successfully! The owner will review your request.", "success")
        # http://127.0.0.1:5000/receipt/11
        return render_template("receipt.html", order=order)

    except sqlite3.Error as e:
        conn.rollback()
        flash(f"Database error: {e}", "error")
        return redirect(url_for("books"))

    finally:
        conn.close()


@app.route("/owner/order/<int:order_id>/accept", methods=["POST"])
@login_required
def accept_order(order_id):
    """Accept a buyer's order (owner action)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT o.*, b.owner_id, b.title AS book_title, o.book_id, o.buyer_id
            FROM orders o
            JOIN books b ON o.book_id = b.id
            WHERE o.id = ?
        """, (order_id,))
        order = cursor.fetchone()
        if not order or order["owner_id"] != session["user_id"]:
            flash("Unauthorized.", "error")
            return redirect(url_for("profile"))

        cursor.execute("UPDATE orders SET status='accepted' WHERE id=?", (order_id,))
        cursor.execute("DELETE FROM notifications WHERE order_id=? AND receiver_id=?", (order_id, session["user_id"]))

        message = f"Your order for '{order['book_title']}' has been accepted."
        cursor.execute("""
            INSERT INTO notifications (sender_id, receiver_id, book_id, order_id, message, status)
            VALUES (?, ?, ?, ?, ?, 'done')
        """, (session["user_id"], order["buyer_id"], order["book_id"], order_id, message))

        conn.commit()
        flash("Order accepted.", "success")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"Database error: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for("profile"))


@app.route("/owner/order/<int:order_id>/reject", methods=["POST"])
@login_required
def reject_order(order_id):
    """Reject a buyer's order (owner action)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT o.*, b.owner_id, b.title AS book_title, o.book_id, o.buyer_id
            FROM orders o
            JOIN books b ON o.book_id = b.id
            WHERE o.id = ?
        """, (order_id,))
        order = cursor.fetchone()
        if not order or order["owner_id"] != session["user_id"]:
            flash("Unauthorized.", "error")
            return redirect(url_for("profile"))

        cursor.execute("UPDATE orders SET status='rejected' WHERE id=?", (order_id,))
        cursor.execute("DELETE FROM notifications WHERE order_id=? AND receiver_id=?", (order_id, session["user_id"]))

        message = f"Your order for '{order['book_title']}' has been rejected."
        cursor.execute("""
            INSERT INTO notifications (sender_id, receiver_id, book_id, order_id, message, status)
            VALUES (?, ?, ?, ?, ?, 'done')
        """, (session["user_id"], order["buyer_id"], order["book_id"], order_id, message))

        conn.commit()
        flash("Order rejected.", "info")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"Database error: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for("profile"))


@app.route("/receipt/<int:order_id>")
@login_required
def receipt(order_id):
    """Display order receipt for buyer or seller."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT o.id AS order_id, o.book_id, o.buyer_id, o.order_type, o.rent_months, 
                   o.total_price, o.status, o.created_at,
                   b.title AS book_title, b.author, b.category, b.condition, b.image,
                   b.owner_id,
                   u1.full_name AS owner_name, u1.email AS owner_email, u1.phone AS owner_phone,
                   u2.full_name AS buyer_name, u2.email AS buyer_email, u2.phone AS buyer_phone
            FROM orders o
            JOIN books b ON o.book_id = b.id
            JOIN users u1 ON b.owner_id = u1.id
            JOIN users u2 ON o.buyer_id = u2.id
            WHERE o.id = ?
        """, (order_id,))

        order = cursor.fetchone()

        if not order:
            flash("Receipt not found.", "error")
            return redirect(url_for("profile"))

        if order["buyer_id"] != session["user_id"] and order["owner_id"] != session["user_id"]:
            flash("Unauthorized access to this receipt.", "error")
            return redirect(url_for("profile"))

        order = dict(order)
        order["created_at"] = datetime.strptime(order["created_at"], "%Y-%m-%d %H:%M:%S")

    finally:
        conn.close()

    return render_template("receipt.html", order=order)


# =============================
# 6. USER PROFILE & NOTIFICATIONS
# =============================
# Purpose: Manage user profile, view orders, notifications, and clear notifications

@app.route("/profile")
@login_required
def profile():
    """Display user profile with orders, books, and notifications."""
    user_id = session["user_id"]
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()

        cursor.execute("""
            SELECT 
                o.id AS id,
                o.book_id,
                o.order_type,
                o.status,
                o.total_price,
                b.title AS book_title
            FROM orders o
            JOIN books b ON o.book_id = b.id
            WHERE o.buyer_id = ?
            ORDER BY o.created_at DESC
        """, (user_id,))
        orders = cursor.fetchall()

        cursor.execute("""
            SELECT *, buy_price AS sell_price
            FROM books
            WHERE owner_id=?
            ORDER BY created_at DESC
        """, (user_id,))
        user_books = cursor.fetchall()

        cursor.execute("""
            SELECT o.*, b.title AS book_title, u.full_name AS buyer_name, u.email AS buyer_email
            FROM orders o
            JOIN books b ON o.book_id = b.id
            JOIN users u ON o.buyer_id = u.id
            WHERE b.owner_id = ?
            ORDER BY o.created_at DESC
        """, (user_id,))
        user_book_orders = cursor.fetchall()

        cursor.execute("""
            SELECT n.*, u.full_name AS sender_name, b.title AS book_title, b.owner_id AS book_owner_id
            FROM notifications n
            JOIN users u ON n.sender_id = u.id
            LEFT JOIN books b ON n.book_id = b.id
            WHERE n.receiver_id = ?
            ORDER BY n.created_at DESC
        """, (user_id,))
        notifications = cursor.fetchall()

    finally:
        conn.close()

    return render_template(
        "profile.html",
        user=user,
        orders=orders,
        user_books=user_books,
        user_book_orders=user_book_orders,
        notifications=notifications
    )


@app.route("/update_profile", methods=["POST"])
@login_required
def update_profile():
    """Update user profile information."""
    full_name = request.form["full_name"]
    email = request.form["email"]
    phone = request.form["phone"]
    address = request.form["address"]

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE users SET full_name=?, email=?, phone=?, address=? WHERE id=?
        """, (full_name, email, phone, address, session["user_id"]))
        conn.commit()
        flash("Profile updated successfully!", "success")
    finally:
        conn.close()
    return redirect(url_for("profile"))


@app.route("/clear_notifications", methods=["POST"])
@login_required
def clear_notifications():
    """Clear all completed notifications for the user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            DELETE FROM notifications
            WHERE receiver_id = ?
              AND status = 'done'
        """, (session["user_id"],))
        conn.commit()
        flash("Notifications cleared.", "success")
    finally:
        conn.close()
    return redirect(url_for("profile"))


# =============================
# 7. BOOK MANAGEMENT
# =============================
# Purpose: Add, edit, and delete books by users

@app.route("/add_book", methods=["POST"])
@login_required
def add_book():
    """Add a new book to sell/rent."""
    title = request.form["title"]
    author = request.form["author"]
    category = request.form["category"]
    description = request.form.get("description", "")
    condition = request.form.get("condition", "Like New")
    buy_price = request.form["sell_price"]
    rent_price = request.form.get("rent_price") or None
    location = request.form["location"]
    cover_image = request.files.get("cover_image")

    filename = None
    if cover_image and cover_image.filename:
        filename = f"{int(datetime.now().timestamp())}_{cover_image.filename}"
        cover_image.save(f"static/images/Book/{filename}")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO books (
              owner_id, title, author, category, description,
              condition, buy_price, rent_price, location, image, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            title,
            author,
            category,
            description,
            condition,
            buy_price,
            rent_price,
            location,
            filename,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        flash("Book added successfully!", "success")
    finally:
        conn.close()

    return redirect(url_for("profile"))


@app.route("/edit_book/<int:book_id>", methods=["GET", "POST"])
@login_required
def edit_book(book_id):
    """Edit an existing book listing."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM books WHERE id=? AND owner_id=?", (book_id, session["user_id"]))
        book = cursor.fetchone()
        if not book:
            flash("Book not found or you do not have permission.", "error")
            return redirect(url_for("profile"))

        if request.method == "POST":
            title = request.form["title"]
            author = request.form["author"]
            category = request.form["category"]
            description = request.form.get("description", "")
            buy_price = request.form["sell_price"]
            rent_price = request.form.get("rent_price") or None
            location = request.form["location"]

            cover_image = request.files.get("cover_image")
            filename = book["image"]
            if cover_image:
                filename = f"{datetime.now().timestamp()}_{cover_image.filename}"
                cover_image.save(f"static/images/Book/{filename}")

            condition = request.form.get("condition", "Like New")
            cursor.execute("""
                UPDATE books
                SET title=?, author=?, category=?, description=?, condition=?,
                    buy_price=?, rent_price=?, location=?, image=?
                WHERE id=?
            """, (
                title,
                author,
                category,
                description,
                condition,
                buy_price,
                rent_price,
                location,
                filename,
                book_id
            ))

            conn.commit()
            flash("Book updated successfully!", "success")
            return redirect(url_for("profile"))

    finally:
        conn.close()
    return render_template("edit_book.html", book=book)


@app.route("/delete_book/<int:book_id>", methods=["POST"])
@login_required
def delete_book(book_id):
    """Delete a book listing."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM books WHERE id=? AND owner_id=?", (book_id, session["user_id"]))
        book = cursor.fetchone()
        if not book:
            flash("Book not found or you do not have permission.", "error")
            return redirect(url_for("profile"))

        cursor.execute("DELETE FROM books WHERE id=?", (book_id,))
        conn.commit()
        flash("Book deleted successfully!", "success")
    # except sqlite3.Error:
    #     conn.rollback()
    #     flash("Cannot delete book. It may have related orders or reviews.", "error")
    #     return redirect(url_for("profile"))
    finally:
        conn.close()
    return redirect(url_for("profile"))


# =============================
# 8. ADMIN DASHBOARD & USER MANAGEMENT
# =============================
# Purpose: Admin and super-admin tools to manage users and content

@app.route("/admin")
@login_required
def admin():
    """Display admin dashboard with users and books."""
    if session.get("role") not in ["admin", "super_admin"]:
        flash("Access denied.", "error")
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, full_name, email, phone, role FROM users")
        users = cursor.fetchall()
        cursor.execute("""
            SELECT b.*, u.full_name AS owner_name
            FROM books b
            JOIN users u ON b.owner_id = u.id
        """)
        books = cursor.fetchall()
    finally:
        conn.close()
    return render_template("admin.html", users=users, books=books)


@app.route("/admin/promote/<int:user_id>", methods=["POST"])
@login_required
def promote_user(user_id):
    """Promote a user to admin (super-admin only)."""
    if session.get("role") != "super_admin":
        flash("Only Super Admin can promote users.", "error")
        return redirect(url_for("admin"))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        target = cursor.fetchone()
        if not target:
            flash("User not found.", "error")
        elif target["role"] == "super_admin":
            flash("Cannot modify a Super Admin.", "error")
        else:
            cursor.execute("UPDATE users SET role='admin' WHERE id=?", (user_id,))
            conn.commit()
            flash("User promoted to admin.", "success")
    finally:
        conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/demote/<int:user_id>", methods=["POST"])
@login_required
def demote_user(user_id):
    """Demote an admin to user (super-admin only)."""
    if session.get("role") != "super_admin":
        flash("Only super admin can demote admins.", "error")
        return redirect(url_for("admin"))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user or user["role"] == "super_admin":
            flash("Cannot demote this user.", "error")
        else:
            cursor.execute("UPDATE users SET role='user' WHERE id=?", (user_id,))
            conn.commit()
            flash("Admin demoted to user.", "success")
    finally:
        conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/book/delete/<int:book_id>", methods=["POST"])
@login_required
def admin_delete_book(book_id):
    """Delete a book (admin only)."""
    if session.get("role") not in ["admin", "super_admin"]:
        flash("Access denied.", "error")
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM books WHERE id=?", (book_id,))
        conn.commit()
        flash("Book removed.", "success")
    except sqlite3.Error:
        conn.rollback()
        flash("Cannot delete book. It may have related orders or reviews.", "error")
    finally:
        conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/user/delete/<int:user_id>", methods=["POST"])
@login_required
def admin_delete_user(user_id):
    """Delete a user (super-admin only)."""
    if session.get("role") != "super_admin":
        flash("Only Super Admin can delete users.", "error")
        return redirect(url_for("admin"))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT role FROM users WHERE id=?", (user_id,))
        target = cursor.fetchone()
        if not target:
            flash("User not found.", "error")
        elif target["role"] == "super_admin":
            flash("You cannot delete a Super Admin.", "error")
        else:
            cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
            conn.commit()
            flash("User removed successfully.", "success")
    except sqlite3.Error:
        conn.rollback()
        flash("Cannot delete user. User has related data.", "error")
    finally:
        conn.close()
    return redirect(url_for("admin"))

# =============================
# RUN APPLICATION
# =============================
if __name__ == "__main__":
    app.run(debug=True, port=4000)