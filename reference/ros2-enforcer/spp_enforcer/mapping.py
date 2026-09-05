"""Deterministic, ROS-free mapping of trusted admission profiles to Nav2 limits."""
from __future__ import annotations

from dataclasses import dataclass
import math
import re

from spp_admission.models import AdmissionProfile


@dataclass(frozen=True)
class Nav2EnforcementPlan:
    navigation_allowed: bool
    max_speed_mps: float | None = None
    reasons: tuple[str, ...] = ()


def map_profile(profile: AdmissionProfile) -> Nav2EnforcementPlan:
    """Map movement.max_speed <= bounds; this does not authenticate profiles.

    Text restrictions accept only movement.max_speed<=NUMBER (m/s).
    None means no speed operation, not removal of a previously applied limit.
    """
    def deny(reason: str) -> Nav2EnforcementPlan:
        return Nav2EnforcementPlan(False, reasons=(reason,))

    if not isinstance(profile, AdmissionProfile):
        return deny("invalid_admission_profile")
    if profile.status == "DENIED":
        return deny("admission_denied")
    if profile.status not in ("ADMITTED", "DEGRADED"):
        return deny("invalid_admission_status")
    bounds: list[float] = []
    try:
        def add_bound(value: object) -> None:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("invalid_speed_bound")
            speed = float(value)
            if not math.isfinite(speed) or speed < 0:
                raise ValueError("invalid_speed_bound")
            bounds.append(speed)

        for guarantee in profile.operating_profile.get("guarantees", []):
            if guarantee["id"] != "movement.max_speed":
                continue
            if guarantee.get("operator") != "<=":
                return deny("unsupported_speed_operator")
            if guarantee.get("unit", "m/s") != "m/s":
                return deny("unsupported_speed_unit")
            add_bound(guarantee["value"])
        restrictions = profile.restrictions
        embedded = profile.operating_profile.get("restrictions", [])
        if not isinstance(restrictions, list) or not isinstance(embedded, list):
            return deny("invalid_profile_restrictions")
        for restriction in restrictions + embedded:
            if not isinstance(restriction, str):
                return deny("invalid_profile_restrictions")
            match = re.fullmatch(r"movement\.max_speed\s*<=\s*(\S+)", restriction.strip())
            if not match:
                return deny("unsupported_profile_restriction")
            try:
                value = float(match[1])
            except ValueError:
                return deny("invalid_speed_bound")
            add_bound(value)
        speed = min(bounds) if bounds else None
        if speed == 0:
            # Nav2 SpeedLimit(0) means NO LIMIT, not a stop command.
            return deny("zero_speed_requires_stop")
        return Nav2EnforcementPlan(True, speed)
    except (AttributeError, KeyError, TypeError, OverflowError):
        return deny("invalid_admission_profile")
    except ValueError as error:
        return deny(str(error))
