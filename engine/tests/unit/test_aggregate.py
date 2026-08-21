"""The unlock aggregator, and the overclaim it exists to prevent."""

from _helpers import predicate, verdict

from haqdaar.corpus.schema import Satisfy
from haqdaar.eligibility.aggregate import aggregate_unlocks, best_unlock
from haqdaar.eligibility.verdict import Evaluation, GroupResult, Status


def blocked(scheme_id: str, docs: list[str]):
    return verdict(
        [predicate("C", "g", Evaluation.UNKNOWN, verifiable_from=docs)],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.UNKNOWN)],
        Status.BLOCKED_ON_DOCUMENT,
        scheme_id=scheme_id,
        unlocking_docs=docs,
    )


def test_one_document_unlocking_several_schemes():
    options = aggregate_unlocks(
        [blocked("a", ["caste"]), blocked("b", ["caste"]), blocked("c", ["bpl"])]
    )
    assert [(o.document_id, o.unlock_count) for o in options] == [("caste", 2), ("bpl", 1)]
    assert options[0].unlocks == ["a", "b"]
    assert best_unlock([blocked("a", ["caste"]), blocked("b", ["caste"])]).unlocks == [
        "a",
        "b",
    ]


def test_a_document_that_is_one_of_several_blockers_unlocks_nothing():
    """The honesty case.

    Scheme 'a' needs both papers. Fetching the caste certificate alone resolves
    nothing, so promising "one document unlocks 1 more" would send someone across a
    district for a result that does not change.
    """
    options = aggregate_unlocks([blocked("a", ["caste", "income"])])
    assert [o.document_id for o in options] == ["caste", "income"]
    assert all(o.unlocks == [] for o in options)
    assert all(o.contributes_to == ["a"] for o in options)
    assert best_unlock([blocked("a", ["caste", "income"])]) is None


def test_sole_blocker_and_contributor_counted_separately():
    options = aggregate_unlocks([blocked("a", ["caste"]), blocked("b", ["caste", "bpl"])])
    caste = next(o for o in options if o.document_id == "caste")
    assert caste.unlocks == ["a"]
    assert caste.contributes_to == ["b"]
    assert caste.unlock_count == 1


def test_only_blocked_verdicts_count():
    """An UNVERIFIABLE scheme is not waiting on paperwork."""
    unverifiable = verdict(
        [predicate("SECC", "g", Evaluation.UNKNOWN)],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.UNKNOWN)],
        Status.UNVERIFIABLE,
        scheme_id="u",
    )
    eligible = verdict(
        [predicate("C", "g", Evaluation.TRUE, verifiable_from=["aadhaar"])],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.TRUE)],
        Status.ELIGIBLE,
        scheme_id="e",
    )
    assert aggregate_unlocks([unverifiable, eligible]) == []


def test_ranking_is_stable():
    """Ties break alphabetically so the stage order never shuffles between runs."""
    options = aggregate_unlocks([blocked("a", ["zeta"]), blocked("b", ["alpha"])])
    assert [o.document_id for o in options] == ["alpha", "zeta"]


def test_subsumed_schemes_do_not_inflate_the_count():
    absorbed = blocked("b", ["caste"]).model_copy(
        update={"claimable": False, "subsumed_by_scheme": "a"}
    )
    options = aggregate_unlocks([blocked("a", ["caste"]), absorbed])
    assert options[0].unlocks == ["a"]
