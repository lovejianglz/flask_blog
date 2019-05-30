import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "hard to guess string"
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.163.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 994))
    # MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", True)
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", True)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "lovejianglz@163.com")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    FLASKY_MAIL_SUBJECT_PREFIX = "[Flasky]"
    FLASKY_MAIL_SENDER = os.environ.get("FLASKY_MAIL_SENDER", "Flasky Admin<lovejianglz@163.com>")
    FLASKY_ADMIN = os.environ.get("FLASKY_ADMIN", "lovejianglz@163.com")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOGIN_DISABLED = False
    FLASK_POSTS_PER_PAGE = 20
    FLASK_FOLLOWERS_PER_PAGE = 20
    FLASK_COMMENTS_PER_PAGE = 20
    SQLALCHEMY_RECORD_QUERIES = True
    FLASK_SLOW_DB_QUERY_TIME = 0.5
    SSL_REDIRECT = False  # 是否开启HTTPS

    @classmethod
    def init_app(cls, app):
        pass


class DevelopmentConfig(Config):
    # DEBUG = True
    MAIL_DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DEV_DATABASE_URL") or "sqlite:///" + os.path.join(basedir, "database",
                                                                                                "dev-blog.sqlite")


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False  # 禁用CSRF保护
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL") or "sqlite://"


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(basedir, "database",
                                                                                            "blog.sqlite")
    SSL_REDIRECT = True


class NginxConfig(ProductionConfig):
    @classmethod
    def init_app(cls, app):
        super().init_app(app)

        import logging
        from logging import StreamHandler, FileHandler
        file_handler = FileHandler("./log/flask.log")
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)

        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
    "nginx": NginxConfig
}
