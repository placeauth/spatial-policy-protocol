from copy import deepcopy
from pathlib import Path
import runpy
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/admission/src"))
from spp_admission.models import AdmissionProfile, EvidenceBinding
from spp_admission.open_rmf import TaskContext, make_delivery_callback, map_profile

CONTEXT = TaskContext("robot:1", "clinic", "clinic/wing")


def profile(status="ADMITTED"):
    return AdmissionProfile(status, CONTEXT.actor_id, CONTEXT.place, CONTEXT.space, 1,
                            "sha256:evidence", EvidenceBinding("robot:1", "b", "c", "p", "e", "plan"))


def test_admitted():
    assert map_profile(profile(), CONTEXT).task_allowed


def test_degraded_requires_explicit_acceptance_and_preserves_both_restriction_lists():
    p = profile("DEGRADED")
    p.restrictions = ["staff_assistance"]
    p.operating_profile["restrictions"] = ["video_disabled"]
    assert not map_profile(p, CONTEXT).task_allowed
    result = map_profile(p, CONTEXT, accepted_restrictions=frozenset({"staff_assistance", "video_disabled"}))
    assert result.task_allowed
    assert result.restrictions == ("staff_assistance", "video_disabled")


def test_denied():
    assert not map_profile(profile("DENIED"), CONTEXT).task_allowed


def test_missing():
    assert map_profile(None, CONTEXT).reasons == ("missing_profile",)


@pytest.mark.parametrize("bad", [{}, profile("UNKNOWN"), profile("DEGRADED")])
def test_invalid(bad):
    assert not map_profile(bad, CONTEXT).task_allowed


def test_wrong_destination_or_actor():
    for context in (TaskContext("other", "clinic", "clinic/wing"),
                    TaskContext("robot:1", "clinic", "clinic/restricted")):
        assert not map_profile(profile(), context).task_allowed


def test_deterministic_no_mutation():
    p = profile()
    before = deepcopy(p)
    assert map_profile(p, CONTEXT) == map_profile(p, CONTEXT)
    assert p == before


def test_callback_contract_and_lookup_failure():
    # Test double for the documented Python Confirmation interface, NOT RMF.
    class Confirmation:
        def __init__(self):
            self.accepted = False
            self.errors = []

        def accept(self):
            self.accepted = True

        def set_errors(self, errors):
            self.errors = errors

    descriptions = []
    current = profile()

    def resolve(description):
        descriptions.append(description)
        return CONTEXT

    callback = make_delivery_callback(resolve, lambda _: current,
                                      confirmation_factory=Confirmation)
    assert callback({"place": "wing"}).accepted
    current.status = "DENIED"
    assert not callback({"place": "wing"}).accepted
    assert len(descriptions) == 2  # Admission is looked up for each request.
    broken = make_delivery_callback(lambda _: 1 / 0, lambda _: current,
                                    confirmation_factory=Confirmation)
    assert broken({}).errors == ["spp_admission_unavailable"]


def test_demo_uses_evidence_backed_profiles():
    results = runpy.run_path(str(ROOT / "demo/open_rmf/run_demo.py"))["run"]()
    assert [status for _, status, _ in results] == ["ADMITTED", "DENIED", "DEGRADED"]
    assert [decision.task_allowed for _, _, decision in results] == [True, False, True]
