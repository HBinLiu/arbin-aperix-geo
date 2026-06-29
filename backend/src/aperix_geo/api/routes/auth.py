"""Authentication routes."""

import secrets
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.api.deps import CurrentUser, DbSession
from aperix_geo.config import get_settings
from aperix_geo.db.models import Tenant, User
from aperix_geo.schemas.auth import (
    BindEmailRequest,
    BindPhoneRequest,
    ChangePasswordRequest,
    LoginRequest,
    LoginWithOtpRequest,
    RegisterRequest,
    RegisterWithOtpRequest,
    SendBindCodeRequest,
    InviteTenantMemberRequest,
    SendInviteCodeRequest,
    SendCodeRequest,
    SendCodeResponse,
    TenantOut,
    TenantMemberOut,
    TenantMembersOut,
    TokenResponse,
    UserNotificationSettingsOut,
    UserNotificationSettingsUpdate,
    UserOut,
    UserWechatOut,
    WechatBindDevRequest,
)
from aperix_geo.security.jwt import create_access_token
from aperix_geo.security.password import hash_password, password_strength_error, verify_password
from aperix_geo.services.auth import otp as otp_svc
from aperix_geo.services.auth import tenant_members as member_svc
from aperix_geo.utils.contact import mask_phone_cn

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_to_out(user: User, *, phone: str | None = None) -> UserOut:
    return UserOut(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        phone=phone if phone is not None else user.phone,
        role=user.role,
        has_password=bool(user.password),
        created_at=user.created_at,
        wechat=UserWechatOut(
            nick_name=user.nick_name,
            open_id=user.open_id,
            union_id=user.union_id,
        ),
        notifications=UserNotificationSettingsOut(
            in_app=user.notify_in_app,
            email=user.notify_email,
            wechat=user.notify_wechat,
        ),
    )


def _users_by_email(db: Session, email_norm: str) -> list[User]:
    return list(db.execute(select(User).where(User.email == email_norm)).scalars().all())


def _user_by_phone(db: Session, phone_norm: str) -> User | None:
    return db.execute(select(User).where(User.phone == phone_norm)).scalar_one_or_none()


def _user_by_open_id(db: Session, open_id: str) -> User | None:
    return db.execute(select(User).where(User.open_id == open_id)).scalar_one_or_none()


def _email_taken_by_other(db: Session, email_norm: str, user_id) -> bool:
    row = db.execute(
        select(User.id).where(User.email == email_norm, User.id != user_id),
    ).scalar_one_or_none()
    return row is not None


def _phone_taken_by_other(db: Session, phone_norm: str, user_id) -> bool:
    existing = _user_by_phone(db, phone_norm)
    return existing is not None and existing.id != user_id


def _send_code_response(
    *,
    settings,
    channel: str,
    exposed: str | None,
) -> SendCodeResponse:
    if channel == "phone" and otp_svc.sms_use_dev_stub(settings):
        msg = "开发环境未发送短信；请使用响应中的验证码"
    elif channel == "phone" and settings.sms_aliyun_enabled:
        msg = "验证码已通过阿里云短信发送，请查收手机短信"
    elif channel == "email":
        msg = (
            "验证码已记录（邮箱通道仍为占位；开发环境见响应 dev_code，生产请查邮件）"
            if otp_svc.is_dev_environment(settings)
            else "验证码已记录（邮箱通道仍为占位，请查收邮件）"
        )
    else:
        msg = "验证码已记录（未开启阿里云短信时见服务端日志；可设置 SMS_ALIYUN_ENABLED=true）"
    return SendCodeResponse(ok=True, message=msg, dev_code=exposed)


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
    elif body.purpose == "invite":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请在账户设置成员页进行邀请",
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

    return _send_code_response(settings=settings, channel=body.channel, exposed=exposed)


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
    return _user_to_out(current, phone=mask_phone_cn(current.phone))


@router.post("/me/send-bind-code", response_model=SendCodeResponse)
def send_bind_code(body: SendBindCodeRequest, current: CurrentUser, db: DbSession) -> SendCodeResponse:
    settings = get_settings()
    try:
        if body.channel == "email":
            target_norm = otp_svc.normalize_email(body.target)
        else:
            target_norm = otp_svc.normalize_phone_cn(body.target)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    if body.channel == "email":
        if _email_taken_by_other(db, target_norm, current.id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已被其他账号使用")
    elif _phone_taken_by_other(db, target_norm, current.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该手机号已被其他账号使用")

    try:
        _, exposed = otp_svc.send_code(
            settings=settings,
            purpose="bind",
            channel=body.channel,
            target_raw=body.target,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e

    return _send_code_response(settings=settings, channel=body.channel, exposed=exposed)


@router.patch("/me/password", response_model=UserOut)
def change_my_password(body: ChangePasswordRequest, current: CurrentUser, db: DbSession) -> UserOut:
    user = db.get(User, current.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.password:
        if not body.current_password or not verify_password(body.current_password, user.password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确")

    if err := password_strength_error(body.new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    user.password = hash_password(body.new_password)
    db.commit()
    db.refresh(user)
    return _user_to_out(user, phone=mask_phone_cn(user.phone))


@router.patch("/me/phone", response_model=UserOut)
def bind_my_phone(body: BindPhoneRequest, current: CurrentUser, db: DbSession) -> UserOut:
    settings = get_settings()
    user = db.get(User, current.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not otp_svc.verify_code(
        settings=settings,
        purpose="bind",
        channel="phone",
        target_raw=body.target,
        code=body.code,
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码无效或已过期")

    try:
        target_norm = otp_svc.normalize_phone_cn(body.target)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    if _phone_taken_by_other(db, target_norm, user.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该手机号已被其他账号使用")

    user.phone = target_norm
    db.commit()
    db.refresh(user)
    return _user_to_out(user, phone=mask_phone_cn(user.phone))


@router.patch("/me/email", response_model=UserOut)
def bind_my_email(body: BindEmailRequest, current: CurrentUser, db: DbSession) -> UserOut:
    settings = get_settings()
    user = db.get(User, current.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not otp_svc.verify_code(
        settings=settings,
        purpose="bind",
        channel="email",
        target_raw=body.target,
        code=body.code,
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码无效或已过期")

    try:
        target_norm = otp_svc.normalize_email(body.target)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    if _email_taken_by_other(db, target_norm, user.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已被其他账号使用")

    user.email = target_norm
    if body.password:
        user.password = hash_password(body.password)
    db.commit()
    db.refresh(user)
    return _user_to_out(user, phone=mask_phone_cn(user.phone))


@router.post("/me/wechat/unbind", response_model=UserOut)
def unbind_my_wechat(current: CurrentUser, db: DbSession) -> UserOut:
    user = db.get(User, current.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.open_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="WeChat account is not bound")

    user.open_id = ""
    user.union_id = ""
    user.nick_name = ""
    user.notify_wechat = False
    db.commit()
    db.refresh(user)
    return _user_to_out(user, phone=mask_phone_cn(user.phone))


@router.post("/me/wechat/bind-dev", response_model=UserOut)
def bind_my_wechat_dev(body: WechatBindDevRequest, current: CurrentUser, db: DbSession) -> UserOut:
    settings = get_settings()
    if not otp_svc.is_dev_environment(settings):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WeChat binding is only available in development",
        )

    user = db.get(User, current.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    open_id = body.open_id.strip() or f"dev_{secrets.token_hex(8)}"
    union_id = body.union_id.strip()
    existing = _user_by_open_id(db, open_id)
    if existing and existing.id != user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该微信已被其他账号绑定")

    user.open_id = open_id
    user.union_id = union_id
    user.nick_name = body.nick_name.strip()
    db.commit()
    db.refresh(user)
    return _user_to_out(user, phone=mask_phone_cn(user.phone))


@router.patch("/me/notifications", response_model=UserOut)
def update_my_notifications(
    body: UserNotificationSettingsUpdate,
    current: CurrentUser,
    db: DbSession,
) -> UserOut:
    user = db.get(User, current.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.in_app is not None:
        user.notify_in_app = body.in_app
    if body.email is not None:
        user.notify_email = body.email
    if body.wechat is not None:
        if body.wechat and not user.open_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="WeChat account is not bound",
            )
        user.notify_wechat = body.wechat

    db.commit()
    db.refresh(user)
    return _user_to_out(user, phone=mask_phone_cn(user.phone))


@router.get("/tenant/members", response_model=TenantMembersOut)
def list_tenant_members(current: CurrentUser, db: DbSession) -> TenantMembersOut:
    items = member_svc.list_tenant_members(db, current.tenant_id)
    return TenantMembersOut(items=[TenantMemberOut.model_validate(item) for item in items])


@router.post("/tenant/members/send-invite-code", response_model=SendCodeResponse)
def send_tenant_invite_code(
    body: SendInviteCodeRequest,
    current: CurrentUser,
    db: DbSession,
) -> SendCodeResponse:
    member_svc.require_tenant_admin(current)
    settings = get_settings()
    phone_norm = member_svc.validate_invite_phone(db, tenant_id=current.tenant_id, phone_raw=body.phone)

    try:
        _, exposed = otp_svc.send_code(
            settings=settings,
            purpose="invite",
            channel="phone",
            target_raw=phone_norm,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e

    return _send_code_response(settings=settings, channel="phone", exposed=exposed)


@router.post("/tenant/members/invite", response_model=TenantMemberOut, status_code=status.HTTP_201_CREATED)
def invite_tenant_member(
    body: InviteTenantMemberRequest,
    current: CurrentUser,
    db: DbSession,
) -> TenantMemberOut:
    settings = get_settings()
    user = member_svc.invite_tenant_member(
        db,
        tenant_id=current.tenant_id,
        inviter=current,
        phone_raw=body.phone,
        code=body.code,
        role=body.role,
        settings=settings,
    )
    return TenantMemberOut(
        id=user.id,
        phone=mask_phone_cn(user.phone),
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.delete("/tenant/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_tenant_member(user_id: uuid.UUID, current: CurrentUser, db: DbSession) -> None:
    member_svc.remove_tenant_member(
        db,
        tenant_id=current.tenant_id,
        actor=current,
        member_id=user_id,
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
