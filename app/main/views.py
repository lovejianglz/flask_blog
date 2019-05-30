from flask import render_template, session, request, url_for, redirect, \
    current_app, flash, abort, make_response, Response
from . import main
from .forms import NameForm, EditProfileForm, EditProfileAdminForm, PostForm, CommentForm
from .. import db
from ..models import User, Permission, Post, Follow, Comment
from ..email import send_mail
from flask_login import login_required, current_user
from ..decorators import admin_required, permission_required
from flask_sqlalchemy import get_debug_queries

@main.route("/", methods=["GET", "POST"])
def index():
    form = PostForm()
    if form.validate_on_submit() and current_user.can(Permission.WRITE):
        post = Post(body=form.body.data,
                    author=current_user)  # 例子中，使用了 current_user._get_current_object()获取真正的用户对象
        db.session.add(post)
        db.session.commit()
        flash("Successfully post!")
        return redirect(url_for("main.index"))
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get("show_followed", ""))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config["FLASK_POSTS_PER_PAGE"], error_out=False)
    posts = pagination.items
    return render_template("index.html", form=form, posts=posts,
                           show_followed=show_followed, pagination=pagination)


@main.route("/user/<username>")
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get("page", 1, type=int)
    pagination = Post.query.filter_by(author=user).order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config["FLASK_POSTS_PER_PAGE"], error_out=False)
    posts = pagination.items
    return render_template("user.html", user=user, posts=posts, pagination=pagination)


@main.route("/secret")
@login_required
def secret():
    return "Only authencated user are allowed"


@main.route("/admin")
@login_required
@admin_required
def for_admin_only():
    return "For administrators!"


@main.route("/moderate")
@login_required
@permission_required(Permission.MODERATE)
def for_moderators_only():
    return "For comment moderators"


@main.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        db.session.commit()
        flash("Your profile has been updated.")
        return redirect(url_for(".user", username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template("edit_profile.html", form=form)


@main.route("/edit-profile/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.location = form.location.data
        user.confirmed = form.confirmed.data
        user.role = form.role.data
        user.name = form.name.data
        user.about_me: str = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash("The profile has been updated.")
        return redirect(url_for(".user", username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.location.data = user.location
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.about_me.data = user.about_me
    return render_template("edit_profile.html", form=form, user=user)


@main.route("/post/<int:post_id>", methods=["GET", "POST"])
def post(post_id):
    post = Post.query.get_or_404(post_id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, post=post, author=current_user)
        db.session.add(comment)
        db.session.commit()
        flash("You have commented this post!")
        return redirect(url_for("main.post", post_id=post.id, page=-1))
    page = request.args.get("page", default=1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // current_app.config["FLASK_COMMENTS_PER_PAGE"] + 1
    pagination = Comment.query.filter_by(post=post, disabled=False). \
        paginate(page=page, per_page=current_app.config["FLASK_COMMENTS_PER_PAGE"], error_out=True)
    comments = pagination.items
    return render_template("post.html", posts=[post], comments=comments,
                           pagination=pagination, form=form)


@main.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMIN):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        db.session.commit()
        flash("The post has been updated!")
        return redirect("main.post", id=id)
    form.body.data = post.body
    return render_template("edit_post.html", form=form)


@main.route("/follow/<int:user_id>")
@login_required
@permission_required(Permission.FOLLOW)
def follow(user_id):
    user = User.query.get_or_404(user_id)
    if current_user != user and not current_user.is_following(user):
        current_user.follow(user)
        db.session.commit()
        flash("you have followed {}".format(user.username))
    else:
        flash("you can not follow {}".format(user.username))
    return redirect(url_for("main.user", username=user.username))


@main.route("/unfollow/<int:user_id>")
@login_required
def unfollow(user_id):
    user = User.query.get_or_404(user_id)
    if current_user != user and current_user.is_following(user):
        current_user.unfollow(user)
        db.session.commit()
        flash("You have unfollowed {}.".format(user.username))
    else:
        flash("You have not followed {} yet.".format(user.username))
    target = get_previous_page()
    return redirect(target)


@main.route("/followers/<int:user_id>")
def followers(user_id):
    user = User.query.get_or_404(user_id)
    if user is None:
        flash("Invalid user.")
        return redirect(url_for("main.index"))
    page = request.args.get("page", 1, type=int)
    pagination = user.followers.order_by(Follow.timestamp.desc()).paginate(
        page, per_page=current_app.config["FLASK_FOLLOWERS_PER_PAGE"], error_out=False)
    follows = [{"user": item.follower, "timestamp": item.timestamp} for item in pagination.items]
    return render_template("followers.html", user=user, title="Followers of", follows=follows,
                           endpoint="main.followers", pagination=pagination)


@main.route("/followed_by/<int:user_id>")
def followed_by(user_id):
    user = User.query.get_or_404(user_id)
    if user is None:
        flash("Invalid user.")
        return redirect(url_for("main.index"))
    page = request.args.get("page", 1, type=int)
    pagination = user.followed.order_by(Follow.timestamp.desc()).paginate(
        page, per_page=current_app.config["FLASK_FOLLOWERS_PER_PAGE"], error_out=False)
    follows = [{"user": item.followed, "timestamp": item.timestamp} for item in pagination.items]
    return render_template("followers.html", user=user, title="Followed by", follows=follows,
                           endpoint="main.followed_by", pagination=pagination)


@main.route("/all_posts")
@login_required
def all_posts():
    resp = make_response(redirect(url_for("main.index")))
    resp.set_cookie("show_followed", "")
    return resp


@main.route("/followed_posts")
@login_required
def followed_posts():
    resp = make_response(redirect(url_for("main.index")))
    resp.set_cookie("show_followed", "True")
    return resp


@main.route("/moderate_comments")
@permission_required(Permission.MODERATE)
def moderate_comments():
    comment_id = request.args.get("comment_id", -1, type=int)
    comment_disable = request.args.get("comment_disable", type=bool)
    print(comment_disable)
    if comment_id != -1:  # 如果传入的参数里有 comment_id
        comment = Comment.query.get_or_404(comment_id)
        comment.disabled = comment_disable
        db.session.add(comment)
        db.session.commit()
        if comment_disable:
            flash("comment has disabled")
        else:
            flash("comment has enabled")
    page = request.args.get("page", 1)
    pagination = Comment.query.order_by(Comment.timestamp).paginate(
        page=page, per_page=current_app.config["FLASK_COMMENTS_PER_PAGE"],
        error_out=True, max_per_page=None)
    comments = pagination.items
    return render_template("moderate_comments.html", comments=comments,
                           pagination=pagination, moderate=True)


def get_previous_page():
    """
        获取当前请求的前一个页面
    :return:
    """
    pre_page = None
    for target in request.args.get('next'), request.referrer:
        if target:
            pre_page = target
            break
    if pre_page is None:
        pre_page = url_for("main.index")
    return pre_page


@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config["FLASK_SLOW_DB_QUERY_TIME"]:
            current_app.logger.warning("Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n"%
                                       (query.statement, query.parameters, query.duration, query.context))
    return response
