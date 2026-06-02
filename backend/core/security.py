# backend/core/security.py
"""
인증/인가 코어 (Authentication & Authorization)

이 모듈이 다루는 것:
- JWT 토큰 검증 (인증, authn)
- Authorization 헤더 → user 정보 추출 (FastAPI Depends 호환)
- role 기반 권한 검사 (인가, authz)

설계 원칙:
- cross-cutting concern은 라우터가 아니라 core에 둠
- 모든 보호된 엔드포인트는 Depends(get_current_user) 또는 Depends(require_role(...))를 통과
"""
import os
from fastapi import HTTPException, Header, Depends
from jose import jwt


# ──────────────────────────────────────────
# JWT 설정 (auth.py에서 이동)
# ──────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"


# ──────────────────────────────────────────
# 1. JWT 토큰 검증
# ──────────────────────────────────────────
def verify_access_token(token: str) -> dict:
    """
    JWT 토큰 문자열을 받아 payload(dict) 반환.
    
    payload 구조: {"user_id": str, "role": str, "exp": timestamp}
    
    실패 시 401 에러 raise.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="유효하지 않거나 만료된 토큰입니다.")


# ──────────────────────────────────────────
# 2. FastAPI Depends용 — Authorization 헤더에서 user 추출
# ──────────────────────────────────────────
def get_current_user(authorization: str = Header(...)) -> dict:
    """
    Authorization 헤더에서 'Bearer <token>'을 파싱해 검증 후 user payload 반환.
    
    사용:
        @router.get("/me")
        async def me(current_user: dict = Depends(get_current_user)):
            return {"user_id": current_user["user_id"]}
    """
    token = authorization.replace("Bearer ", "")
    return verify_access_token(token)


# ──────────────────────────────────────────
# 3. RBAC — role 화이트리스트 데코레이터 팩토리
# ──────────────────────────────────────────
def require_role(*allowed_roles: str):
    """
    특정 role만 접근 가능한 엔드포인트에 적용하는 의존성 팩토리.
    
    사용 예:
        @router.get("/admin/panel", dependencies=[Depends(require_role("admin"))])
        async def admin_panel():
            return {"ok": True}
        
        # 또는 current_user 객체가 필요하면:
        @router.get("/guardian/dashboard")
        async def dashboard(
            current_user: dict = Depends(require_role("guardian", "admin"))
        ):
            return {"user_id": current_user["user_id"]}
    
    Args:
        *allowed_roles: 허용할 role 문자열들 (가변 인자)
                        예: require_role("admin"), require_role("guardian", "admin")
    
    Returns:
        FastAPI Depends에 쓸 수 있는 dependency 함수.
        통과 시 current_user dict 반환, 실패 시 403 raise.
    """
    def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"권한이 없습니다. 필요한 role: {allowed_roles}"
            )
        return current_user
    return dependency