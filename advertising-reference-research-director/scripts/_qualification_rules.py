#!/usr/bin/env python3
"""Central semantic qualification rules shared by import and final validation."""

from __future__ import annotations

import math
from datetime import timedelta
from typing import Any


MAX_FUTURE_SKEW = timedelta(minutes=5)
MIN_IMAGE_EDGE = 240
MIN_IMAGE_PIXELS = 230_400
HIGH_RISK_RIGHTS = {"downloadable", "internal_board_use", "commercial_reuse"}


def finite_number(value: Any) -> bool:
    return (
        isinstance(value, int) and not isinstance(value, bool)
    ) or (
        isinstance(value, float) and math.isfinite(value)
    )


def media_evidence_errors(receipt: dict[str, Any], modality: str) -> list[str]:
    errors: list[str] = []
    media = receipt.get("media_check")
    if not isinstance(media, dict) or media.get("status") != "passed" or media.get("kind") != modality:
        return ["media_check must be passed and match the candidate modality"]
    if modality == "image":
        image = media.get("image_render")
        if not isinstance(image, dict):
            return ["qualified image receipt lacks image_render"]
        width = image.get("natural_width")
        height = image.get("natural_height")
        if image.get("rendered") is not True or image.get("placeholder_detected") is not False:
            errors.append("qualified image must be rendered and not a placeholder")
        if not isinstance(image.get("asset_locator"), str) or not image["asset_locator"].strip():
            errors.append("qualified image lacks a concrete asset locator")
        if not isinstance(width, int) or isinstance(width, bool) or not isinstance(height, int) or isinstance(height, bool):
            errors.append("qualified image dimensions must be integers")
        elif min(width, height) < MIN_IMAGE_EDGE or width * height < MIN_IMAGE_PIXELS:
            errors.append(
                f"qualified image must have min edge >= {MIN_IMAGE_EDGE} and pixels >= {MIN_IMAGE_PIXELS}"
            )
    elif modality == "video":
        video = media.get("video_playback")
        if not isinstance(video, dict):
            return ["qualified video receipt lacks video_playback"]
        progress = video.get("observed_progress_seconds")
        duration = video.get("duration_seconds")
        if video.get("player_present") is not True or video.get("playback_started") is not True:
            errors.append("qualified video requires a present player and started playback")
        if video.get("specific_work_matched") is not True:
            errors.append("qualified video must bind playback to the specific work")
        if not finite_number(progress) or not finite_number(duration):
            errors.append("qualified video progress and duration must be finite numbers")
        elif not (0 < progress <= duration):
            errors.append("qualified video progress must be > 0 and <= duration")
    else:
        errors.append("unsupported qualified media modality")
    return errors


def expected_dedup_status(version_relation: Any) -> str:
    if version_relation in {"unique", "same_campaign_distinct_asset"}:
        return "unique"
    if version_relation in {"cutdown", "regional_version"}:
        return "authorized_version"
    if version_relation in {"mirror", "repost"}:
        return "duplicate"
    return "uncertain"
