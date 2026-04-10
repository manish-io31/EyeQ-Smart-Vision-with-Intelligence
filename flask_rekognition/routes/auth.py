"""
Authentication Blueprint
Session persistence: session.permanent = True ensures no redirect on browser refresh.
"""

from flask import (Blueprint, render_template, redirect, url_for,
                   request, flash, jsonify, session)
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember_me") == "on"

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            # ★ CRITICAL: session.permanent = True prevents logout on refresh
            session.permanent = True
            login_user(user, remember=remember)
            flash(f"Welcome, {user.username}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("login.html", show_register=True)
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return render_template("login.html", show_register=True)

        user = User(username=username, email=email or None, role="user")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session.permanent = True
        login_user(user, remember=True)
        flash("Account created!", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("login.html", show_register=True)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/me")
@login_required
def me():
    """AJAX session check — returns 200 if logged in, 401 if expired."""
    return jsonify({
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
    })
