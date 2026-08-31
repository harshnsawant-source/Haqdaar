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


def test_no_partner_name_carries_a_piece_of_its_address():
    """The defect this test exists for.

    Several rows in the published PDFs write the name and the address with nothing
    between them, so the first-comma cut landed inside the address and the corpus
    shipped "Bank of Maharashtra Head office 'Lok mangal' 1501" and "UP Sahkari Gram
    Vikas Bank Ltd. 10". Nothing failed; a judge reading the partner list would simply
    have seen it.

    A house number is what leaked every time, so a digit in a name is the signal. No
    partner in any of the seven published lists legitimately has one. If a future list
    adds a bank that does, this fails loudly and the name can be allowed here, which is
    the right way round: the corpus is ninety rows and a person can look.
    """
    import re

    offenders = [p.name for p in load_partners(PARTNERS) if re.search(r"\d", p.name)]
    assert not offenders, offenders


def test_a_partner_with_an_address_is_placed_in_a_state():
    """A partner nobody can be shown is a partner we do not have.

    Ten of eighty-nine were unreachable, not because the source withheld the state but
    because the extractor would not read it off a printed postal address. The two that
    remain are the Small Finance Banks, whose list is two bank names and nothing else.
    """
    unplaced = [p for p in load_partners(PARTNERS) if not p.state]
    assert all(not p.address for p in unplaced), [p.name for p in unplaced if p.address]
    assert len(unplaced) == 2, [p.name for p in unplaced]


def test_the_hand_corrections_are_actually_in_the_corpus():
    """corrections.yaml is only worth having if re-running the extractor honours it.

    The corrected values live in two places by necessity: the correction file a person
    edits, and the generated YAML the router reads. This is what keeps them the same
    file's worth of truth, so a re-run without the corrections cannot quietly restore
    the defects.
    """
    import yaml

    data = yaml.safe_load(open(f"{PARTNERS}/corrections.yaml", encoding="utf-8"))
    corrections = data["corrections"]
    assert corrections, "corrections.yaml lists none"

    partners = load_partners(PARTNERS)
    for correction in corrections:
        in_category = [p for p in partners if p.category == correction["category"]]
        for field in ("name", "state"):
            if field in correction:
                assert any(
                    getattr(p, field) == correction[field] for p in in_category
                ), f"{correction['category']} #{correction['serial']}: {field} not applied"


def test_every_published_list_can_be_reached():
    """A category held in the corpus but absent from the routing rules is invisible.

    NBFC-MFIs were exactly that: seven partners loaded, counted in every total, and
    shown to nobody, because the category was left out of `also_categories` with no
    source behind the omission. NSFDC publishes that list from the same directory as
    the bank lists that were already routed.
    """
    from haqdaar.partners.router import load_routing

    routing = load_routing(PARTNERS)
    reachable = set(routing["also_categories"])
    for rule in routing["rules"]:
        reachable |= set(rule["primary_categories"])

    held = {p.category for p in load_partners(PARTNERS)}
    assert held <= reachable, {"held but unreachable": held - reachable}
