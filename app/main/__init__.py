from flask import Blueprint
from ..models import Permission
from datetime import datetime

main = Blueprint("main", __name__)


@main.app_context_processor
def inject_permissions():
    """
        在渲染模板时，把常用的参数在这里传入
    :return:
    """
    return dict(Permission=Permission, current_time=datetime.utcnow())


from . import views, errors
