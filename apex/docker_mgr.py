"""Docker SDK wrapper used by the scheduler and sessions routes."""
from __future__ import annotations

import socket
from typing import Any

try:
    import docker
    from docker.errors import DockerException, ImageNotFound, NotFound
    from docker.types import DeviceRequest
except ImportError:  # pragma: no cover
    docker = None  # type: ignore
    DockerException = Exception  # type: ignore
    ImageNotFound = Exception  # type: ignore
    NotFound = Exception  # type: ignore
    DeviceRequest = None  # type: ignore

from apex.config import CONFIG


_client = None


def get_client():
    global _client
    if docker is None:
        raise RuntimeError("docker SDK not installed")
    if _client is None:
        _client = docker.from_env()
    return _client


def is_available() -> bool:
    try:
        get_client().ping()
        return True
    except Exception:
        return False


def list_images() -> list[dict[str, Any]]:
    try:
        client = get_client()
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    try:
        for img in client.images.list():
            tags = img.tags or []
            size_gb = round((img.attrs.get("Size", 0) or 0) / 1024**3, 2)
            out.append({"id": img.id, "tags": tags, "size_gb": size_gb})
    except Exception:
        pass
    return out


def _gpu_kwargs(gpu_count: int) -> dict[str, Any]:
    if gpu_count <= 0 or DeviceRequest is None:
        return {}
    count = -1 if gpu_count >= 99 else gpu_count
    return {"device_requests": [DeviceRequest(count=count, capabilities=[["gpu"]])]}


def _remove_by_name(client, name: str) -> None:
    """Force-remove a container with the given name if one exists (stale from a prior run)."""
    try:
        old = client.containers.get(name)
    except NotFound:
        return
    except Exception:
        return
    try:
        old.remove(force=True)
    except Exception:
        pass


def _create_and_start(
    client,
    *,
    name: str,
    check_running_after: bool,
    **create_kwargs: Any,
):
    """Shared create→start→verify helper used by both jobs and sessions.

    Why split create and start instead of using `containers.run`:
    - `run()` bundles create+start and, on start failure, leaves a half-created
      container behind AND raises before we can see the container object.
    - With explicit create+start we can always `remove(force=True)` on any
      failure path, so we never leak stale containers that would cause 409
      name conflicts on the next attempt.

    ``check_running_after`` controls whether we briefly wait and verify the
    container is still running after start — the session path wants this
    (code-server should stay up; exiting immediately means the entrypoint is
    missing), but jobs are expected to start, run, and eventually exit, so
    this check isn't applied to them.
    """
    _remove_by_name(client, name)

    try:
        container = client.containers.create(name=name, **create_kwargs)
    except ImageNotFound:
        raise RuntimeError(f"Docker image not found: {create_kwargs.get('image')}")
    except Exception as e:
        raise RuntimeError(_clean_docker_error(e))

    try:
        container.start()
        if check_running_after:
            import time
            time.sleep(0.4)
            container.reload()
            if container.status != "running":
                logs = ""
                try:
                    logs = container.logs(tail=20).decode(errors="replace").strip()
                except Exception:
                    pass
                detail = logs.splitlines()[-1] if logs else f"container state: {container.status}"
                if logs and ("executable file not found" in logs or "not found in $PATH" in logs):
                    detail = (
                        f"image {create_kwargs.get('image')!r} does not have code-server installed. "
                        f"Use an image with code-server (e.g. codercom/code-server:latest)."
                    )
                raise RuntimeError(detail)
    except Exception as e:
        try:
            container.remove(force=True)
        except Exception:
            pass
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(_clean_docker_error(e))

    return container


def run_job_container(job_id: int, image: str, command: str, gpu_count: int) -> str:
    client = get_client()
    workspace = CONFIG["workspace_path"]
    name = f"apex-job-{job_id}"

    create_kwargs: dict[str, Any] = {
        "image": image,
        "command": command,
        "detach": True,
        "volumes": {workspace: {"bind": "/workspace", "mode": "rw"}},
        "working_dir": "/workspace",
        "shm_size": "16g",
    }
    create_kwargs.update(_gpu_kwargs(gpu_count))

    # Jobs are expected to start, run, and exit — don't enforce "still running"
    # after the startup delay, or a very fast script would be misreported.
    container = _create_and_start(client, name=name, check_running_after=False, **create_kwargs)
    return container.id


def run_session_container(session_id: int, image: str, port: int) -> str:
    client = get_client()
    workspace = CONFIG["workspace_path"]
    name = f"apex-session-{session_id}"
    container = _create_and_start(
        client,
        name=name,
        check_running_after=True,
        image=image,
        command=[
            "code-server",
            "--auth", "none",
            "--bind-addr", "0.0.0.0:8080",
        ],
        detach=True,
        ports={"8080/tcp": port},
        volumes={workspace: {"bind": "/workspace", "mode": "rw"}},
        **_gpu_kwargs(99),  # request all available GPUs (count=-1)
    )
    return container.id


def _clean_docker_error(e: Exception) -> str:
    """Extract the useful bit from the Docker SDK's verbose HTTP error wrappers."""
    msg = str(e)
    # Patterns like: 400 Client Error for http+docker://...: Bad Request ("real message")
    import re
    m = re.search(r'\(\"(.*)\"\)\s*$', msg)
    if m:
        msg = m.group(1)
    # Further trim OCI runtime goo
    if "executable file not found in $PATH" in msg:
        return "executable not found in image — does it have code-server installed?"
    if "pull access denied" in msg or "repository does not exist" in msg:
        return "image not found"
    if len(msg) > 240:
        msg = msg[:240] + "…"
    return msg


def get_container(container_id: str):
    return get_client().containers.get(container_id)


def stop_container(container_id: str, remove: bool = True) -> None:
    try:
        c = get_container(container_id)
        try:
            c.stop(timeout=5)
        except Exception:
            pass
        if remove:
            try:
                c.remove(force=True)
            except Exception:
                pass
    except NotFound:
        pass
    except Exception:
        pass


def find_free_port(start: int, end: int) -> int | None:
    for p in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", p))
                return p
            except OSError:
                continue
    return None
