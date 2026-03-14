from flask import Flask, render_template, request, redirect, session, url_for
import psycopg2
from psycopg2.extras import DictCursor
import os
import random
import datetime
import base64

app = Flask(__name__)
app.secret_key = "government_secure_key_2026"

# This pulls the connection string from Render's settings later
DATABASE_URL = os.environ.get("DATABASE_URL")

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

# ---------------- DATABASE INIT ----------------
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        name TEXT, email TEXT, password TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS complaints(
        tracking_id TEXT PRIMARY KEY, 
        user_id INTEGER, 
        department TEXT,
        category TEXT, 
        incident TEXT, 
        description TEXT,
        address TEXT, 
        file TEXT, 
        priority INTEGER,
        status TEXT, 
        date TEXT, 
        time TEXT
    )""")
    conn.commit()
    cur.close()
    conn.close()

init_db()

def set_priority(category):
    high = ["assault", "women", "child", "fire", "ambulance", "sos"]
    medium = ["missing", "roads", "water", "electricity", "health"]
    cat = category.lower()
    if cat in high: return 1
    elif cat in medium: return 2
    return 3

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return redirect(url_for('login'))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name, email, password = request.form["name"], request.form["email"], request.form["password"]
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email, password = request.form["email"], request.form["password"]
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            session["user"] = user[0]
            return redirect(url_for('dashboard'))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/dashboard")
def dashboard():
    if "user" not in session: return redirect(url_for('login'))
    return render_template("dashboard.html")

@app.route("/police")
def police(): return render_template("police.html")

@app.route("/municipal")
def municipal(): return render_template("municipal.html")

@app.route("/emergency")
def emergency(): return render_template("emergency.html")

@app.route("/municipal/roads")
def municipal_roads(): return render_template("municipal_roads.html")

@app.route("/municipal/water")
def municipal_water(): return render_template("municipal_water.html")

@app.route("/municipal/health")
def municipal_health(): return render_template("municipal_health.html")

@app.route("/municipal/electricity")
def municipal_electric(): return render_template("municipal_electric.html")

@app.route("/sos")
def sos_emergency():
    if "user" not in session: return redirect(url_for('login'))
    tracking = "SOS" + str(random.randint(100000, 999999))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO complaints VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
               (tracking, session["user"], "police", "sos", "SOS Emergency", "SOS TRIGGERED", "GPS Requested", "", 1, "Active", str(datetime.date.today()), datetime.datetime.now().strftime("%H:%M:%S")))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('my_complaints'))

@app.route("/complaint/<department>/<category>", methods=["GET", "POST"])
def complaint(department, category):
    if "user" not in session: return redirect(url_for('login'))
    if request.method == "POST":
        description = request.form.get("description")
        address = request.form.get("location")
        file = request.files.get("image")
        image_data = request.form.get("image_data")
        filename = ""

        if file and file.filename != "":
            filename = str(random.randint(1000, 9999)) + "_" + file.filename
            file.save(os.path.join(UPLOAD_FOLDER, filename))
        elif image_data and "," in image_data:
            filename = f"cam_{random.randint(10000, 99999)}.png"
            header, encoded = image_data.split(",", 1)
            with open(os.path.join(UPLOAD_FOLDER, filename), "wb") as f:
                f.write(base64.b64decode(encoded))

        tracking = "TRK" + str(random.randint(100000, 999999))
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO complaints VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                   (tracking, session["user"], department, category, category, description, address, filename, set_priority(category), "Active", str(datetime.date.today()), datetime.datetime.now().strftime("%H:%M:%S")))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('my_complaints'))
    return render_template("complaint.html", department=department, category=category)

@app.route("/my_complaints")
def my_complaints():
    if "user" not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor) # Uses DictCursor to handle data easily
    cur.execute("SELECT * FROM complaints WHERE user_id=%s", (session["user"],))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("my_complaints.html", data=data)

@app.route("/track", methods=["GET", "POST"])
def track():
    data = None
    if request.method == "POST":
        tracking = request.form["tracking"]
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        cur.execute("SELECT * FROM complaints WHERE tracking_id=%s", (tracking,))
        data = cur.fetchone()
        cur.close()
        conn.close()
    return render_template("track.html", data=data)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form["username"] == "admin@gov.in" and request.form["password"] == "admin123":
            session["admin"] = True
            return redirect(url_for('admin_dashboard'))
    return render_template("admin_login.html")

@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session: return redirect(url_for('admin'))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute("SELECT * FROM complaints ORDER BY date DESC")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin.html", data=data)

@app.route("/update_status", methods=["POST"])
def update_status():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE complaints SET status=%s WHERE tracking_id=%s", (request.form["status"], request.form["tracking"]))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(debug=True)