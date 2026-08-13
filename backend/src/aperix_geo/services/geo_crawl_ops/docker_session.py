"""Shared GEO crawl-ops remote desktop sessions (noVNC + Chromium).

Used by Doubao account tickets today; DeepSeek / Qianwen / … can reuse the same
image and spawn helpers with a different ``platform`` / ``start_url``.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aperix_geo.config import Settings, get_settings

logger = logging.getLogger(__name__)

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_.-]+")


@dataclass(frozen=True)
class OpsSessionSpawn:
    container_id: str
    login_url: str
    host_port: int
    name: str


class GeoCrawlOpsDockerError(RuntimeError):
    """Docker CLI / spawn failure for geo-crawl-ops sessions."""


def geo_crawl_ops_ready(settings: Settings | None = None) -> bool:
    """True when noVNC base URL + Docker image are configured (shared across platforms)."""
    settings = settings or get_settings()
    return bool(
        (settings.geo_crawl_ops_novnc_base_url or "").strip()
        and (settings.geo_crawl_ops_docker_image or "").strip()
    )


def docker_cli_available() -> bool:
    return shutil.which("docker") is not None


def _run_docker(args: list[str], *, timeout_s: float = 60.0) -> str:
    cmd = ["docker", *args]
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except FileNotFoundError as exc:
        raise GeoCrawlOpsDockerError("docker CLI not found on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise GeoCrawlOpsDockerError(f"docker timed out: {' '.join(cmd)}") from exc
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise GeoCrawlOpsDockerError(err or f"docker failed ({proc.returncode}): {' '.join(cmd)}")
    return (proc.stdout or "").strip()


def _container_name(ticket_token: str, *, platform: str) -> str:
    slug = _SAFE_NAME.sub("-", (platform or "web").strip().lower())[:20] or "web"
    tok = _SAFE_NAME.sub("", ticket_token)[:12] or "ticket"
    return f"geo-crawl-ops-{slug}-{tok}"[:63]


def build_login_url(base_url: str, *, ticket_token: str, host_port: int = 0) -> str:
    """Support templates ``{ticket}`` / ``{port}``; default ``{base}/?ticket=…``."""
    base = (base_url or "").strip().rstrip("/")
    if not base:
        return ""
    if "{ticket}" in base or "{port}" in base:
        return base.format(ticket=ticket_token, port=host_port or "")
    return f"{base}/?ticket={ticket_token}"


def build_complete_callback_url(callback_base_url: str) -> str:
    """Map API base (or full path) to Doubao complete-by-token endpoint."""
    base = (callback_base_url or "").strip().rstrip("/")
    if not base:
        return ""
    if base.endswith("/tickets/complete-by-token"):
        return base
    return f"{base}/api/v1/ops/geo-crawl/tickets/complete-by-token"


def rewrite_callback_url_for_container(complete_url: str) -> tuple[str, bool]:
    """Rewrite loopback callback hosts so the ops container can reach the API host.

    ``127.0.0.1`` / ``localhost`` inside the container is the container itself, so
    POSTs never hit the API → cookies/ticket stay stale while ``--rm`` still
    removes the session after TTL/exit.

    Returns ``(url, needs_host_gateway)``. When ``needs_host_gateway`` is True,
    spawn must pass ``--add-host=host.docker.internal:host-gateway``.

    Note: the API process must still accept connections from the Docker bridge
    (listen on ``0.0.0.0``, or use a public/nginx URL / shared Docker network).
    """
    url = (complete_url or "").strip()
    if not url:
        return "", False
    rewritten = re.sub(
        r"^(https?://)(?:127\.0\.0\.1|localhost)(?=[:/]|$)",
        r"\1host.docker.internal",
        url,
        count=1,
        flags=re.IGNORECASE,
    )
    if rewritten != url:
        logger.warning(
            "geo-crawl-ops callback rewritten for container: %s → %s "
            "(set GEO_CRAWL_OPS_CALLBACK_BASE_URL to a container-reachable host "
            "or public API URL to avoid this)",
            url,
            rewritten,
        )
        return rewritten, True
    return url, False


def spawn_ops_session(
    *,
    ticket_token: str,
    platform: str,
    start_url: str,
    ttl_min: int,
    storage_state: dict[str, Any] | None = None,
    ops_reason: str = "login_expired",
    settings: Settings | None = None,
) -> OpsSessionSpawn:
    """Start a geo-crawl-ops container for human login / captcha.

    Requires Docker CLI on the API/worker host. Image must expose noVNC on 6080
    and honor env ``GEO_CRAWL_OPS_START_URL`` / ``GEO_CRAWL_OPS_TICKET_TOKEN`` /
    ``GEO_CRAWL_OPS_PLATFORM`` / ``GEO_CRAWL_OPS_REASON``.
    """
    settings = settings or get_settings()
    if not geo_crawl_ops_ready(settings):
        raise GeoCrawlOpsDockerError(
            "GEO_CRAWL_OPS_NOVNC_BASE_URL / GEO_CRAWL_OPS_DOCKER_IMAGE not configured"
        )
    if not docker_cli_available():
        raise GeoCrawlOpsDockerError("docker CLI not available")

    reason = (ops_reason or "login_expired").strip().lower()
    if reason not in ("login_expired", "captcha"):
        reason = "login_expired"

    image = settings.geo_crawl_ops_docker_image.strip()
    name = _container_name(ticket_token, platform=platform)
    try:
        _run_docker(["rm", "-f", name], timeout_s=30.0)
    except GeoCrawlOpsDockerError:
        pass

    args = [
        "create",
        "--rm",
        "--name",
        name,
        "--label",
        "aperix.geo_crawl_ops=1",
        "--label",
        f"aperix.geo_crawl_ops.platform={platform}",
        "--label",
        f"aperix.geo_crawl_ops.ticket={ticket_token}",
        "--label",
        f"aperix.geo_crawl_ops.reason={reason}",
        "-p",
        "127.0.0.1::6080",
        "-e",
        f"GEO_CRAWL_OPS_TICKET_TOKEN={ticket_token}",
        "-e",
        f"GEO_CRAWL_OPS_PLATFORM={platform}",
        "-e",
        f"GEO_CRAWL_OPS_START_URL={start_url}",
        "-e",
        f"GEO_CRAWL_OPS_TTL_MIN={max(5, int(ttl_min))}",
        "-e",
        f"GEO_CRAWL_OPS_REASON={reason}",
    ]
    complete_url = build_complete_callback_url(settings.geo_crawl_ops_callback_base_url)
    complete_url, needs_host_gateway = rewrite_callback_url_for_container(complete_url)
    if complete_url:
        args.extend(["-e", f"GEO_CRAWL_OPS_COMPLETE_URL={complete_url}"])
        logger.info("geo-crawl-ops COMPLETE_URL=%s", complete_url)
    elif (settings.geo_crawl_ops_callback_base_url or "").strip():
        logger.warning("geo-crawl-ops callback base set but complete URL empty")
    else:
        logger.warning(
            "GEO_CRAWL_OPS_CALLBACK_BASE_URL unset; login will not auto-write cookies"
        )
    if needs_host_gateway:
        # Linux Docker: map host.docker.internal → host gateway (Docker 20.10+)
        args.extend(["--add-host", "host.docker.internal:host-gateway"])
    network = (settings.geo_crawl_ops_docker_network or "").strip()
    if network:
        args.extend(["--network", network])

    has_state = bool(
        storage_state
        and isinstance(storage_state.get("cookies"), list)
        and storage_state["cookies"]
    )
    if has_state:
        args.extend(["-e", "GEO_CRAWL_OPS_STORAGE_STATE_PATH=/data/storage_state.json"])

    args.append(image)

    try:
        container_id = _run_docker(args, timeout_s=120.0)
        if has_state:
            with tempfile.TemporaryDirectory(prefix="geo-crawl-ops-state-") as tmp:
                state_path = Path(tmp) / "storage_state.json"
                state_path.write_text(
                    json.dumps(storage_state, ensure_ascii=False),
                    encoding="utf-8",
                )
                _run_docker(
                    ["cp", str(state_path), f"{container_id}:/data/storage_state.json"],
                    timeout_s=30.0,
                )
        _run_docker(["start", container_id], timeout_s=60.0)
        host_port = _inspect_host_port(container_id, container_port=6080)
        login_url = build_login_url(
            settings.geo_crawl_ops_novnc_base_url,
            ticket_token=ticket_token,
            host_port=host_port,
        )
        logger.info(
            "geo-crawl-ops session started platform=%s name=%s id=%s port=%s",
            platform,
            name,
            container_id[:12],
            host_port,
        )
        return OpsSessionSpawn(
            container_id=container_id,
            login_url=login_url,
            host_port=host_port,
            name=name,
        )
    except Exception:
        try:
            _run_docker(["rm", "-f", name], timeout_s=30.0)
        except Exception:
            pass
        raise


def _inspect_host_port(container_id: str, *, container_port: int) -> int:
    raw = _run_docker(
        [
            "inspect",
            "-f",
            f'{{{{(index (index .NetworkSettings.Ports "{container_port}/tcp") 0).HostPort}}}}',
            container_id,
        ],
        timeout_s=30.0,
    )
    try:
        return int(raw.strip().strip("'\"") or "0")
    except ValueError:
        return 0


def ops_session_running(container_id: str) -> bool:
    """True when the container exists and ``State.Running`` is true."""
    cid = (container_id or "").strip()
    if not cid or not docker_cli_available():
        return False
    try:
        raw = _run_docker(
            ["inspect", "-f", "{{.State.Running}}", cid],
            timeout_s=15.0,
        )
    except GeoCrawlOpsDockerError:
        return False
    return raw.strip().lower() in ("true", "1")


def stop_ops_session(container_id: str) -> None:
    """Force-remove a geo-crawl-ops container (idempotent)."""
    cid = (container_id or "").strip()
    if not cid:
        return
    if not docker_cli_available():
        logger.warning("docker CLI missing; cannot stop geo-crawl-ops container %s", cid[:12])
        return
    try:
        _run_docker(["rm", "-f", cid], timeout_s=45.0)
        logger.info("geo-crawl-ops session stopped id=%s", cid[:12])
    except GeoCrawlOpsDockerError as exc:
        logger.warning("geo-crawl-ops stop failed id=%s: %s", cid[:12], exc)
