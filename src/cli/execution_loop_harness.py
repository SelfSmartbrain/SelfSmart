"""Separate-process execution harness for SIGKILL recovery verification."""

from __future__ import annotations

import json
import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import click
from rich.console import Console
from rich.table import Table


console = Console()
DEFAULT_STATE_FILE = Path(".modelx/execution_loop_checkpoints.json")
DEFAULT_PID_FILE = Path("/tmp/modelx_harness.pid")


class FileCheckpointStore:
    """Durable append-only checkpoint history backed by one JSON file."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(
        self,
        *,
        objective_id: str,
        description: str,
        current_step: int,
        total_steps: int,
        status: str,
    ) -> dict[str, Any]:
        """Append a checkpoint and persist it with an atomic file replacement."""
        document = self._read_document()
        history = document["objectives"].setdefault(objective_id, [])
        sequence = len(history) + 1
        checkpoint = {
            "checkpoint_name": f"harness_{sequence:04d}",
            "objective_id": objective_id,
            "state_snapshot": {
                "tick_count": current_step,
                "objective_id": objective_id,
                "objective_description": description,
                "running": status == "running",
                "status": status,
            },
            "progress_snapshot": {
                "step": current_step,
                "total_steps": total_steps,
                "progress_percent": (current_step / total_steps) * 100,
            },
            "metadata": {
                "auto": True,
                "type": "process_harness",
                "sequence": sequence,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        history.append(checkpoint)
        self._atomic_write(document)
        return checkpoint

    def latest(self, objective_id: str) -> dict[str, Any] | None:
        """Return the latest checkpoint for an objective."""
        history = self._read_document()["objectives"].get(objective_id, [])
        return history[-1] if history else None

    def list(self, objective_id: str) -> list[dict[str, Any]]:
        """Return all checkpoints for an objective."""
        return list(self._read_document()["objectives"].get(objective_id, []))

    def _read_document(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "objectives": {}}
        with self.path.open(encoding="utf-8") as checkpoint_file:
            document = json.load(checkpoint_file)
        if document.get("version") != 1 or not isinstance(document.get("objectives"), dict):
            raise click.ClickException(f"Invalid checkpoint store: {self.path}")
        return document

    def _atomic_write(self, document: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        with temporary_path.open("w", encoding="utf-8") as checkpoint_file:
            json.dump(document, checkpoint_file, indent=2, sort_keys=True)
            checkpoint_file.flush()
            os.fsync(checkpoint_file.fileno())
        os.replace(temporary_path, self.path)


class ExecutionLoopHarness:
    """Run deterministic ticks and checkpoint after every completed tick."""

    def __init__(
        self,
        *,
        checkpoint_store: FileCheckpointStore,
        pid_file: Path,
        step_delay: float,
    ) -> None:
        if step_delay < 0:
            raise click.ClickException("--step-delay must be zero or greater")
        self.checkpoint_store = checkpoint_store
        self.pid_file = pid_file
        self.step_delay = step_delay

    def run_objective(
        self,
        *,
        objective_id: str,
        description: str,
        total_steps: int,
    ) -> dict[str, Any]:
        """Start a new objective and run it to completion."""
        if total_steps < 1:
            raise click.ClickException("--total-steps must be at least 1")
        if self.checkpoint_store.latest(objective_id):
            raise click.ClickException(
                f"Objective {objective_id} already has checkpoints; use restore"
            )

        self._write_pid_file()
        try:
            self._record(objective_id, description, 0, total_steps, "running")
            return self._run_from(objective_id, description, 0, total_steps)
        finally:
            self._remove_own_pid_file()

    def restore_and_resume(self, objective_id: str) -> dict[str, Any]:
        """Restore the latest durable checkpoint and resume remaining ticks."""
        checkpoint = self.checkpoint_store.latest(objective_id)
        if not checkpoint:
            raise click.ClickException(f"No checkpoint found for objective {objective_id}")

        state = checkpoint["state_snapshot"]
        progress = checkpoint["progress_snapshot"]
        if state["status"] == "completed":
            return checkpoint

        self._write_pid_file()
        try:
            return self._run_from(
                objective_id,
                state["objective_description"],
                int(progress["step"]),
                int(progress["total_steps"]),
            )
        finally:
            self._remove_own_pid_file()

    def _run_from(
        self,
        objective_id: str,
        description: str,
        current_step: int,
        total_steps: int,
    ) -> dict[str, Any]:
        latest = self.checkpoint_store.latest(objective_id)
        for step in range(current_step + 1, total_steps + 1):
            time.sleep(self.step_delay)
            latest = self._record(
                objective_id,
                description,
                step,
                total_steps,
                "running",
            )

        return self._record(
            objective_id,
            description,
            total_steps,
            total_steps,
            "completed",
        )

    def _record(
        self,
        objective_id: str,
        description: str,
        current_step: int,
        total_steps: int,
        status: str,
    ) -> dict[str, Any]:
        checkpoint = self.checkpoint_store.append(
            objective_id=objective_id,
            description=description,
            current_step=current_step,
            total_steps=total_steps,
            status=status,
        )
        console.print(
            f"{checkpoint['checkpoint_name']} "
            f"step={current_step}/{total_steps} status={status}"
        )
        return checkpoint

    def _write_pid_file(self) -> None:
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.write_text(str(os.getpid()), encoding="utf-8")

    def _remove_own_pid_file(self) -> None:
        try:
            if self.pid_file.read_text(encoding="utf-8").strip() == str(os.getpid()):
                self.pid_file.unlink()
        except FileNotFoundError:
            pass


def _build_harness(state_file: Path, pid_file: Path, step_delay: float) -> ExecutionLoopHarness:
    return ExecutionLoopHarness(
        checkpoint_store=FileCheckpointStore(state_file),
        pid_file=pid_file,
        step_delay=step_delay,
    )


@click.group()
def cli() -> None:
    """Run and inspect the process-level checkpoint recovery harness."""


@cli.command()
@click.argument("objective")
@click.option("--objective-id", default=None, help="Stable objective ID for restoration.")
@click.option("--total-steps", default=20, show_default=True, type=int)
@click.option("--step-delay", default=0.25, show_default=True, type=float)
@click.option(
    "--state-file",
    default=DEFAULT_STATE_FILE,
    show_default=True,
    type=click.Path(path_type=Path),
)
@click.option(
    "--pid-file",
    default=DEFAULT_PID_FILE,
    show_default=True,
    type=click.Path(path_type=Path),
)
def run(
    objective: str,
    objective_id: str | None,
    total_steps: int,
    step_delay: float,
    state_file: Path,
    pid_file: Path,
) -> None:
    """Run a new checkpointed objective."""
    resolved_objective_id = objective_id or f"obj_{uuid4().hex[:12]}"
    console.print(f"objective_id={resolved_objective_id}")
    harness = _build_harness(state_file, pid_file, step_delay)
    harness.run_objective(
        objective_id=resolved_objective_id,
        description=objective,
        total_steps=total_steps,
    )


@cli.command()
@click.argument("objective_id")
@click.option("--step-delay", default=0.25, show_default=True, type=float)
@click.option(
    "--state-file",
    default=DEFAULT_STATE_FILE,
    show_default=True,
    type=click.Path(path_type=Path),
)
@click.option(
    "--pid-file",
    default=DEFAULT_PID_FILE,
    show_default=True,
    type=click.Path(path_type=Path),
)
def restore(
    objective_id: str,
    step_delay: float,
    state_file: Path,
    pid_file: Path,
) -> None:
    """Restore and resume an objective from its latest checkpoint."""
    harness = _build_harness(state_file, pid_file, step_delay)
    checkpoint = harness.restore_and_resume(objective_id)
    console.print(
        f"restored objective_id={objective_id} "
        f"status={checkpoint['state_snapshot']['status']}"
    )


@cli.command("list-checkpoints")
@click.argument("objective_id")
@click.option(
    "--state-file",
    default=DEFAULT_STATE_FILE,
    show_default=True,
    type=click.Path(path_type=Path),
)
def list_checkpoints(objective_id: str, state_file: Path) -> None:
    """List durable checkpoints for an objective."""
    checkpoints = FileCheckpointStore(state_file).list(objective_id)
    checkpoint_table = Table(title=f"Checkpoints for {objective_id}")
    checkpoint_table.add_column("Name")
    checkpoint_table.add_column("Step")
    checkpoint_table.add_column("Status")
    checkpoint_table.add_column("Created")
    for checkpoint in checkpoints:
        checkpoint_table.add_row(
            checkpoint["checkpoint_name"],
            str(checkpoint["progress_snapshot"]["step"]),
            checkpoint["state_snapshot"]["status"],
            checkpoint["created_at"],
        )
    console.print(checkpoint_table)


@cli.command()
@click.option(
    "--pid-file",
    default=DEFAULT_PID_FILE,
    show_default=True,
    type=click.Path(path_type=Path),
)
def kill(pid_file: Path) -> None:
    """Send SIGKILL to the process recorded in the PID file."""
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except FileNotFoundError as exc:
        raise click.ClickException(f"PID file not found: {pid_file}") from exc
    except ValueError as exc:
        raise click.ClickException(f"Invalid PID file: {pid_file}") from exc
    os.kill(pid, signal.SIGKILL)


if __name__ == "__main__":
    cli()
