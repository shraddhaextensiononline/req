from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length
from flask_wtf.file import FileField, FileAllowed

from .models import RequirementStatus


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


class RequirementForm(FlaskForm):
    customer_name = StringField("Customer Name", validators=[DataRequired(), Length(max=100)])
    contact_info = StringField("Contact Info", validators=[DataRequired(), Length(max=120)])
    details = TextAreaField("Requirement Details", validators=[DataRequired(), Length(max=2000)])
    image = FileField("Product Image", validators=[FileAllowed(["png", "jpg", "jpeg", "gif", "webp"], "Images only!")])
    staff_name = SelectField(
        "Staff Name",
        validators=[DataRequired()],
        choices=[("", "Select staff...")],
        coerce=str,
    )
    submit = SubmitField("Save")


class UpdateStatusForm(FlaskForm):
    status = SelectField(
        "Status",
        choices=[
            (RequirementStatus.NEW.value, "New"),
            (RequirementStatus.IN_PROGRESS.value, "In Progress"),
            (RequirementStatus.FULFILLED.value, "Fulfilled"),
        ],
        validators=[DataRequired()],
    )
    fulfill_image = FileField(
        "Product Image (required when marking Fulfilled)",
        validators=[FileAllowed(["png", "jpg", "jpeg", "gif", "webp"], "Images only!")],
    )
    submit = SubmitField("Update")


