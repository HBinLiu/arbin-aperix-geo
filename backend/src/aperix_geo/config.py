"""Application configuration (pydantic-settings)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env 优先于 仓库根/.env（与当前工作目录无关）
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(_REPO_ROOT / ".env"),
            str(_BACKEND_DIR / ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://aperix:aperix@127.0.0.1:5432/aperix_geo"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    sampling_scheduler_tick_seconds: int = Field(default=900, ge=60, le=3600)
    # 重启后 queued/running 且无 worker 推进时，超过该秒数视为 stale 并重新入队
    sampling_stale_job_seconds: int = Field(default=90, ge=30, le=600)
    sampling_resume_debounce_seconds: int = Field(default=90, ge=30, le=600)
    # 开发调试入口：curl 手动触发采样（须同时设 SAMPLING_DEBUG_ENABLED 与 SAMPLING_DEBUG_SECRET）
    sampling_debug_enabled: bool = False
    sampling_debug_secret: str = ""

    jwt_secret_key: str = "change-me"
    jwt_encrypt_algorithm: str = "HS256"
    jwt_token_expire_minutes: int = 60 * 24 * 7

    # --- 大模型：默认推理 · DeepSeek（见 services/providers/）---
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_rate_limit_per_minute: int = 30

    # --- 大模型：腾讯元宝 / 混元（见 services/providers/）---
    yuanbao_api_key: str = ""
    yuanbao_base_url: str = "https://api.hunyuan.cloud.tencent.com/v1"
    yuanbao_model: str = "hunyuan-turbos-latest"
    yuanbao_rate_limit_per_minute: int = 30

    # --- 大模型：火山方舟 · 豆包（Dispatch 采样）---
    doubao_api_key: str = ""
    doubao_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    doubao_model: str = "doubao-seed-1-6-251015"
    doubao_rate_limit_per_minute: int = 30

    # --- 大模型：阿里云 · 通义千问（Dispatch 采样，见 services/sampling_llm.py）---
    qianwen_api_key: str = ""
    qianwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qianwen_model: str = "qwen-plus"
    qianwen_rate_limit_per_minute: int = 30

    # --- 大模型：月之暗面 · Kimi（Dispatch 采样）---
    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_model: str = "moonshot-v1-8k"
    kimi_rate_limit_per_minute: int = 30

    # --- 大模型：百度 · 文心一言 / 千帆 ERNIE（Dispatch 采样）---
    ernie_api_key: str = ""
    ernie_base_url: str = "https://qianfan.baidubce.com/v2"
    ernie_model: str = "ernie-4.0-8k"
    ernie_rate_limit_per_minute: int = 30

    # --- 竞品发现（.env：COMPETITOR_* + SEARXNG_BASE_URL）---
    searxng_base_url: str = ""
    competitor_pool_size: int = Field(default=30, ge=8, le=60)
    competitor_search_rounds: int = Field(default=5, ge=1, le=5)
    competitor_min_score: float = Field(default=6.0, ge=0.0, le=10.0)
    competitor_site_fetch_timeout_s: float = Field(default=5.0, ge=1.0, le=60.0)
    competitor_site_fetch_concurrency: int = Field(default=30, ge=1, le=100)
    competitor_target_fetch_timeout_s: float = Field(default=12.0, ge=1.0, le=120.0)
    competitor_target_crawl_timeout_s: float = Field(default=45.0, ge=5.0, le=120.0)
    competitor_target_crawl_max_chars: int = Field(default=14_000, ge=2000, le=50_000)
    competitor_cross_validate_batch_size: int = Field(default=15, ge=1, le=50)
    competitor_search_page_size: int = Field(default=50, ge=10, le=100)
    competitor_result_min: int = Field(default=3, ge=1, le=20)
    competitor_result_max: int = Field(default=5, ge=1, le=20)

    # uvicorn：见 `python -m aperix_geo` / 控制台命令 `aperix-geo-api`
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)

    # development / dev / local：手机号验证码随机生成并在 send-code 响应 dev_code 中回显
    env: str = Field(default="development", description="运行环境；生产部署请设为 production")

    # 验证码（Redis）；开发环境 send-code 回显 dev_code，生产不回显
    otp_code_ttl_seconds: int = 300
    otp_send_interval_seconds: int = 60
    otp_code_length: int = 6

    # 阿里云短信（国内验证码）；SMS_ALIYUN_ENABLED=true 且 channel=phone 且非开发环境时调用 SendSms
    sms_aliyun_enabled: bool = False
    sms_aliyun_access_key_id: str = ""
    sms_aliyun_access_key_secret: str = ""
    sms_aliyun_sign_name: str = ""
    sms_aliyun_template_code: str = ""
    sms_aliyun_template_param_code_key: str = Field(
        default="code",
        description="SendSms 模板 JSON 中验证码字段名，须与阿里云控制台模板变量一致",
    )
    sms_aliyun_endpoint: str = "dysmsapi.aliyuncs.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
