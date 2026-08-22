"""T3 — nothing in the corpus answers this question.

The floor is biased to refuse: a query that is merely near the corpus resolves outside
it. A false refusal is on-brand; a false confident answer is disqualifying.
"""

import pytest

from haqdaar.corpus.loader import load_corpus
from haqdaar.guard.triggers import TriggerId, t3_no_retrieval_support
from haqdaar.retrieval.route import route


@pytest.fixture(scope="module")
def schemes(request):
    return load_corpus(
        request.config.rootpath.parent / "corpus" / "entrepreneur" / "schemes"
    )


@pytest.mark.parametrize(
    "query",
    [
        "How much tax do I owe this year?",
        "What is the weather tomorrow?",
        "Who won the match last night?",
        "Please write me a poem.",
        "",
    ],
)
def test_out_of_domain_queries_refuse(schemes, query):
    result = route(query, schemes)
    assert result.outside_corpus
    finding = t3_no_retrieval_support(result)
    assert finding is not None
    assert finding.trigger is TriggerId.T3_NO_RETRIEVAL_SUPPORT
    assert finding.clause_ids == []


@pytest.mark.parametrize(
    "query",
    [
        "Am I eligible for Stand-Up India?",
        "Tell me about the NSFDC term loan",
        "standup india greenfield enterprise loan",
    ],
)
def test_in_corpus_queries_route(schemes, query):
    result = route(query, schemes)
    assert not result.outside_corpus
    assert t3_no_retrieval_support(result) is None


def test_the_named_scheme_ranks_first(schemes):
    assert route("Stand-Up India", schemes).scheme_ids[0] == "stand-up-india"
    assert route("NSFDC term loan", schemes).scheme_ids[0] == "nsfdc-term-loan"


def test_an_empty_corpus_refuses_rather_than_crashing(schemes):
    """A corpus that failed to load must refuse, not raise mid-demo."""
    result = route("Stand-Up India", [])
    assert result.outside_corpus
    assert t3_no_retrieval_support(result) is not None


def test_a_barely_matching_query_refuses(schemes):
    """The margin at work: one incidental shared word is not a match.

    "loan" appears in both schemes, but a question about a car loan is not a question
    about either of them.
    """
    result = route(
        "I want to know about my car loan interest rate and my credit card bill "
        "and whether the weather affects my repayment schedule this month",
        schemes,
    )
    assert result.outside_corpus


def test_scores_are_deterministic_and_ordered(schemes):
    first = route("Stand-Up India greenfield", schemes)
    second = route("Stand-Up India greenfield", schemes)
    assert first == second
    assert [s.score for s in first.scores] == sorted(
        (s.score for s in first.scores), reverse=True
    )
