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
    # Celery 单条 response 采样重试：指数退避 base/cap 与最大次数
    sampling_retry_base_s: int = Field(default=20, ge=1, le=300)
    sampling_retry_cap_s: int = Field(default=120, ge=1, le=600)
    sampling_retry_max: int = Field(default=8, ge=0, le=20)
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
    deepseek_web_search_enabled: bool = True
    deepseek_chat_timeout_s: float = Field(default=120.0, ge=10.0, le=600.0)

    # --- 采样 · SearXNG 联网（DeepSeek / Kimi 等）---
    sampling_searxng_max_results: int = Field(default=8, ge=1, le=28)

    # --- 页面抓取（httpx → Crawl4AI，全局共用）---
    page_crawl_fetch_timeout_s: float = Field(default=8.0, ge=1.0, le=120.0)
    page_crawl_crawl_timeout_s: float = Field(default=45.0, ge=5.0, le=120.0)
    page_crawl_max_chars: int = Field(default=120_000, ge=5000, le=500_000)
    page_crawl_seo_max_chars: int = Field(default=64_000, ge=5000, le=500_000)
    page_crawl_fallback_enabled: bool = True
    page_crawl_seo_fallback_enabled: bool = False
    page_crawl_concurrency: int = Field(default=10, ge=1, le=100)
    page_crawl_crawl4ai_concurrency: int = Field(default=5, ge=1, le=20)
    page_crawl_cache_ttl_s: int = Field(default=3600, ge=0, le=86_400)
    page_crawl_negative_cache_ttl_s: int = Field(default=300, ge=0, le=3600)
    page_crawl_dns_cache_ttl_s: int = Field(default=3600, ge=0, le=86_400)

    # --- 引用来源 · Page GEO / ABSA 分析（不含抓取）---
    citation_text_snippet_chars: int = Field(default=4_000, ge=500, le=50_000)
    citation_page_geo_llm_enabled: bool = True
    citation_page_geo_batch_size: int = Field(default=8, ge=1, le=20)
    citation_page_geo_cache_ttl_s: int = Field(default=3600, ge=0, le=86_400)
    citation_response_absa_cache_ttl_s: int = Field(default=3600, ge=0, le=86_400)

    # --- 大模型：腾讯元宝 / 混元（见 services/providers/）---
    yuanbao_api_key: str = ""
    yuanbao_base_url: str = "https://api.hunyuan.cloud.tencent.com/v1"
    yuanbao_model: str = "hunyuan-turbos-latest"
    yuanbao_rate_limit_per_minute: int = 30
    yuanbao_web_search_enabled: bool = True
    yuanbao_chat_timeout_s: float = Field(default=120.0, ge=10.0, le=600.0)

    # --- 大模型：火山方舟 · 豆包（Dispatch 采样）---
    doubao_api_key: str = ""
    doubao_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    doubao_model: str = "doubao-seed-1-6-251015"
    doubao_rate_limit_per_minute: int = 30
    doubao_web_search_enabled: bool = True
    doubao_responses_timeout_s: float = Field(default=120.0, ge=10.0, le=600.0)

    # --- 大模型：阿里云 · 通义千问（DashScope Generation API 采样）---
    qianwen_api_key: str = ""
    qianwen_base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    qianwen_model: str = "qwen-plus"
    qianwen_rate_limit_per_minute: int = 30
    qianwen_web_search_enabled: bool = True
    qianwen_generation_timeout_s: float = Field(default=120.0, ge=10.0, le=600.0)

    # --- 大模型：月之暗面 · Kimi（Dispatch 采样）---
    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_model: str = "moonshot-v1-8k"
    kimi_rate_limit_per_minute: int = 30
    kimi_web_search_enabled: bool = True
    kimi_chat_timeout_s: float = Field(default=120.0, ge=10.0, le=600.0)

    # --- 大模型：百度 · 文心一言 / 千帆 ERNIE（Dispatch 采样）---
    ernie_api_key: str = ""
    ernie_base_url: str = "https://qianfan.baidubce.com/v2"
    ernie_model: str = "ernie-4.0-8k"
    ernie_rate_limit_per_minute: int = 30
    ernie_web_search_enabled: bool = True
    ernie_chat_timeout_s: float = Field(default=120.0, ge=10.0, le=600.0)

    # --- 竞品发现（.env：COMPETITOR_* + SEARXNG_BASE_URL）---
    searxng_base_url: str = ""
    # 交叉验算 head 走 PAGE_CRAWL_SEO_*（轻量 httpx）；池越大召回越好，与 PAGE_CRAWL_CONCURRENCY 配合
    competitor_pool_size: int = Field(default=40, ge=8, le=60)
    competitor_search_rounds: int = Field(default=3, ge=1, le=5)
    competitor_cross_validate_pass_score: float = Field(default=6.0, ge=0.0, le=10.0)
    # head 已预抓取，瓶颈在 LLM；略大批次减少往返
    competitor_cross_validate_batch_size: int = Field(default=20, ge=1, le=50)
    competitor_search_page_size: int = Field(default=50, ge=10, le=100)
    competitor_result_min: int = Field(default=3, ge=1, le=20)
    competitor_result_max: int = Field(default=5, ge=1, le=20)

    # 设置向导 Redis 会话 TTL（秒）；0=永不过期。finalize 成功仍会主动删除。
    setup_session_ttl_s: int = Field(default=86_400, ge=0, le=604_800)

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

    # favicon 本地持久化目录（按域名子目录保存全部成功抓取的图标）
    favicon_storage_dir: str = Field(default=str(_BACKEND_DIR / "data" / "favicons"))
    favicon_warm_concurrency: int = Field(default=6, ge=1, le=32)


@lru_cache
def get_settings() -> Settings:
    return Settings()
