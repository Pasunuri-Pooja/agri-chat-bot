# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from io import BytesIO, StringIO
import csv
import os

from database import init_db, db, User, ChatHistory
from chatbot_model import process_message

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret_key")
init_db(app)


# ---------------- USER ROUTES ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    """Login page"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Please enter username and password", "warning")
            return redirect(url_for("index"))

        # Admin shortcut
        if username == "admin":
            return redirect(url_for("admin_login"))

        user = User.get_by_username(username)
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("chat"))
        flash("Invalid username or password", "danger")
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """User registration"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            flash("Please enter username and password", "warning")
            return redirect(url_for("register"))
        if User.get_by_username(username):
            flash("Username already exists", "danger")
            return redirect(url_for("register"))
        User.create(username, password)
        flash("Registered successfully — please login", "success")
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/chat", methods=["GET", "POST"])
def chat():
    """Chat page — GET shows UI + user's past chats, POST handles a message"""
    if "user_id" not in session:
        return redirect(url_for("index"))

    # POST: incoming message (AJAX form)
    if request.method == "POST":
        user_input = request.form.get("message", "").strip()
        lang = request.form.get("lang", "en")
        if not user_input:
            return jsonify({"response": "Please enter a message."})

        # Process message -> returns bot response translated to dest_lang
        bot_response = process_message(user_input, dest_lang=lang)

        # Save conversation in DB (visible to admin)
        ChatHistory.create(session["user_id"], user_input, bot_response)

        return jsonify({"response": bot_response})

    # GET: show chat UI + previous messages for this user
    chats = ChatHistory.query.filter_by(user_id=session["user_id"]).order_by(ChatHistory.timestamp.asc()).all()
    return render_template("chat.html", username=session.get("username"), chats=chats)


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("index"))


# ---------------- ADMIN ROUTES ----------------
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    """Simple admin login (username=admin / password=admin123 by default)"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == "admin" and password == "admin123":
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin credentials", "danger")
    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    q = request.args.get("q", "").strip()
    if q:
        # join with users so we can search username + message + response
        chats = (ChatHistory.query
                 .join(User, ChatHistory.user_id == User.id)
                 .filter(
                     (User.username.ilike(f"%{q}%")) |
                     (ChatHistory.message.ilike(f"%{q}%")) |
                     (ChatHistory.response.ilike(f"%{q}%"))
                 )
                 .order_by(ChatHistory.timestamp.desc())
                 .all())
    else:
        chats = ChatHistory.query.order_by(ChatHistory.timestamp.desc()).all()

    return render_template("admin_dashboard.html", chats=chats, query=q)


@app.route("/admin/download")
def admin_download():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    chats = ChatHistory.query.join(User, ChatHistory.user_id == User.id).order_by(ChatHistory.timestamp.desc()).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "User ID", "Username", "Message", "Response", "Timestamp"])
    for c in chats:
        writer.writerow([c.id, c.user_id, c.user.username if c.user else "Unknown", c.message, c.response, c.timestamp])

    mem = BytesIO()
    mem.write(output.getvalue().encode("utf-8"))
    mem.seek(0)
    output.close()
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="chat_history.csv")


@app.route("/admin/clear_history", methods=["POST"])
def clear_history():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    ChatHistory.query.delete()
    db.session.commit()
    flash("Chat history cleared", "success")
    return redirect(url_for("admin_dashboard"))


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)