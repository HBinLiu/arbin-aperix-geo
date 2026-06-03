"""以项目配置启动 uvicorn：`python -m aperix_geo` 或安装后的 `aperix-geo-api`。"""

from __future__ import annotations


def main() -> None:
    import uvicorn

    from aperix_geo.config import get_settings
    from aperix_geo.utils.logging import configure

    configure()
    s = get_settings()
    # 热重载请直接用：uvicorn aperix_geo.main:app --reload --host … --port …
    uvicorn.run(
        "aperix_geo.main:app",
        host=s.api_host,
        port=s.api_port,
    )


if __name__ == "__main__":
    main()
