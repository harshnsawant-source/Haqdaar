"""The Channel Partner router, SIH26092's third component.

The problem statement's own account of the problem is that funds route through more
than a hundred Channel Partners and applicants cannot find the one "equipped to process
their specific loan category", so applications are misrouted and disbursement is
delayed. These tests pin the three things that make the answer honest.
"""

import pytest

from haqdaar.partners.router import (
    PartnersUnavailable,
    load_partners,
    route,
    states_covered,
)

PARTNERS = "corpus/partners"


def test_the_partner_corpus_loads_with_states():
    partners = load_partners(PARTNERS)
    assert len(partners) > 80
    assert len(states_covered(partners)) > 25
    # Every partner carries the list it came from, so a citizen can be told whether she
    # is being sent to a state agency or a bank.
    assert all(p.category and p.category_label for p in partners)
    assert all(p.source_url.startswith("https://nsfdc.nic.in") for p in partners)


def test_a_state_gets_its_own_channelising_agency():
    found = route(PARTNERS, "nsfdc-term-loan", "Maharashtra")
    assert found.primary, "Maharashtra should have at least one SCA"
    assert all(p.state == "Maharashtra" for p in found.primary)
    assert all(p.category == "SCA" for p in found.primary)


def test_no_partner_from_another_state_is_shown():
    """The bug this test exists for.

    The first version kept partners whose state could not be read, reasoning that
    absence of a state is not evidence of being elsewhere. True in the abstract, wrong
    on the screen: it put Uttar Pradesh Gramin Bank in front of someone who had said
    Maharashtra, which reads as a claim that it serves her.
    """
    found = route(PARTNERS, "nsfdc-term-loan", "Maharashtra")
    for partner in found.primary + found.also:
        assert partner.state == "Maharashtra", partner.name


def test_partners_we_could_not_place_are_counted_not_hidden():
    found = route(PARTNERS, "nsfdc-term-loan", "Kerala")
    assert found.unplaced > 0
    assert all(p.state == "Kerala" for p in found.primary + found.also)


def test_the_routing_rule_is_quoted():
    """A partner is named with the sentence that sends her there, like a verdict."""
    found = route(PARTNERS, "nsfdc-micro-finance", "Bihar")
    assert "SCAs/CAs" in found.quote
    assert found.source_url.startswith("https://nsfdc.nic.in")


def test_every_route_carries_the_refusal_to_rank():
    """Not an error field. It is present on every successful answer.

    SIH26092 asks for partners filtered so applications avoid those with high NPAs or
    overdues. NSFDC publishes no such figures, so the order carries no meaning and the
    response has to say that rather than let the order imply one.
    """
    found = route(PARTNERS, "nsfdc-term-loan", "Kerala")
    assert "does not publish" in found.cannot_rank
    assert "which to try first" in found.cannot_rank


def test_a_scheme_with_no_routing_rule_refuses_rather_than_listing_everyone():
    with pytest.raises(PartnersUnavailable) as caught:
        route(PARTNERS, "ignwps", "Maharashtra")
    assert "does not record who processes this scheme" in str(caught.value)


def test_without_a_state_it_returns_the_whole_network():
    found = route(PARTNERS, "nsfdc-term-loan", None)
    assert len(found.primary) > 30
    assert found.unplaced == 0


def test_the_evaluator_does_not_import_the_partner_router():
    import ast

    import haqdaar.eligibility.evaluate as evaluate

    tree = ast.parse(open(evaluate.__file__, encoding="utf-8").read())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any("partners" in name for name in imported), imported


def test_every_scheme_with_credit_terms_also_has_a_route():
    """The UI gates the partner panel on `lends`, and this is why that is safe.

    A scheme that lends but has no routing rule would render a panel that immediately
    refuses; a scheme with a route but no credit terms would never show one. Both come
    from the same NSFDC page today, so the sets match. If they ever diverge this fails
    rather than the divergence appearing on a citizen's screen.
    """
    from haqdaar.corpus.loader import load_corpus
    from haqdaar.partners.router import load_routing

    routed = {r["scheme_id"] for r in load_routing(PARTNERS)["rules"]}
    lending = {
        s.scheme_id
        for vertical in ("entrepreneur", "welfare", "student")
        for s in load_corpus(f"corpus/{vertical}/schemes")
        if s.credit_terms is not None
    }
    assert routed == lending, {"routed only": routed - lending, "lends only": lending - routed}
