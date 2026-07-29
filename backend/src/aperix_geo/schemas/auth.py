"""Shared Pydantic schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SendCodeRequest(BaseModel):
    purpose: Literal["login", "bind", "invite"]
    channel: Literal["email", "phone"]
    target: str = Field(..., min_length=3, max_length=320)


class SendInviteCodeRequest(BaseModel):
    phone: str = Field(..., min_length=3, max_length=320)


class InviteTenantMemberRequest(BaseModel):
    phone: str = Field(..., min_length=3, max_length=320)
    code: str = Field(..., min_length=4, max_length=16)
    role: Literal["member", "readonly"] = "member"


class TenantMemberOut(BaseModel):
    id: UUID
    phone: str
    role: str
    is_active: bool
    created_at: datetime


class TenantMembersOut(BaseModel):
    items: list[TenantMemberOut]


class SendBindCodeRequest(BaseModel):
    channel: Literal["email", "phone"]
    target: str = Field(..., min_length=3, max_length=320)


class BindPhoneRequest(BaseModel):
    target: str = Field(..., min_length=3, max_length=320)
    code: str = Field(..., min_length=4, max_length=16)


class BindEmailRequest(BaseModel):
    target: str = Field(..., min_length=3, max_length=320)
    code: str = Field(..., min_length=4, max_length=16)


class WechatBindDevRequest(BaseModel):
    nick_name: str = Field(..., min_length=1, max_length=128)
    open_id: str = Field(default="", max_length=128)
    union_id: str = Field(default="", max_length=128)


class WechatBindQrOut(BaseModel):
    ticket_id: str
    qrcode_url: str
    expires_in: int


class WechatBindQrStatusOut(BaseModel):
    ticket_id: str
    status: Literal["pending", "bound", "failed", "expired"]
    error: str = ""


class SendCodeResponse(BaseModel):
    ok: bool = True
    message: str = Field(
        default="验证码已发送",
        description="提示文案",
    )
    dev_code: str | None = Field(
        default=None,
        description="仅开发环境（ENV=development|dev|local）回显验证码；生产恒为 null",
    )


class LoginWithOtpRequest(BaseModel):
    """邮箱或手机号验证码登录；若未注册则本次验证通过后自动创建租户与用户。"""

    channel: Literal["email", "phone"]
    target: str = Field(..., min_length=3, max_length=320)
    code: str = Field(..., min_length=4, max_length=16)
    tenant_name: str | None = Field(
        default=None,
        max_length=255,
        description="首次登录自动注册时的工作区名称；已注册用户可忽略",
    )


class UserWechatOut(BaseModel):
    nick_name: str = ""
    open_id: str = ""
    union_id: str = ""


class UserNotificationSettingsOut(BaseModel):
    in_app: bool = True
    email: bool = True
    wechat: bool = False


class UserNotificationSettingsUpdate(BaseModel):
    in_app: bool | None = None
    email: bool | None = None
    wechat: bool | None = None


class UserOut(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    phone: str
    role: str = "admin"
    created_at: datetime
    wechat: UserWechatOut
    notifications: UserNotificationSettingsOut

    model_config = {"from_attributes": True}


class TenantOut(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
