"""Run geo-web-crawl jobs: resident HTTP service (preferred) or local CLI.

Production: ``GEO_WEB_CRAWL_BASE_URL`` → long-running geo-web-crawl service.
Dev fallback: host ``geo_web_crawl.cli`` subprocess.
Per-job ``docker run --rm`` is opt-in only (``GEO_WEB_CRAWL_DOCKER_EPHEMERAL=1``).
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_MODULE = "aperix_geo.services.geo_web_crawl.cli"
_SAFE = re.compile(r"[^a-zA-Z0-9_.-]+")


def resolve_geo_web_crawl_docker_image(explicit: str | None = None) -> str:
    if explicit is not None and str(explicit).strip():
        return str(explicit).strip()
    return (os.environ.get("GEO_WEB_CRAWL_DOCKER_IMAGE") or "").strip()


def should_use_geo_web_crawl_docker(*, docker_image: str | None = None) -> bool:
    return bool(resolve_geo_web_crawl_docker_image(docker_image))


def _ephemeral_docker_enabled() -> bool:
    return (os.environ.get("GEO_WEB_CRAWL_DOCKER_EPHEMERAL") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _fail(message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error_type": "CrawlError",
        "error": message,
        "human_ops": False,
        "storage_state": None,
    }


def _read_result(out_path: Path, *, returncode: int, stderr: str, stdout: str) -> dict[str, Any]:
    if not out_path.is_file():
        err_tail = (stderr or stdout or "").strip()[-800:]
        return _fail(f"crawl missing output file exit={returncode}: {err_tail}")
    try:
        result = json.loads(out_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return _fail(f"crawl invalid output JSON: {exc}")
    if not isinstance(result, dict):
        return _fail(f"crawl returned non-dict: {type(result)!r}")
    if not result.get("ok"):
        logger.warning(
            "geo-web-crawl-child result ok=false type=%s err=%s exit=%s",
            result.get("error_type"),
            str(result.get("error") or "")[:400],
            returncode,
        )
    return result


def _log_child_output(*, stderr: str, stdout: str, returncode: int) -> None:
    if stderr:
        for line in stderr.strip().splitlines()[-40:]:
            logger.info("geo-web-crawl-child: %s", line)
    if returncode != 0 and stdout:
        for line in stdout.strip().splitlines()[-20:]:
            logger.info("geo-web-crawl-child-stdout: %s", line)


def _run_local_subprocess(
    payload: dict[str, Any],
    *,
    join_timeout: float,
    mode: str = "crawl",
) -> dict[str, Any]:
    env = os.environ.copy()
    env.pop("CELERY_WORKER_ROLE", None)

    with tempfile.TemporaryDirectory(prefix="geo-web-crawl-") as tmp:
        tmp_path = Path(tmp)
        in_path = tmp_path / "in.json"
        out_path = tmp_path / "out.json"
        in_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        cmd = [
            sys.executable,
            "-m",
            _MODULE,
            "--mode",
            mode,
            "--in",
            str(in_path),
            "--out",
            str(out_path),
        ]
        try:
            completed = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=join_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return _fail(f"subprocess crawl timed out after {join_timeout:.0f}s")
        except Exception as exc:  # noqa: BLE001
            return _fail(f"subprocess crawl failed to start: {exc}")

        _log_child_output(
            stderr=completed.stderr or "",
            stdout=completed.stdout or "",
            returncode=completed.returncode,
        )
        return _read_result(
            out_path,
            returncode=completed.returncode,
            stderr=completed.stderr or "",
            stdout=completed.stdout or "",
        )





def _run_docker_ephemeral(
    payload: dict[str, Any],
    *,
    join_timeout: float,
    image: str,
    mode: str = "crawl",
) -> dict[str, Any]:
    """Emergency one-shot container (expensive; prefer resident service)."""
    if shutil.which("docker") is None:
        return _fail("GEO_WEB_CRAWL_DOCKER_EPHEMERAL set but docker CLI not found")

    shm = (os.environ.get("GEO_WEB_CRAWL_DOCKER_SHM_SIZE") or "").strip() or "1g"
    network = (os.environ.get("GEO_WEB_CRAWL_DOCKER_NETWORK") or "").strip()
    name_slug = _SAFE.sub("-", image.split("/")[-1].split(":")[0])[:20] or "crawl"

    with tempfile.TemporaryDirectory(prefix="geo-web-crawl-") as tmp:
        tmp_path = Path(tmp)
        in_path = tmp_path / "in.json"
        out_path = tmp_path / "out.json"
        in_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        cmd = [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "python",
            f"--shm-size={shm}",
            "--name",
            f"geo-web-crawl-{mode}-{os.getpid()}-{name_slug}"[:63],
            "-v",
            f"{tmp_path}:/data",
            "-e",
            "PYTHONPATH=/app/src",
        ]
        if network:
            cmd.extend(["--network", network])
        cmd.extend(
            [
                image,
                "-m",
                _MODULE,
                "--mode",
                mode,
                "--in",
                "/data/in.json",
                "--out",
                "/data/out.json",
            ]
        )

        logger.warning(
            "geo web crawl ephemeral docker mode=%s image=%s (prefer GEO_WEB_CRAWL_BASE_URL)",
            mode,
            image,
        )
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=join_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            try:
                subprocess.run(
                    ["docker", "rm", "-f", cmd[cmd.index("--name") + 1]],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
            except Exception:
                pass
            return _fail(f"docker crawl timed out after {join_timeout:.0f}s image={image}")
        except Exception as exc:  # noqa: BLE001
            return _fail(f"docker crawl failed to start: {exc}")

        _log_child_output(
            stderr=completed.stderr or "",
            stdout=completed.stdout or "",
            returncode=completed.returncode,
        )
        if completed.returncode != 0 and not out_path.is_file():
            err = (completed.stderr or completed.stdout or "").strip()[-800:]
            return _fail(f"docker crawl exit={completed.returncode}: {err}")

        return _read_result(
            out_path,
            returncode=completed.returncode,
            stderr=completed.stderr or "",
            stdout=completed.stdout or "",
        )


def run_geo_web_crawl_spawn(
    payload: dict[str, Any],
    *,
    timeout_s: float,
    docker_image: str | None = None,
    mode: str = "crawl",
    base_url: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """Run crawl/probe via resident HTTP service, else local CLI (or ephemeral docker)."""
    join_timeout = max(60.0, float(timeout_s) + 60.0)
    job_mode = (mode or "crawl").strip().lower() or "crawl"
    if job_mode not in ("crawl", "probe"):
        job_mode = "crawl"
    payload = {
        **payload,
        "mode": job_mode,
        "platform": str(payload.get("platform") or "doubao").strip().lower() or "doubao",
        "timeout_s": float(payload.get("timeout_s") or timeout_s),
    }

    from aperix_geo.services.geo_web_crawl.client import (
        resolve_geo_web_crawl_base_url,
        run_geo_web_crawl_job,
    )

    url = resolve_geo_web_crawl_base_url(base_url)
    if url:
        return run_geo_web_crawl_job(
            payload,
            base_url=url,
            token=token,
            timeout_s=float(timeout_s),
        )

    image = resolve_geo_web_crawl_docker_image(docker_image)
    if image and _ephemeral_docker_enabled():
        return _run_docker_ephemeral(
            payload, join_timeout=join_timeout, image=image, mode=job_mode
        )

    if image and not url:
        logger.warning(
            "GEO_WEB_CRAWL_DOCKER_IMAGE is set but GEO_WEB_CRAWL_BASE_URL is empty; "
            "use a resident service URL. Falling back to host geo_web_crawl.cli."
        )

    logger.warning(
        "geo web crawl: GEO_WEB_CRAWL_BASE_URL unset; "
        "using host geo_web_crawl.cli subprocess. mode=%s timeout_s=%s",
        job_mode,
        timeout_s,
    )
    return _run_local_subprocess(payload, join_timeout=join_timeout, mode=job_mode)
