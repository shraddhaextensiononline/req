import os
from uuid import uuid4
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user

from .. import db
from ..forms import RequirementForm, UpdateStatusForm
from ..models import Requirement, RequirementStatus, Department, User


requirements_bp = Blueprint("requirements", __name__)


@requirements_bp.route("/")
@login_required
def dashboard():
    # Read filters
    staff = request.args.get("staff", "").strip()
    customer = request.args.get("customer", "").strip()
    status = (request.args.get("status", "open") or "open").strip().lower()

    query = db.select(Requirement).where(Requirement.department == current_user.department)

    if staff:
        query = query.where(Requirement.staff_name.ilike(f"%{staff}%"))
    if customer:
        query = query.where(Requirement.customer_name.ilike(f"%{customer}%"))

    if status == "open":
        query = query.where(Requirement.status.in_([RequirementStatus.NEW, RequirementStatus.IN_PROGRESS]))
    elif status in {"new", "in_progress", "fulfilled"}:
        query = query.where(Requirement.status == RequirementStatus(status.upper()))
    # else: 'all' shows everything

    items = db.session.execute(query.order_by(Requirement.created_at.desc())).scalars().all()

    # Staff list for convenience filter per department
    dept_staff = {
        Department.GIFTS: ["Threeshma", "Ansuya", "Anita", "Harika", "Praveen"],
        Department.STATIONERY: ["Mastaan", "Sunita", "Akash", "Rajesh"],
        Department.TOYS: ["Sony", "Sai", "Satya"],
        Department.BOOKS: ["Anjan", "Shiva", "Lavanya"],
    }
    staff_list = dept_staff.get(current_user.department, [])

    return render_template(
        "requirements/dashboard.html",
        items=items,
        Department=Department,
        RequirementStatus=RequirementStatus,
        filter_staff=staff,
        filter_customer=customer,
        filter_status=status,
        staff_list=staff_list,
        dept_title=current_user.department.value,
        public_view=False,
    )


@requirements_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_requirement():
    form = RequirementForm()
    # Populate staff choices based on logged-in user's department
    dept_staff = {
        Department.GIFTS: ["Threeshma", "Ansuya", "Anita", "Harika", "Praveen"],
        Department.STATIONERY: ["Mastaan", "Sunita", "Akash", "Rajesh"],
        Department.TOYS: ["Sony", "Sai", "Satya"],
        Department.BOOKS: ["Anjan", "Shiva", "Lavanya"],
    }
    staff_list = dept_staff.get(current_user.department, [])
    form.staff_name.choices = [("", "Select staff...")] + [(s, s) for s in staff_list]
    if form.validate_on_submit():
        requirement = Requirement(
            customer_name=form.customer_name.data,
            contact_info=form.contact_info.data,
            details=form.details.data,
            staff_name=form.staff_name.data,
            department=current_user.department,
            created_by=current_user,
        )
        image_file = form.image.data
        if image_file and getattr(image_file, "filename", ""):
            original_name = secure_filename(image_file.filename)
            ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
            if ext not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
                flash("Invalid image type.", "danger")
                return render_template("requirements/create.html", form=form)
            unique_name = f"{uuid4().hex}.{ext}"
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
            image_file.save(save_path)
            requirement.image_filename = unique_name
        db.session.add(requirement)
        db.session.commit()
        flash("Requirement created", "success")
        return redirect(url_for("requirements.dashboard"))
    return render_template("requirements/create.html", form=form)


@requirements_bp.route("/<int:req_id>", methods=["GET", "POST"])
@login_required
def detail(req_id: int):
    requirement = db.session.get(Requirement, req_id)
    if requirement is None:
        flash("Requirement not found", "warning")
        return redirect(url_for("requirements.dashboard"))
    if requirement.department != current_user.department and not getattr(current_user, "is_admin", False):
        flash("Requirement not found", "warning")
        return redirect(url_for("requirements.dashboard"))
    form = UpdateStatusForm(status=requirement.status.value)
    if form.validate_on_submit():
        new_status = RequirementStatus(form.status.data)
        # If moving to FULFILLED, require image if none exists yet
        if new_status == RequirementStatus.FULFILLED and not requirement.image_filename:
            image_file = form.fulfill_image.data
            if not image_file or not getattr(image_file, "filename", ""):
                flash("Please upload a product image to mark as Fulfilled.", "danger")
                return render_template("requirements/detail.html", item=requirement, form=form, from_admin=request.args.get("from_admin"))
            original_name = secure_filename(image_file.filename)
            ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
            if ext not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
                flash("Invalid image type.", "danger")
                return render_template("requirements/detail.html", item=requirement, form=form, from_admin=request.args.get("from_admin"))
            unique_name = f"{uuid4().hex}.{ext}"
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
            image_file.save(save_path)
            requirement.image_filename = unique_name
        requirement.status = new_status
        db.session.commit()
        flash("Status updated", "success")
        return redirect(url_for("requirements.detail", req_id=req_id, from_admin=request.args.get("from_admin")))
    return render_template("requirements/detail.html", item=requirement, form=form, from_admin=request.args.get("from_admin"))


@requirements_bp.route("/uploads/<path:filename>")
def uploaded_file(filename: str):
    # Publicly accessible: images shown in public detail views
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@requirements_bp.route("/browse")
def browse_redirect():
    """Public entry: accepts ?dept=GIFTS and redirects to pretty URL."""
    dept_param = (request.args.get("dept") or "").upper()
    try:
        dept = Department[dept_param]
    except Exception:
        flash("Please select a valid department.", "warning")
        return redirect(url_for("auth.login"))
    return redirect(url_for("requirements.browse_dept", dept=dept.name))


@requirements_bp.route("/dept/<dept>")
def browse_dept(dept: str):
    """Public department dashboard with filters and quick-create form link."""
    try:
        department_enum = Department[dept.upper()]
    except Exception:
        flash("Department not found", "warning")
        return redirect(url_for("auth.login"))

    staff = request.args.get("staff", "").strip()
    customer = request.args.get("customer", "").strip()
    status = (request.args.get("status", "open") or "open").strip().lower()

    query = db.select(Requirement).where(Requirement.department == department_enum)
    if staff:
        query = query.where(Requirement.staff_name.ilike(f"%{staff}%"))
    if customer:
        query = query.where(Requirement.customer_name.ilike(f"%{customer}%"))
    if status == "open":
        query = query.where(Requirement.status.in_([RequirementStatus.NEW, RequirementStatus.IN_PROGRESS]))
    elif status in {"new", "in_progress", "fulfilled"}:
        query = query.where(Requirement.status == RequirementStatus(status.upper()))

    items = db.session.execute(query.order_by(Requirement.created_at.desc())).scalars().all()

    dept_staff = {
        Department.GIFTS: ["Threeshma", "Ansuya", "Anita", "Harika", "Praveen"],
        Department.STATIONERY: ["Mastaan", "Sunita", "Akash", "Rajesh"],
        Department.TOYS: ["Sony", "Sai", "Satya"],
        Department.BOOKS: ["Anjan", "Shiva", "Lavanya"],
    }
    staff_list = dept_staff.get(department_enum, [])

    return render_template(
        "requirements/dashboard.html",
        items=items,
        Department=Department,
        RequirementStatus=RequirementStatus,
        filter_staff=staff,
        filter_customer=customer,
        filter_status=status,
        staff_list=staff_list,
        dept_title=department_enum.value,
        dept_key=department_enum.name,
        public_view=True,
    )


@requirements_bp.route("/dept/<dept>/<int:req_id>", methods=["GET", "POST"])
def public_detail(dept: str, req_id: int):
    try:
        department_enum = Department[dept.upper()]
    except Exception:
        flash("Department not found", "warning")
        return redirect(url_for("auth.login"))

    requirement = db.session.get(Requirement, req_id)
    if requirement is None or requirement.department != department_enum:
        flash("Requirement not found", "warning")
        return redirect(url_for("requirements.browse_dept", dept=department_enum.name))

    # If an admin is logged in, send them to the private management view
    if getattr(current_user, "is_authenticated", False) and getattr(current_user, "is_admin", False):
        return redirect(url_for("requirements.detail", req_id=req_id))

    # Allow public status updates with same validation rules
    form = UpdateStatusForm(status=requirement.status.value)
    if form.validate_on_submit():
        new_status = RequirementStatus(form.status.data)
        if new_status == RequirementStatus.FULFILLED and not requirement.image_filename:
            image_file = form.fulfill_image.data
            if not image_file or not getattr(image_file, "filename", ""):
                flash("Please upload a product image to mark as Fulfilled.", "danger")
                return render_template(
                    "requirements/detail.html",
                    item=requirement,
                    form=form,
                    from_admin=None,
                    public_view=True,
                    cancel_url=url_for("requirements.browse_dept", dept=department_enum.name),
                    dept_key=department_enum.name,
                )
            original_name = secure_filename(image_file.filename)
            ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
            if ext not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
                flash("Invalid image type.", "danger")
                return render_template(
                    "requirements/detail.html",
                    item=requirement,
                    form=form,
                    from_admin=None,
                    public_view=True,
                    cancel_url=url_for("requirements.browse_dept", dept=department_enum.name),
                    dept_key=department_enum.name,
                )
            unique_name = f"{uuid4().hex}.{ext}"
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
            image_file.save(save_path)
            requirement.image_filename = unique_name
        requirement.status = new_status
        db.session.commit()
        flash("Status updated", "success")
        return redirect(url_for("requirements.public_detail", dept=department_enum.name, req_id=req_id))

    return render_template(
        "requirements/detail.html",
        item=requirement,
        form=form,
        from_admin=None,
        public_view=True,
        cancel_url=url_for("requirements.browse_dept", dept=department_enum.name),
        dept_key=department_enum.name,
    )


@requirements_bp.route("/dept/<dept>/<int:req_id>/edit", methods=["GET", "POST"])
def public_edit(dept: str, req_id: int):
    try:
        department_enum = Department[dept.upper()]
    except Exception:
        flash("Department not found", "warning")
        return redirect(url_for("auth.login"))

    requirement = db.session.get(Requirement, req_id)
    if requirement is None or requirement.department != department_enum:
        flash("Requirement not found", "warning")
        return redirect(url_for("requirements.browse_dept", dept=department_enum.name))

    form = RequirementForm(obj=requirement)
    dept_staff = {
        Department.GIFTS: ["Threeshma", "Ansuya", "Anita", "Harika", "Praveen"],
        Department.STATIONERY: ["Mastaan", "Sunita", "Akash", "Rajesh"],
        Department.TOYS: ["Sony", "Sai", "Satya"],
        Department.BOOKS: ["Anjan", "Shiva", "Lavanya"],
    }
    staff_list = dept_staff.get(requirement.department, [])
    form.staff_name.choices = [("", "Select staff...")] + [(s, s) for s in staff_list]

    if form.validate_on_submit():
        requirement.customer_name = form.customer_name.data
        requirement.contact_info = form.contact_info.data
        requirement.details = form.details.data
        requirement.staff_name = form.staff_name.data

        image_file = form.image.data
        if image_file and getattr(image_file, "filename", ""):
            original_name = secure_filename(image_file.filename)
            ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
            if ext not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
                flash("Invalid image type.", "danger")
                return render_template("requirements/edit.html", form=form, item=requirement)
            unique_name = f"{uuid4().hex}.{ext}"
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
            image_file.save(save_path)
            requirement.image_filename = unique_name

        db.session.commit()
        flash("Requirement updated", "success")
        return redirect(url_for("requirements.public_detail", dept=department_enum.name, req_id=requirement.id))

    return render_template("requirements/edit.html", form=form, item=requirement)


@requirements_bp.route("/dept/<dept>/<int:req_id>/delete", methods=["POST"])
def public_delete(dept: str, req_id: int):
    try:
        department_enum = Department[dept.upper()]
    except Exception:
        flash("Department not found", "warning")
        return redirect(url_for("auth.login"))

    requirement = db.session.get(Requirement, req_id)
    if requirement is None or requirement.department != department_enum:
        flash("Requirement not found", "warning")
        return redirect(url_for("requirements.browse_dept", dept=department_enum.name))

    db.session.delete(requirement)
    db.session.commit()
    flash("Requirement deleted", "success")
    return redirect(url_for("requirements.browse_dept", dept=department_enum.name))


@requirements_bp.route("/dept/<dept>/create", methods=["GET", "POST"])
def create_requirement_public(dept: str):
    """Public requirement creation for a specific department (no login).
    Uses the department's default user as created_by.
    """
    try:
        department_enum = Department[dept.upper()]
    except Exception:
        flash("Department not found", "warning")
        return redirect(url_for("auth.login"))

    form = RequirementForm()

    # Populate staff choices based on department
    dept_staff = {
        Department.GIFTS: ["Threeshma", "Ansuya", "Anita", "Harika", "Praveen"],
        Department.STATIONERY: ["Mastaan", "Sunita", "Akash", "Rajesh"],
        Department.TOYS: ["Sony", "Sai", "Satya"],
        Department.BOOKS: ["Anjan", "Shiva", "Lavanya"],
    }
    staff_list = dept_staff.get(department_enum, [])
    form.staff_name.choices = [("", "Select staff...")] + [(s, s) for s in staff_list]

    if form.validate_on_submit():
        # Find a default user for this department (seeded user, first non-admin)
        default_user = db.session.execute(
            db.select(User)
            .where(User.department == department_enum, User.is_admin.is_(False))
            .order_by(User.id.asc())
        ).scalars().first()

        if default_user is None:
            flash("No default user found for this department.", "danger")
            return render_template("requirements/create.html", form=form, cancel_url=url_for("requirements.browse_dept", dept=department_enum.name))

        requirement = Requirement(
            customer_name=form.customer_name.data,
            contact_info=form.contact_info.data,
            details=form.details.data,
            staff_name=form.staff_name.data,
            department=department_enum,
            created_by=default_user,
        )

        image_file = form.image.data
        if image_file and getattr(image_file, "filename", ""):
            original_name = secure_filename(image_file.filename)
            ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
            if ext not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
                flash("Invalid image type.", "danger")
                return render_template("requirements/create.html", form=form, cancel_url=url_for("requirements.browse_dept", dept=department_enum.name))
            unique_name = f"{uuid4().hex}.{ext}"
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
            image_file.save(save_path)
            requirement.image_filename = unique_name

        db.session.add(requirement)
        db.session.commit()
        flash("Requirement created", "success")
        return redirect(url_for("requirements.browse_dept", dept=department_enum.name))

    return render_template(
        "requirements/create.html",
        form=form,
        cancel_url=url_for("requirements.browse_dept", dept=department_enum.name),
    )
@requirements_bp.route("/<int:req_id>/edit", methods=["GET", "POST"])
@login_required
def edit_requirement(req_id: int):
    requirement = db.session.get(Requirement, req_id)
    if requirement is None:
        flash("Requirement not found", "warning")
        return redirect(url_for("requirements.dashboard"))
    if requirement.department != current_user.department and not getattr(current_user, "is_admin", False):
        flash("Not authorized", "danger")
        return redirect(url_for("requirements.dashboard"))

    form = RequirementForm(obj=requirement)
    # Populate staff choices based on the requirement's department
    dept_staff = {
        Department.GIFTS: ["Threeshma", "Ansuya", "Anita", "Harika", "Praveen"],
        Department.STATIONERY: ["Mastaan", "Sunita", "Akash", "Rajesh"],
        Department.TOYS: ["Sony", "Sai", "Satya"],
        Department.BOOKS: ["Anjan", "Shiva", "Lavanya"],
    }
    staff_list = dept_staff.get(requirement.department, [])
    form.staff_name.choices = [("", "Select staff...")] + [(s, s) for s in staff_list]

    if form.validate_on_submit():
        requirement.customer_name = form.customer_name.data
        requirement.contact_info = form.contact_info.data
        requirement.details = form.details.data
        requirement.staff_name = form.staff_name.data

        image_file = form.image.data
        if image_file and getattr(image_file, "filename", ""):
            original_name = secure_filename(image_file.filename)
            ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
            if ext not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
                flash("Invalid image type.", "danger")
                return render_template("requirements/edit.html", form=form, item=requirement)
            unique_name = f"{uuid4().hex}.{ext}"
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
            image_file.save(save_path)
            requirement.image_filename = unique_name

        db.session.commit()
        flash("Requirement updated", "success")
        return redirect(url_for("requirements.detail", req_id=requirement.id, from_admin=request.args.get("from_admin")))

    return render_template("requirements/edit.html", form=form, item=requirement)


@requirements_bp.route("/<int:req_id>/delete", methods=["POST"])
@login_required
def delete_requirement(req_id: int):
    requirement = db.session.get(Requirement, req_id)
    if requirement is None:
        flash("Requirement not found", "warning")
        return redirect(url_for("requirements.dashboard"))
    if requirement.department != current_user.department and not getattr(current_user, "is_admin", False):
        flash("Not authorized", "danger")
        return redirect(url_for("requirements.dashboard"))

    from_admin = request.args.get("from_admin")
    db.session.delete(requirement)
    db.session.commit()
    flash("Requirement deleted", "success")
    if from_admin:
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("requirements.dashboard"))

