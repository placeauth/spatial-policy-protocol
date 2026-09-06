"""Reference task-acceptance gate; no Open-RMF dependency for pure mapping."""
from copy import deepcopy
from dataclasses import dataclass
from typing import Callable

from .models import AdmissionProfile, EvidenceBinding


@dataclass(frozen=True)
class TaskContext:
    actor_id: str
    place: str
    space: str


@dataclass(frozen=True)
class RMFAdmissionDecision:
    task_allowed: bool
    evidence_digest: str = ""
    restrictions: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


def _strings(value):
    return isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value)


def map_profile(profile: AdmissionProfile | None, context: TaskContext, *,
                accepted_restrictions: frozenset[str] = frozenset()) -> RMFAdmissionDecision:
    """Map a freshly evaluated profile from a trusted admission service.

    accepted_restrictions is deployment configuration: each exact string must
    have an implementation that enforces it for this task. It is not task input.
    This mapper cannot authenticate a Python dataclass or determine its age.
    """
    if profile is None:
        return RMFAdmissionDecision(False, reasons=("missing_profile",))
    profile = deepcopy(profile)
    if (not isinstance(profile, AdmissionProfile)
            or profile.status not in ("ADMITTED", "DEGRADED", "DENIED")
            or not isinstance(context, TaskContext)
            or not all(isinstance(v, str) and v.strip() for v in (
                context.actor_id, context.place, context.space,
                profile.actor_id, profile.place, profile.space, profile.evidence_digest))
            or type(profile.policy_version) is not int or profile.policy_version < 1
            or not isinstance(profile.binding, EvidenceBinding)
            or not isinstance(profile.operating_profile, dict)
            or not _strings(profile.restrictions) or not _strings(profile.reason_codes)
            or not _strings(profile.unresolved)
            or not _strings(profile.operating_profile.get("restrictions", []))):
        return RMFAdmissionDecision(False, reasons=("invalid_profile",))
    restrictions = tuple(sorted(set(profile.restrictions)
                                | set(profile.operating_profile.get("restrictions", []))))

    def deny(reason):
        return RMFAdmissionDecision(False, profile.evidence_digest, restrictions,
                                    (reason,) + tuple(profile.reason_codes))

    if (profile.actor_id, profile.place, profile.space) != (
            context.actor_id, context.place, context.space):
        return deny("profile_context_mismatch")
    if profile.status == "DENIED":
        return deny("admission_denied")
    if profile.binding.actor_id != context.actor_id:
        return deny("profile_binding_mismatch")
    if profile.status == "ADMITTED" and profile.unresolved:
        return deny("invalid_profile")
    if profile.status == "DEGRADED" and not restrictions:
        return deny("degraded_without_restrictions")
    if not set(restrictions) <= accepted_restrictions:
        return deny("restrictions_not_accepted")
    return RMFAdmissionDecision(True, profile.evidence_digest, restrictions,
                                tuple(profile.reason_codes))


def make_delivery_callback(
    resolve_context: Callable[[dict], TaskContext],
    evaluate_admission: Callable[[TaskContext], AdmissionProfile | None], *,
    accepted_restrictions: frozenset[str] = frozenset(),
    confirmation_factory=None,
):
    """Create a Humble consider_delivery_requests pickup/dropoff callback.

    The fleet callback has no selected robot ID. The deployment resolver must
    provide a valid actor scope (e.g. a single-robot fleet), place and space.
    Evaluate admission afresh on every call. An injected confirmation factory
    is a unit-test seam, not proof that an RMF runtime executed the callback.
    """
    if confirmation_factory is None:
        from rmf_adapter.fleet_update_handle import Confirmation
        confirmation_factory = Confirmation
    accepted_restrictions = frozenset(accepted_restrictions)

    def consider(description):
        confirmation = confirmation_factory()
        try:
            context = resolve_context(deepcopy(description))
            decision = map_profile(evaluate_admission(context), context,
                                   accepted_restrictions=accepted_restrictions)
        except Exception:
            confirmation.set_errors(["spp_admission_unavailable"])
            return confirmation
        if decision.task_allowed:
            confirmation.accept()
        else:
            confirmation.set_errors(list(decision.reasons))
        return confirmation

    return consider
