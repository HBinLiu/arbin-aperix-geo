"""Authentication routes."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.api.deps import CurrentUser, DbSession
from aperix_geo.config import get_settings
from aperix_geo.db.models import Tenant, User
from aperix_geo.schemas.auth import (
    LoginRequest,
    LoginWithOtpRequest,
    RegisterRequest,
    RegisterWithOtpRequest,
    SendCodeRequest,
    SendCodeResponse,
    TenantOut,
    TokenResponse,
    UserOut,
)
from aperix_geo.security.jwt import create_access_token
from aperix_geo.security.password import hash_password, verify_password
from aperix_geo.services.auth import otp as otp_svc
from aperix_geo.utils.contact import mask_phone_cn

router = APIRouter(prefix="/auth", tags=["auth"])


def _users_by_email(db: Session, email_norm: str) -> list[User]:
    return list(db.execute(select(User).where(User.email == email_norm)).scalars().all())


def _user_by_phone(db: Session, phone_norm: str) -> User | None:
    return db.execute(select(User).where(User.phone == phone_norm)).scalar_one_or_none()


def _contact_taken_register(db: Session, channel: str, target_norm: str) -> bool:
    if channel == "email":
        return len(_users_by_email(db, target_norm)) > 0
    return _user_by_phone(db, target_norm) is not None


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: DbSession) -> TokenResponse:
    tenant = Tenant(name=body.tenant_name.strip())
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=str(body.email).lower().strip(),
        password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    token = create_access_token(user_id=user.id, tenant_id=tenant.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbSession) -> TokenResponse:
    email_norm = str(body.email).lower().strip()
    q = select(User).where(User.email == email_norm)
    if body.tenant_id is not None:
        q = q.where(User.tenant_id == body.tenant_id)
    users = list(db.execute(q).scalars().all())
    if not users:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if len(users) > 1 and body.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple accounts for this email; pass tenant_id",
        )
    user = users[0]
    if not user.password or not verify_password(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user_id=user.id, tenant_id=user.tenant_id)
    return TokenResponse(access_token=token)


@router.post("/send-code", response_model=SendCodeResponse)
def send_code(body: SendCodeRequest, db: DbSession) -> SendCodeResponse:
    settings = get_settings()
    try:
        if body.channel == "email":
            target_norm = otp_svc.normalize_email(body.target)
        else:
            target_norm = otp_svc.normalize_phone_cn(body.target)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    if body.purpose == "register":
        if body.channel == "phone":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号无需单独注册，请在登录页使用短信验证码登录，首次验证通过将自动开通账号",
            )
        if _contact_taken_register(db, body.channel, target_norm):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该邮箱已注册",
            )
    else:
        # 邮箱登录仅支持密码，不提供「登录验证码」
        if body.channel == "email":
            return SendCodeResponse(
                ok=True,
                message="邮箱请使用密码登录；若尚未注册请先完成邮箱注册（验证码+密码）",
                dev_code=None,
            )
        # 手机号登录：未注册也发验证码，以便「验证即注册」

    try:
        _, exposed = otp_svc.send_code(
            settings=settings,
            purpose=body.purpose,
            channel=body.channel,
            target_raw=body.target,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e

    if body.channel == "phone" and otp_svc.sms_use_dev_stub(settings):
        msg = "开发环境未发送短信；请使用响应中的验证码"
    elif body.channel == "phone" and settings.sms_aliyun_enabled:
        msg = "验证码已通过阿里云短信发送，请查收手机短信"
    elif body.channel == "email":
        msg = (
            "验证码已记录（邮箱通道仍为占位；开发环境见响应 dev_code，生产请查邮件）"
            if otp_svc.is_dev_environment(settings)
            else "验证码已记录（邮箱通道仍为占位，请查收邮件）"
        )
    else:
        msg = "验证码已记录（未开启阿里云短信时见服务端日志；可设置 SMS_ALIYUN_ENABLED=true）"
    return SendCodeResponse(ok=True, message=msg, dev_code=exposed)


@router.post("/register-with-otp", response_model=TokenResponse)
def register_with_otp(body: RegisterWithOtpRequest, db: DbSession) -> TokenResponse:
    settings = get_settings()
    if not otp_svc.verify_code(
        settings=settings,
        purpose="register",
        channel="email",
        target_raw=body.target,
        code=body.code,
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码无效或已过期")

    try:
        target_norm = otp_svc.normalize_email(body.target)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    if _contact_taken_register(db, "email", target_norm):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已注册")

    tenant = Tenant(name=body.tenant_name.strip())
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=target_norm,
        phone="",
        password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user_id=user.id, tenant_id=tenant.id)
    return TokenResponse(access_token=token)


@router.post("/login-with-otp", response_model=TokenResponse)
def login_with_otp(body: LoginWithOtpRequest, db: DbSession) -> TokenResponse:
    settings = get_settings()
    if not otp_svc.verify_code(
        settings=settings,
        purpose="login",
        channel="phone",
        target_raw=body.target,
        code=body.code,
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码无效或已过期")

    try:
        target_norm = otp_svc.normalize_phone_cn(body.target)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    user = _user_by_phone(db, target_norm)
    if user:
        token = create_access_token(user_id=user.id, tenant_id=user.tenant_id)
        return TokenResponse(access_token=token)

    tenant_name = (body.tenant_name or "").strip() or f"手机用户_{target_norm[-4:]}"
    tenant = Tenant(name=tenant_name)
    db.add(tenant)
    db.flush()
    new_user = User(tenant_id=tenant.id, email="", phone=target_norm, password="")
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    token = create_access_token(user_id=new_user.id, tenant_id=tenant.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current: CurrentUser) -> UserOut:
    return UserOut(
        id=current.id,
        tenant_id=current.tenant_id,
        email=current.email,
        phone=mask_phone_cn(current.phone),
    )


@router.get("/tenant", response_model=TenantOut)
def current_tenant(
    current: CurrentUser,
    db: DbSession,
) -> Tenant:
    tenant = db.get(Tenant, current.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
