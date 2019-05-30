from . import api
from ..models import Post, Permission
from flask import jsonify, request, g, url_for, current_app
from .. import db
from .decorators import permission_required
from .errors import forbidden


@api.route("/posts/")
def get_posts():
    """
    返回全部博客
    :return:
    """
    page = request.args.get("page", 1, type=int)
    pagination = Post.query.paginate(page=page, per_page=current_app.config["FLASK_POSTS_PER_PAGE"],
                                     error_out=False)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for("api.get_posts", page=page-1)
    next = None
    if pagination.has_next:
        next = url_for("api.get_posts", page=page+1)
    return jsonify({"posts": [post.to_json() for post in posts],
                    "next_url": next,
                    "prev_url": prev,
                    "count": pagination.total
                    })


@api.route("/posts/", methods=["POST"])
@permission_required(Permission.WRITE)
def new_post():
    """
    创建一篇博客文章
    :return:
    """
    post = Post.from_json(request.json)
    post.author = g.current_user
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_json()), 201, {"Location": url_for("api.get_post", id=post.id)}


@api.route("/posts/<int:id>")
def get_post(id):
    """
    返回指定博客文章
    :param id:
    :return:
    """
    post = Post.query.get_or_404(id)
    return jsonify(post.to_json())

@api.route("/posts/<int:id>", methods=["PUT"])
def edit_post(id):
    """
    修改指定博客文章
    :param id:
    :return:
    """
    post = Post.query.get_or_404(id)
    if g.current_user != post.author and not g.current_user.can(Permission.ADMIN):
        return forbidden("Insufficient permissions")
    post.body = request.json.get("body", post.body)
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_json())


