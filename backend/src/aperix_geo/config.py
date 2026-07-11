"""Application configuration (pydantic-settings)."""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
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

    # 每日定时采样（北京时间）：从 sampling_daily_hour 起，在 window 分钟内按 subject 分散；默认 02:00–05:00
    sampling_daily_hour: int = Field(default=2, ge=0, le=23)
    sampling_daily_window_minutes: int = Field(default=180, ge=15, le=360)
    # Celery Beat 在每日窗口内的扫描间隔（分钟）；subject 仍按 id hash 在窗口内错开 slot
    sampling_scheduler_interval_minutes: int = Field(default=15, ge=5, le=60)
    sampling_scheduler_max_enqueue_per_run: int = Field(default=50, ge=1, le=500)
    # 重启后 queued/running 且无 worker 推进时，超过该秒数视为 stale 并重新入队
    sampling_stale_job_seconds: int = Field(default=90, ge=30, le=600)
    sampling_resume_debounce_seconds: int = Field(default=90, ge=30, le=600)
    sampling_fill_debounce_seconds: int = Field(default=1, ge=1, le=30)
    sampling_finalize_debounce_seconds: int = Field(default=5, ge=1, le=120)
    # Celery 单条 response 采样重试：指数退避 base/cap 与最大次数
    sampling_retry_base_s: int = Field(default=20, ge=1, le=300)
    sampling_retry_cap_s: int = Field(default=120, ge=1, le=600)
    sampling_retry_max: int = Field(default=8, ge=0, le=20)
    sampling_db_retry_max: int = Field(default=3, ge=1, le=10)
    sampling_llm_result_cache_ttl_s: int = Field(default=3600, ge=60, le=86_400)
    sampling_response_claim_ttl_s: int = Field(default=2700, ge=300, le=7200)
    # 每个 sampling job 各 phase 同时进行中的 response 数上限
    sampling_max_inflight: int = Field(
        default=10,
        ge=1,
        le=500,
        validation_alias=AliasChoices("sampling_max_inflight", "sampling_chord_batch_size"),
    )
    # 各平台同时进行中的 LLM HTTP 请求上限（与每分钟 quota 互补）
    sampling_llm_max_inflight: int = Field(default=15, ge=1, le=256)
    sampling_llm_inflight_ttl_s: int = Field(default=600, ge=60, le=7200)
    # Celery 队列：编排 / LLM / Parse 分池（分机部署时各机器只消费对应 -Q）
    celery_default_queue: str = "aperix"
    celery_sampling_llm_queue: str = "sampling.llm"
    celery_sampling_crawl_queue: str = "sampling.crawl"
    celery_sampling_parse_queue: str = "sampling.parse"
    celery_orch_worker_concurrency: int = Field(default=4, ge=1, le=64)
    celery_llm_worker_concurrency: int = Field(default=16, ge=1, le=128)
    celery_crawl_worker_concurrency: int = Field(default=16, ge=1, le=128)
    celery_parse_worker_concurrency: int = Field(default=16, ge=1, le=128)
    celery_redis_socket_timeout_s: float = Field(default=30.0, ge=5.0, le=120.0)
    celery_redis_connect_timeout_s: float = Field(default=10.0, ge=1.0, le=60.0)

    jwt_secret_key: str = "change-me"
    jwt_encrypt_algorithm: str = "HS256"
    jwt_token_expire_minutes: int = 60 * 24 * 7

    # 支付 webhook（空则拒绝外部回调；开发可设固定 secret）
    billing_pay_webhook_secret: str = ""

    # --- 微信支付 V3（Native 扫码）---
    wechat_pay_mch_id: str = ""
    wechat_pay_app_id: str = ""
    wechat_pay_api_v3_key: str = ""
    wechat_pay_mch_cert_serial_no: str = ""
    wechat_pay_private_key: str = ""
    wechat_pay_private_key_path: str = ""
    wechat_pay_platform_cert_pem: str = ""
    wechat_pay_platform_cert_path: str = ""
    wechat_pay_platform_cert_serial: str = ""
    wechat_pay_notify_url: str = ""
    wechat_pay_timeout_s: float = Field(default=15.0, ge=5.0, le=60.0)

    # --- 大模型：默认推理 · DeepSeek（见 services/providers/）---
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_rate_limit_per_minute: int = 30
    deepseek_web_search_enabled: bool = True
    # 原生联网走 Anthropic Messages API；留空则从 DEEPSEEK_BASE_URL 推导
    deepseek_anthropic_base_url: str = ""
    # Anthropic web_search tool 版本（DeepSeek 当前支持 20250305 / 20260209）
    deepseek_web_search_tool_type: str = "web_search_20250305"
    deepseek_web_search_max_uses: int = Field(default=5, ge=1, le=20)
    deepseek_chat_timeout_s: float = Field(default=120.0, ge=10.0, le=600.0)

    # --- DNS（dnspython · 爬虫预检 / 品牌推断等）---
    dns_timeout_s: float = Field(default=1.0, ge=0.5, le=30.0)
    dns_cache_ttl_s: int = Field(default=3600, ge=0, le=86_400)

    # --- 页面抓取（httpx → Crawl4AI，全局共用）---
    page_crawl_fetch_timeout_s: float = Field(default=3.0, ge=1.0, le=120.0)
    page_crawl_crawl_timeout_s: float = Field(default=10.0, ge=5.0, le=120.0)
    page_crawl_max_chars: int = Field(default=32_000, ge=5000, le=500_000)
    page_crawl_seo_max_chars: int = Field(default=64_000, ge=5000, le=500_000)
    page_crawl_fallback_enabled: bool = True
    page_crawl_seo_fallback_enabled: bool = False
    page_crawl_concurrency: int = Field(default=5, ge=1, le=100)
    page_crawl_crawl4ai_concurrency: int = Field(default=5, ge=1, le=20)
    page_crawl_cache_ttl_s: int = Field(default=86_400, ge=0, le=86_400)
    page_crawl_negative_cache_ttl_s: int = Field(default=3600, ge=0, le=3600)
    page_crawl_rate_limit_negative_ttl_s: int = Field(default=60, ge=0, le=600)
    page_crawl_domain_limit_per_minute: int = Field(default=30, ge=0, le=1000)
    page_crawl_domain_max_inflight: int = Field(default=3, ge=0, le=100)
    page_crawl_domain_limit_wait_s: float = Field(default=15.0, ge=0.0, le=120.0)
    page_crawl_domain_inflight_ttl_s: int = Field(default=600, ge=60, le=7200)

    # --- 引用来源 · 抓取与 ABSA ---
    citation_text_snippet_chars: int = Field(default=2_000, ge=500, le=50_000)
    citation_response_absa_cache_ttl_s: int = Field(default=86_400, ge=0, le=86_400)
    citation_favicon_inline: bool = False

    # --- 目录接口 Redis 缓存（entities、subject topics）---
    catalog_cache_ttl_s: int = Field(default=86_400, ge=0, le=604_800)

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

    # --- 向量 Embedding（品牌知识库索引 · OpenAI 兼容 /embeddings）---
    embedding_api_key: str = ""
    embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_model: str = "text-embedding-v4"
    embedding_dimensions: int = Field(default=1024, ge=64, le=4096)
    embedding_batch_size: int = Field(default=25, ge=1, le=100)
    embedding_timeout_s: float = Field(default=60.0, ge=5.0, le=300.0)
    knowledge_chunk_size: int = Field(default=500, ge=100, le=2000)
    knowledge_chunk_overlap: int = Field(default=64, ge=0, le=500)
    knowledge_chunk_max_per_source: int = Field(default=500, ge=1, le=5000)

    # --- 大模型：月之暗面 · Kimi（Dispatch 采样）---
    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_model: str = "moonshot-v1-8k"
    kimi_rate_limit_per_minute: int = 30
    kimi_web_search_enabled: bool = True
    kimi_web_search_max_uses: int = Field(default=5, ge=1, le=20)
    kimi_chat_timeout_s: float = Field(default=180.0, ge=10.0, le=600.0)
    # Kimi 推理类模型（如 kimi-k2）仅允许 temperature=1
    kimi_temperature: float = Field(default=1.0, ge=0.0, le=2.0)

    # --- 大模型：百度 · 文心一言 / 千帆 ERNIE（Dispatch 采样）---
    ernie_api_key: str = ""
    ernie_base_url: str = "https://qianfan.baidubce.com/v2"
    ernie_model: str = "ernie-4.0-8k"
    ernie_rate_limit_per_minute: int = 30
    ernie_web_search_enabled: bool = True
    ernie_chat_timeout_s: float = Field(default=120.0, ge=10.0, le=600.0)

    # --- 竞品发现（.env：COMPETITOR_* + DOUBAO_*）---
    searxng_base_url: str = ""
    searxng_timeout_s: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
        validation_alias=AliasChoices("searxng_timeout_s", "sampling_searxng_timeout_s"),
    )
    # 交叉验算 head 走 PAGE_CRAWL_SEO_*（轻量 httpx）；池越大召回越好，与 PAGE_CRAWL_CONCURRENCY 配合
    competitor_pool_size: int = Field(default=40, ge=8, le=60)
    competitor_search_rounds: int = Field(default=3, ge=1, le=5)
    competitor_cross_validate_pass_score: float = Field(default=6.0, ge=0.0, le=10.0)
    # head 已预抓取，瓶颈在 LLM；略大批次减少往返
    competitor_cross_validate_batch_size: int = Field(default=20, ge=1, le=50)
    competitor_result_min: int = Field(default=3, ge=1, le=20)
    competitor_result_max: int = Field(default=5, ge=1, le=20)

    # 设置向导 Redis 会话 TTL（秒）；0=永不过期。finalize 成功仍会主动删除。
    setup_session_ttl_s: int = Field(default=86_400, ge=0, le=604_800)
    setup_upload_dir: str = Field(
        default="data/setup_uploads",
        description="品牌 Setup 会话期上传文件目录",
    )
    knowledge_upload_dir: str = Field(
        default="data/knowledge_uploads",
        description="finalize 后知识库 upload 持久化目录",
    )

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

    # --- AI 平台欠费/余额告警（运维通知，非租户 OTP）---
    provider_alert_enabled: bool = False
    provider_alert_env_label: str = ""
    provider_alert_channels: str = "email"
    provider_alert_email_to: str = ""
    provider_alert_sms_phones: str = ""
    provider_alert_cooldown_seconds: int = Field(default=21_600, ge=60, le=604_800)
    provider_alert_min_fails: int = Field(default=3, ge=1, le=100)
    provider_alert_sms_template_code: str = ""

    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_from_name: str = "Aperix Alerts"
    smtp_use_tls: bool = True

    # favicon 本地持久化目录（按域名子目录保存全部成功抓取的图标）
    favicon_storage_dir: str = Field(default=str(_BACKEND_DIR / "data" / "favicons"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
