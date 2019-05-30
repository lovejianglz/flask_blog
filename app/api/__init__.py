from flask import Blueprint

api = Blueprint("api", __name__)

from . import authentication, comments, decorators, errors, posts, users

@api.route("/")
def index():
    return "123"