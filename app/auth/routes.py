from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from .. import db
from ..forms import LoginForm
from ..models import User


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        next_page = request.args.get("next")
        return redirect(next_page or url_for("requirements.dashboard"))

    # Check if this is an admin login request
    is_admin_login = request.args.get("admin") == "1"
    
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).filter_by(username=form.username.data)).scalar_one_or_none()
        if user and user.check_password(form.password.data):
            # If admin login requested, verify user is admin
            if is_admin_login and not getattr(user, "is_admin", False):
                flash("Access denied. Admin privileges required.", "danger")
                return render_template("auth/login.html", form=form, is_admin_login=True)
            
            login_user(user)
            flash("Logged in successfully.", "success")
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            if getattr(user, "is_admin", False):
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("requirements.dashboard"))
        flash("Invalid credentials", "danger")
    
    # Pass is_admin_login flag to template
    return render_template("auth/login.html", form=form, is_admin_login=is_admin_login)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


