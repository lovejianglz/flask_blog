from . import api
from ..models import User
from flask import jsonify, request, url_for, current_app


@api.route("/user/<int:id>")
def get_user(id):
    """
    返回指定用户
    :param id:
    :return:
    """
    user = User.query.get_or_404(id)
    return jsonify({"user": user.to_json()})


@api.route("/user/<int:id>/posts")
def get_user_posts(id):
    """
    返回指定用户的发布的全部博客
    :param id:
    :return:
    """
    user = User.query.get_or_404(id)
    page = request.args.get("page", 1, type=int)
    pagination = user.posts.paginate(page=page, per_page=current_app.config["FLASK_POSTS_PER_PAGE"],
                                     error_out=False)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for("api.get_user_posts", page=page - 1, id=user.id)
    next = None
    if pagination.has_next:
        next = url_for("api.get_user_posts", page=page - 1, id=user.id)
    return jsonify({"posts": [post.to_json() for post in posts],
                    "next_url": next,
                    "prev_url": prev,
                    "count": pagination.total
                    })


@api.route("user/<int:id>/timeline")
def get_user_followed_posts(id):
    """
    返回指定用户关注者发布的全部博客
    :param id:
    :return:
    """
    user = User.query.get_or_404(id)
    return jsonify({"posts": [post.to_json() for post in user.followed_posts.all()]})
