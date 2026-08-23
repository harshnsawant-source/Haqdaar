"""The unlock aggregator, and the overclaim it exists to prevent."""

from _helpers import predicate, verdict

from haqdaar.corpus.schema import Satisfy
from haqdaar.eligibility.aggregate import aggregate_unlocks, best_unlock
from haqdaar.eligibility.verdict import Evaluation, GroupResult, Status


def blocked(scheme_id: str, docs: list[str]):
    """One unresolved clause that ANY of `docs` would evidence.

    Note what this models: a single rule with several acceptable proofs (age from an
    Aadhaar card OR an age certificate). Either document settles it. It is NOT two
    rules needing two different papers — see `blocked_on_two_clauses` for that.
    """
    return verdict(
        [predicate("C", "g", Evaluation.UNKNOWN, verifiable_from=docs)],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.UNKNOWN)],
        Status.BLOCKED_ON_DOCUMENT,
        scheme_id=scheme_id,
        unlocking_docs=docs,
    )


def blocked_on_two_clauses(scheme_id: str, first: str, second: str):
    """Two separate unresolved clauses in an ALL group, each needing its own paper.

    Neither document clears the scheme alone. This is the case the aggregator must
    never over-claim on.
    """
    return verdict(
        [
            predicate("C1", "g", Evaluation.UNKNOWN, verifiable_from=[first]),
            predicate("C2", "g", Evaluation.UNKNOWN, verifiable_from=[second]),
        ],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.UNKNOWN)],
        Status.BLOCKED_ON_DOCUMENT,
        scheme_id=scheme_id,
        unlocking_docs=[first, second],
    )


def blocked_on_either_of_two_clauses(scheme_id: str, first: str, second: str):
    """An ANY group — "income under the ceiling OR on the BPL list".

    EITHER document clears the scheme on its own, even though two are listed. This is
    the case the old sole-entry rule under-claimed on.
    """
    return verdict(
        [
            predicate("C1", "g", Evaluation.UNKNOWN, verifiable_from=[first]),
            predicate("C2", "g", Evaluation.UNKNOWN, verifiable_from=[second]),
        ],
        [GroupResult(group_id="g", satisfy=Satisfy.ANY, evaluation=Evaluation.UNKNOWN)],
        Status.BLOCKED_ON_DOCUMENT,
        scheme_id=scheme_id,
        unlocking_docs=[first, second],
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
    """The honesty case, and the one that must never over-claim.

    Scheme 'a' has TWO unresolved clauses in an ALL group, each needing its own paper.
    Fetching the caste certificate alone resolves nothing, so promising "one document
    unlocks 1 more" would send someone across a district for a result that does not
    change.
    """
    scheme = blocked_on_two_clauses("a", "caste", "income")
    options = aggregate_unlocks([scheme])
    assert [o.document_id for o in options] == ["caste", "income"]
    assert all(o.unlocks == [] for o in options)
    assert all(o.contributes_to == ["a"] for o in options)
    assert best_unlock([scheme]) is None


def test_an_any_group_is_cleared_by_either_document():
    """The under-claim this fix removes.

    "Income below the ceiling OR on the BPL list" is satisfied by either paper alone,
    so each is a real unlock even though two are listed. The old rule counted a
    document as unlocking only when it was the sole entry, and reported neither.
    """
    scheme = blocked_on_either_of_two_clauses("sgnay", "bpl", "income_certificate")
    options = {o.document_id: o for o in aggregate_unlocks([scheme])}

    assert options["bpl"].unlocks == ["sgnay"]
    assert options["income_certificate"].unlocks == ["sgnay"]
    assert all(o.contributes_to == [] for o in options.values())
    assert best_unlock([scheme]).unlocks == ["sgnay"]


def test_a_clause_with_two_acceptable_proofs_is_cleared_by_either():
    """One rule, several acceptable papers (age from Aadhaar OR an age certificate)."""
    scheme = blocked("a", ["aadhaar", "age_proof"])
    options = {o.document_id: o for o in aggregate_unlocks([scheme])}
    assert options["aadhaar"].unlocks == ["a"]
    assert options["age_proof"].unlocks == ["a"]


def test_a_partially_cleared_scheme_still_does_not_count_as_unlocked():
    """Three clauses, one paper. Progress is not an unlock."""
    scheme = verdict(
        [
            predicate("C1", "g", Evaluation.UNKNOWN, verifiable_from=["a_doc"]),
            predicate("C2", "g", Evaluation.UNKNOWN, verifiable_from=["b_doc"]),
            predicate("C3", "g", Evaluation.UNKNOWN, verifiable_from=["c_doc"]),
        ],
        [GroupResult(group_id="g", satisfy=Satisfy.ALL, evaluation=Evaluation.UNKNOWN)],
        Status.BLOCKED_ON_DOCUMENT,
        scheme_id="s",
        unlocking_docs=["a_doc", "b_doc", "c_doc"],
    )
    assert all(o.unlocks == [] for o in aggregate_unlocks([scheme]))
    assert best_unlock([scheme]) is None


def test_sole_blocker_and_contributor_counted_separately():
    """One caste certificate clears 'a' outright and only helps 'b'."""
    options = aggregate_unlocks(
        [blocked("a", ["caste"]), blocked_on_two_clauses("b", "caste", "bpl")]
    )
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
