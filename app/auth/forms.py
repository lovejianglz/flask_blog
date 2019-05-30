from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo
from ..models import User
from wtforms import ValidationError
from flask_login import current_user


class LoginForms(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(1)])
    remember_me = BooleanField("Keep me logged in")
    submit = SubmitField("Log In")


class RegistrationForms(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Length(1, 64), Email()])
    name = StringField("Username", validators=[DataRequired(), Length(1, 64),
                                               Regexp("^[a-zA-Z][A-Za-z0-9_.]*$", 0,
                                                      "Username must have only lettets, numbers, dots or underscores")])
    password1 = PasswordField("Password", validators=[DataRequired(), EqualTo("password2", message="Password must match.")])
    password2 = PasswordField("Confirm password", validators=[DataRequired()])
    submit = SubmitField("Register")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("Email already registered.")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("Username already in use.")


class ChangePasswordForms(FlaskForm):
    old_password = PasswordField("Old password", validators=[DataRequired()])
    new_password1 = PasswordField("New password", validators=[DataRequired()])
    new_password2 = PasswordField("Confirm password",
                                  validators=[DataRequired(), EqualTo("new_password1", message="Confirm not match!")])
    submit = SubmitField("Confirm")

    def validate_old_password(self, field):
        if not current_user.verify_password(field.data):
            raise ValidationError("Old password is incorrect!")


class ResetPasswordEmailForms(FlaskForm):
    # 用于用户提交重设密码
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Reset password")

    def validate_email(self, field):
        if not User.query.filter_by(email=field.data).first():
            raise ValidationError("Incorrect email address")


class ResetPasswordForms(FlaskForm):
    # 用于用户点击重置链接后，重置密码
    password1 = PasswordField("Password", validators=[DataRequired()])
    password2 = PasswordField("Confirm password",
                              validators=[DataRequired(), EqualTo("password1", message="confirm not match")])
    submit = SubmitField("Reset Password!")


class ChangeEmailForms(FlaskForm):
    mail = StringField("New email", validators=[DataRequired(), Email()])
    submit = SubmitField("Change Email")

    def validate_mail(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("email already exist.")
