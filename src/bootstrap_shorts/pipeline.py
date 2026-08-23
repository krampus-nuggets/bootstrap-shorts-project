"""End-to-end bootstrap: prepare files, then drive After Effects."""

from __future__ import annotations

import logging
from typing import Any

from bootstrap_shorts.ae_bridge import DEFAULT_TIMEOUT_SECONDS, run_after_effects_job
from bootstrap_shorts.config import ResolvedConfig
from bootstrap_shorts.detect_ae import resolve_afterfx
from bootstrap_shorts.filesystem import (
    build_job_payload,
    copy_raw_footage,
    disk_footage_dir,
    job_path,
    prepare_project_dir,
    result_path,
    write_job_json,
)

LOGGER = logging.getLogger(__name__)


def run_bootstrap(
    config: ResolvedConfig,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    root = config.project_dir
    LOGGER.info("Preparing project directory %s", root)
    prepare_project_dir(root, force=config.force)

    footage_dir = disk_footage_dir(root, config.main_import_folder)
    LOGGER.info("Copying %s raw footage file(s) to %s", len(config.raw_footage), footage_dir)
    imported_files = copy_raw_footage(config.raw_footage, footage_dir)

    payload = build_job_payload(config, imported_files)
    written_job = write_job_json(job_path(root), payload)
    LOGGER.info("Wrote After Effects job %s", written_job)

    afterfx = resolve_afterfx(config.after_effects_exe)
    LOGGER.info("Using After Effects at %s", afterfx)

    result = run_after_effects_job(
        afterfx,
        written_job,
        result_path(root),
        timeout=timeout,
    )

    for warning in result.get("warnings") or []:
        LOGGER.warning("%s", warning)

    LOGGER.info(
        "Imported %s item(s) into the main project and %s item(s) into the pre-process project",
        len(result.get("imported_main") or []),
        len(result.get("imported_preprocess") or []),
    )
    relinked = result.get("relinked") or []
    if relinked:
        LOGGER.info("Relinked %s existing template footage item(s)", len(relinked))

    LOGGER.info("Bootstrap complete: %s", root)
    return result
