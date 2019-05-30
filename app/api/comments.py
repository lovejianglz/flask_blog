from app import db
from app.api.decorators import permission_required
from . import api
from ..models import Comment, Post, Permission
from flask import jsonify, request, g


@api.route("/comments/")
def get_comments():
    """
    返回所有评论
    :return:
    """
    comments = Comment.query.all()
    return jsonify({"comments": [comment.to_json() for comment in comments]})


@api.route("/comments/<int:id>")
def get_comment(id):
    """
    返回一条指定评论
    :param id:
    :return:
    """
    comment = Comment.query.get_or_404(id)
    return jsonify({"comment": comment.to_json()})


@api.route("/posts/<int:id>/comments")
def get_posts_comments(id):
    """
    返回指定博客文章的有效评论
    :param id:
    :return:
    """
    post = Post.query.get_or_404(id)
    return jsonify({"comments": [comment.to_json() for comment in post.comments.filter_by(disabled=False).all()]})


@api.route("/posts/<int:id>/comments", methods=["POST"])
@permission_required(Permission.COMMENT)
def new_posts_comments(id):
    """
    对指定博客文章新增评论
    :param id:
    :return:
    """
    post = Post.query.get_or_404(id)
    comment = Comment.from_json(request.json)
    comment.author = g.current_user
    comment.post = post
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_json())
