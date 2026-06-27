"""Shared Pydantic schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    tenant_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: UUID | None = None


class SendCodeRequest(BaseModel):
    purpose: Literal["register", "login", "bind"]
    channel: Literal["email", "phone"]
    target: str = Field(..., min_length=3, max_length=320)


class SendBindCodeRequest(BaseModel):
    channel: Literal["email", "phone"]
    target: str = Field(..., min_length=3, max_length=320)


class ChangePasswordRequest(BaseModel):
    current_password: str | None = Field(default=None, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class BindPhoneRequest(BaseModel):
    target: str = Field(..., min_length=3, max_length=320)
    code: str = Field(..., min_length=4, max_length=16)


class BindEmailRequest(BaseModel):
    target: str = Field(..., min_length=3, max_length=320)
    code: str = Field(..., min_length=4, max_length=16)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class WechatBindDevRequest(BaseModel):
    nick_name: str = Field(..., min_length=1, max_length=128)
    open_id: str = Field(default="", max_length=128)
    union_id: str = Field(default="", max_length=128)


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


class RegisterWithOtpRequest(BaseModel):
    """仅邮箱：邮箱验证码 + 登录密码完成注册（手机号请走登录页短信验证码自动注册）。"""

    tenant_name: str = Field(..., min_length=1, max_length=255)
    channel: Literal["email"] = "email"
    target: str = Field(..., min_length=3, max_length=320)
    code: str = Field(..., min_length=4, max_length=16)
    password: str = Field(..., min_length=8, max_length=128)


class LoginWithOtpRequest(BaseModel):
    """仅手机号：验证码登录；若号码未注册则本次验证通过后自动创建租户与用户。"""

    channel: Literal["phone"] = "phone"
    target: str = Field(..., min_length=3, max_length=320)
    code: str = Field(..., min_length=4, max_length=16)
    tenant_name: str | None = Field(
        default=None,
        max_length=255,
        description="首次短信登录自动注册时的工作区名称；已注册用户可忽略",
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
    has_password: bool = False
    created_at: datetime
    wechat: UserWechatOut
    notifications: UserNotificationSettingsOut

    model_config = {"from_attributes": True}


class TenantOut(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
