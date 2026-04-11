"""Apex CLI — `apex start|stop|status|logs`."""
from __future__ import annotations

import os
import sys
import threading
import webbrowser

import click

from apex import __version__
from apex.config import CONFIG


def _ping_telemetry() -> None:
    """Fire-and-forget anonymous install ping. Opt-out via APEX_NO_TELEMETRY=1."""
    if os.environ.get("APEX_NO_TELEMETRY"):
        return
    try:
        import json
        import secrets
        import urllib.request
        from apex.config import CONFIG_DIR

        id_file = CONFIG_DIR / ".install_id"
        if not id_file.exists():
            id_file.write_text(secrets.token_hex(16))
        install_id = id_file.read_text().strip()

        payload = json.dumps({"v": __version__, "id": install_id}).encode()
        req = urllib.request.Request(
            "https://telemetry.tryapex.dev/ping",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass


@click.group(invoke_without_command=False)
@click.version_option(__version__, prog_name="apex")
def main() -> None:
    """Apex — self-hosted ML platform for small AI teams."""


@main.command()
@click.option("--host", default=None, help="Bind host (default from config)")
@click.option("--port", default=None, type=int, help="Bind port (default from config)")
@click.option("--workers", default=1, type=int, help="Uvicorn workers")
@click.option("--no-browser", is_flag=True, help="Don't auto-open browser")
@click.option("--skip-docker-check", is_flag=True, help="Skip docker daemon check (dev mode)")
def start(host: str | None, port: int | None, workers: int, no_browser: bool, skip_docker_check: bool) -> None:
    """Start the Apex platform."""
    host = host or CONFIG.get("host", "0.0.0.0")
    port = port or CONFIG.get("port", 7000)

    # 1. Check Docker daemon
    if not skip_docker_check:
        try:
            import docker
            docker.from_env().ping()
        except Exception as e:
            click.secho("✗ Docker daemon not found.", fg="red", bold=True)
            click.echo(f"  {e}")
            click.echo("  Please start Docker first, or re-run with --skip-docker-check for dev mode.")
            sys.exit(1)

    # 2. Init DB
    from apex.server.db import init_db
    init_db()

    # 3. Create owner account on first run
    from apex.server.auth import ensure_owner_account
    creds = ensure_owner_account()
    if creds:
        email, password = creds
        click.secho("\n=== First-run owner account created ===", fg="cyan", bold=True)
        click.echo(f"  email:    {email}")
        click.echo(f"  password: {password}")
        click.secho("  Save this — it will not be shown again.", fg="yellow")

    # 4. Anonymous telemetry ping (opt-out via APEX_NO_TELEMETRY=1)
    if not os.environ.get("APEX_NO_TELEMETRY"):
        click.echo("  Telemetry: anonymous usage pings are enabled.  Set APEX_NO_TELEMETRY=1 to opt out.\n")
    threading.Thread(target=_ping_telemetry, daemon=True).start()

    # 5. Start monitor collector thread
    from apex.monitor.collector import start_collector
    start_collector()

    # 6. Start scheduler worker thread
    from apex.scheduler.worker import start_worker
    start_worker()

    # 7. Launch Uvicorn
    import uvicorn
    from apex.server.app import create_app
    from apex.config import CONFIG_DIR

    app = create_app()

    # Write PID file so `apex stop` can signal this process cleanly.
    pid_path = CONFIG_DIR / "apex.pid"
    log_path = CONFIG_DIR / "apex.log"
    try:
        pid_path.write_text(str(os.getpid()))
    except Exception:
        pass

    import atexit
    atexit.register(lambda: pid_path.unlink(missing_ok=True))

    click.secho(f"\n▲ Apex is running at http://localhost:{port}", fg="cyan", bold=True)
    click.echo(f"  Logs: {log_path}  (apex logs --tail 100)\n")

    if not no_browser:
        try:
            threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{port}")).start()
        except Exception:
            pass

    # Route uvicorn logs to both stdout and ~/.apex/apex.log
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(message)s",
                "use_colors": True,
            },
            "file": {"format": "%(asctime)s %(levelname)s %(message)s"},
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stderr",
            },
            "file": {
                "class": "logging.FileHandler",
                "formatter": "file",
                "filename": str(log_path),
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default", "file"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["default", "file"], "level": "INFO", "propagate": False},
        },
    }

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        workers=workers if workers > 1 else None,
        log_config=log_config,
    )


@main.command("build-images")
@click.option("--pytorch", is_flag=True, help="Also build the PyTorch/CUDA image (~8 GB)")
def build_images(pytorch: bool) -> None:
    """Build the bundled base images locally (one-time setup)."""
    import pathlib
    import subprocess

    docker_dir = pathlib.Path(__file__).parent / "docker"

    images = [("apex/code-server:python", "python.Dockerfile", "~2 min")]
    if pytorch:
        images.append(("apex/code-server:pytorch", "pytorch.Dockerfile", "~15 min, ~8 GB"))

    for tag, dockerfile, estimate in images:
        click.echo(f"\nBuilding {tag}  ({estimate}) ...")
        result = subprocess.run(
            ["docker", "build", "-t", tag, "-f", str(docker_dir / dockerfile), str(docker_dir)],
        )
        if result.returncode != 0:
            click.secho(f"✗ Failed to build {tag}", fg="red", bold=True)
            sys.exit(1)
        click.secho(f"✓ {tag}", fg="green", bold=True)

    click.secho("\nDone. Run `apex start` to launch the platform.", fg="cyan")


@main.group()
def config() -> None:
    """View or update Apex configuration."""


@config.command("show")
def config_show() -> None:
    """Show current configuration."""
    from apex.config import CONFIG_PATH
    display_keys = ("workspace_path", "host", "port", "session_port_range")
    for k in display_keys:
        click.echo(f"  {k}: {CONFIG.get(k)}")
    click.echo(f"\n  config file: {CONFIG_PATH}")


@config.command("set")
@click.argument("key", metavar="KEY")
@click.argument("value", metavar="VALUE")
def config_set(key: str, value: str) -> None:
    """Persist a config value (e.g. apex config set workspace /mnt/ssd/apex)."""
    import json
    from apex.config import CONFIG_PATH, CONFIG_DIR

    # normalise alias
    if key == "workspace":
        key = "workspace_path"

    _SETTABLE = {"workspace_path", "port", "host", "session_port_range"}
    if key not in _SETTABLE:
        click.secho(f"✗ Unknown key '{key}'. Settable keys: workspace, port, host, session_port_range", fg="red")
        raise SystemExit(1)

    if key == "workspace_path":
        import pathlib
        path = pathlib.Path(value).expanduser().resolve()
        if not path.exists():
            click.secho(f"  Warning: path does not exist yet — it will be created on next start.", fg="yellow")
        value = str(path)

    if key == "port":
        try:
            value = int(value)  # type: ignore[assignment]
        except ValueError:
            click.secho("✗ port must be an integer", fg="red")
            raise SystemExit(1)

    if key == "session_port_range":
        import re
        parts = re.split(r"[\s,]+", value.strip())
        if len(parts) != 2:
            click.secho("✗ session_port_range requires two integers, e.g. 'apex config set session_port_range 8080,8200'", fg="red")
            raise SystemExit(1)
        try:
            lo, hi = int(parts[0]), int(parts[1])
        except ValueError:
            click.secho("✗ session_port_range values must be integers", fg="red")
            raise SystemExit(1)
        if lo >= hi:
            click.secho("✗ session_port_range start must be less than end", fg="red")
            raise SystemExit(1)
        value = [lo, hi]  # type: ignore[assignment]

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}
    except json.JSONDecodeError:
        data = {}
    data[key] = value
    CONFIG_PATH.write_text(json.dumps(data, indent=2))
    click.secho(f"✓ {key} = {value}", fg="green")
    if key == "workspace_path":
        click.echo("  Restart `apex start` for the change to take effect.")


@main.command()
def stop() -> None:
    """Stop the Apex platform."""
    import signal
    from apex.config import CONFIG_DIR

    pid_path = CONFIG_DIR / "apex.pid"
    if not pid_path.exists():
        click.echo("Apex does not appear to be running (no PID file found at ~/.apex/apex.pid).")
        click.echo("If it is running, press Ctrl+C in the terminal where `apex start` was run.")
        return
    try:
        pid = int(pid_path.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        pid_path.unlink(missing_ok=True)
        click.secho(f"✓ Sent SIGTERM to apex process (PID {pid})", fg="green")
    except ProcessLookupError:
        pid_path.unlink(missing_ok=True)
        click.echo("Apex process not found — it may have already stopped.")
    except Exception as e:
        click.secho(f"✗ Failed to stop: {e}", fg="red")
        click.echo("  Press Ctrl+C in the terminal where `apex start` was run.")


@main.command()
def status() -> None:
    """Show Apex status."""
    import urllib.request
    import json
    port = CONFIG.get("port", 7000)
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/api/health", timeout=1) as r:
            data = json.loads(r.read().decode())
        click.secho(f"● running on :{port}  {data}", fg="green")
    except Exception:
        click.secho(f"○ not running (no response on :{port})", fg="red")


@main.command()
@click.option("--tail", default=100, type=int, help="Number of lines to show")
def logs(tail: int) -> None:
    """Tail recent platform logs from ~/.apex/apex.log."""
    from apex.config import CONFIG_DIR

    log_path = CONFIG_DIR / "apex.log"
    if not log_path.exists():
        click.echo("No log file found — logs are written to ~/.apex/apex.log when `apex start` is run.")
        click.echo("If apex is already running without a log file, restart it to begin logging.")
        return
    lines = log_path.read_text(errors="replace").splitlines()
    for line in lines[-tail:]:
        click.echo(line)


if __name__ == "__main__":
    main()
