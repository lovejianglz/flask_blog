from . import auth
from flask import g, render_template, flash, request, url_for, redirect
from .forms import LoginForms,RegistrationForms, ChangePasswordForms, \
    ResetPasswordEmailForms, ResetPasswordForms, ChangeEmailForms
from datetime import datetime
from ..models import User
from flask_login import login_user, current_user, logout_user, login_required
from .. import db
from ..email import send_mail


@auth.before_app_request  # 对全部的路由都是有效的
def before_request():
    if current_user.is_authenticated:  # 用户已登陆
        current_user.ping()  # 更新用户最近登陆的时间
        if not current_user.confirmed \
                and request.endpoint \
                and request.blueprint != "auth" \
                and request.endpoint != "static":
            # 当用户已登录且未点击认证链接，访问的路径未在auth下，则跳转认证提示页
            return redirect(url_for("auth.unconfirmed"))


@auth.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForms()
    if not current_user.is_authenticated:
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user is not None and user.verify_password(form.password.data):
                login_user(user, form.remember_me.data)
                next = request.args.get("next")
                if next is None or not next.startswith("/"):
                    next = url_for("main.index")
                return redirect(next)
            flash("Invalid username or password")
        return render_template("auth/login.html", form=form, current_time=datetime.utcnow())
    return redirect(url_for("main.index"))  # 如果已经登陆过，重定向至首页


@auth.route("/logout", methods=["GET"])
def logout():
    logout_user()
    flash("You have been logged out")
    return redirect(url_for("main.index"))


@auth.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForms()
    if form.validate_on_submit():
        user = User(username=form.name.data, password=form.password1.data, email=form.email.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        # 发送确认邮件
        send_mail(user.email, "Please confirm your account", "auth/mail/confirm", user=user, token=token)
        flash("You can login now!")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form, current_time=datetime.utcnow())


@auth.route("/confirm/<token>")
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for("main.index"))
    if current_user.confirm(token):
        db.session.commit()
        flash("You have confirmed your account. Thanks!")
    else:
        flash("The confirmation link is invalid or has expired.")
    return redirect(url_for("main.index"))


@auth.route("/unconfirmed")
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for("main.index"))
    return render_template("auth/unconfirmed.html", current_time=datetime.utcnow())


@auth.route("/confirm")
@login_required
def resend_confirmation():
    if not current_user.confirmed:
        token = current_user.generate_confirmation_token()
        send_mail(current_user.email, "Please confirm your account", "auth/mail/confirm", user=current_user, token=token)
        flash("A new confirmatino email has been sent to you by email.")
        return redirect(url_for("main.index"))


@auth.route("/changepwd", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForms()
    if form.validate_on_submit():
        current_user.password = form.new_password1.data
        db.session.add(current_user)
        db.session.commit()
        flash("Change password successfully")
        return redirect(url_for("main.index"))
    return render_template("auth/change_password.html", form=form, current_time=datetime.utcnow())


@auth.route("/resertpwd", methods=["GET", "POST"])
def send_reset_password_mail():
    form = ResetPasswordEmailForms()
    if form.validate_on_submit():
        token = User().generate_reset_password_token()
        send_mail(form.email.data, "Reset password", "auth/mail/reset_password", token=token)
        flash("Please check your email, and follow the steps to reset your password!")
        redirect(url_for("auth.login"))
    return render_template("auth/send_reset_password_email.html", form=form, current_time=datetime.utcnow())


@auth.route("/resertpwd/<token>", methods=["GET", "POST"])
def reset_password(token):
    if User().confirm_reset_password(token):
        form = ResetPasswordForms()
        if form.validate_on_submit():
            password = form.password1.data
            g.user.password = password
            db.session.add(g.user)
            db.session.commit()
            flash("Password reset successfully.")
            return redirect(url_for("auth.login"))
        return render_template("auth/reset_password.html", form=form, current_time=datetime.utcnow())
    flash("Incorrect link, please check or accquire again.")
    return redirect(url_for("main.index"))


@auth.route("/changemail", methods=["GET", "POST"])
@login_required
def change_email():
    form = ChangeEmailForms()
    if form.validate_on_submit():
        token = current_user.generate_change_email_token(form.mail.data)
        send_mail(form.mail.data, "Flasky-Confirm Email", "auth/mail/change_email",
                  token=token, user=current_user)
        flash("account's email has changed, please check your emial and finish the follow steps")
        return redirect(url_for("main.index"))
    return render_template("auth/change_email.html", form=form, current_time=datetime.utcnow())


@auth.route("/changemail/<token>", methods=["GET"])
def change_email_confirm(token):
    new_email = User().confirm_change_email(token)
    if g.user.confirmed:
        flash("You can login know!")
    if new_email:
        if current_user:
            logout_user()
        if g.user.change_email(new_email):
            db.session.commit()
        flash("You have confirmed your new email. You can login now!")
    else:
        flash("The confirmation link is invalid or has expired.")
    return redirect(url_for("auth.login"))
