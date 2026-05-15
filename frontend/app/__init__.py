from flask import Flask
from .config import Config
from .extensions import csrf


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 확장 초기화
    csrf.init_app(app)

    # Blueprint(라우트 묶음) 등록
    from .routes.main import bp as main_bp
    from .routes.auth import bp as auth_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    
    return app