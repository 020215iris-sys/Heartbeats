from flask import Flask, session
from .config import Config
from .extensions import csrf
from .services import guest as guest_svc

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
    
    @app.context_processor
    def inject_current_user():
        # 사용자 상태 판정: authenticated > guest > anonymous 우선순위
        is_authenticated = "access_token" in session
        is_guest = guest_svc.is_guest()

        return {
            "current_user": {
                "is_authenticated": is_authenticated,
                "is_guest": is_guest,
                # 셋 중 하나로 명확히. 헤더 분기 시 status 값 하나로 판단 가능
                "status": (
                    "authenticated" if is_authenticated
                    else "guest" if is_guest
                    else "anonymous"
                ),
                "email": session.get("email"),
                "role": session.get("role"),
                # 게스트일 때만 의미 있는 값들
                "guest_message_count": guest_svc.get_message_count(),
                "guest_remaining": guest_svc.get_remaining_messages() if is_guest else None,
                "guest_limit": app.config["GUEST_MESSAGE_LIMIT"],
            }
        }
    
    return app