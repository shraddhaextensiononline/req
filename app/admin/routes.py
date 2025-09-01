from flask import Blueprint, render_template, abort, request
from flask_login import login_required, current_user

from .. import db
from ..models import Requirement, Department, RequirementStatus


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def require_admin():
    if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
        abort(403)


@admin_bp.route("/")
@login_required
def dashboard():
    require_admin()
    # Filters
    staff = request.args.get("staff", "").strip()
    customer = request.args.get("customer", "").strip()
    status = (request.args.get("status", "open") or "open").strip().lower()

    by_department = {}
    for dept in Department:
        q = db.select(Requirement).where(Requirement.department == dept)
        if staff:
            q = q.where(Requirement.staff_name.ilike(f"%{staff}%"))
        if customer:
            q = q.where(Requirement.customer_name.ilike(f"%{customer}%"))
        if status == "open":
            q = q.where(Requirement.status.in_([RequirementStatus.NEW, RequirementStatus.IN_PROGRESS]))
        elif status in {"new", "in_progress", "fulfilled"}:
            q = q.where(Requirement.status == RequirementStatus(status.upper()))
        items = db.session.execute(q.order_by(Requirement.created_at.desc())).scalars().all()
        by_department[dept] = items
    return render_template(
        "admin/dashboard.html",
        by_department=by_department,
        Department=Department,
        RequirementStatus=RequirementStatus,
        filter_staff=staff,
        filter_customer=customer,
        filter_status=status,
    )


