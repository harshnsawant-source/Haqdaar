"""Route a citizen to the Channel Partner who can process her loan.

SIH26092's third component. The problem statement is explicit that this matters:
"direct loan applications are not entertained", funds route through "over 100 Channel
Partners", and applicants "face difficulties identifying and locating the nearest
authorized Channel Partner equipped to process their specific loan category". The cost
it names is misrouted applications and delayed disbursement.

So the router answers two questions and refuses a third.

  EQUIPPED TO PROCESS -> routing.yaml, which maps a scheme to partner categories and
  carries the sentence each rule came from.

  NEAREST -> by STATE, not by kilometres, and the API says which it used. The partner
  lists give postal addresses and no coordinates. Geocoding ninety addresses would mean
  an external service and an API key, which would end the two claims this product
  actually rests on: no keys, and it works with no network at a Panchayat. A state is
  what the citizen knows about herself anyway, and the State Channelising Agency is a
  state-level body, so state IS the right grain for the primary route.

  RANKED BY FUND AVAILABILITY -> refused. The problem statement asks for partners
  filtered so applications are not sent to those "with high NPAs or overdues". NSFDC
  publishes no fund-utilisation or NPA figures. Ordering the list anyway would look
  exactly like an ordering that meant something, so the order is fixed and the refusal
  is returned as data for the UI to show.

Nothing here is imported by the evaluator, and no verdict depends on it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class PartnersUnavailable(Exception):
    """Raised when the partner corpus cannot answer, with a readable reason."""


@dataclass(frozen=True)
class Partner:
    name: str
    address: str | None
    state: str | None
    category: str
    category_label: str
    source_url: str


@dataclass(frozen=True)
class Route:
    """Where one scheme is filed, for one state."""

    scheme_id: str
    state: str | None
    #: The partner type the scheme itself names. For NSFDC credit that is the State
    #: Channelising Agency, which is one or two bodies per state.
    primary: list[Partner] = field(default_factory=list)
    #: Banks and other Channelising Agencies that also take NSFDC applications and
    #: happen to sit in her state. Secondary because the scheme page names the SCA.
    also: list[Partner] = field(default_factory=list)
    #: Verbatim wording behind the primary routing rule.
    quote: str = ""
    also_quote: str = ""
    source_url: str = ""
    #: Partners we hold whose state the source did not make readable. Reported rather
    #: than folded into the list, because a partner of unknown location shown under
    #: "Maharashtra" is a claim we cannot support.
    unplaced: int = 0
    #: Present always. The UI must show it whenever it shows a partner.
    cannot_rank: str = (
        "These are listed in a fixed order, not a recommended one. NSFDC does not "
        "publish which partners currently have funds or a clean repayment record, so "
        "this cannot tell you which to try first."
    )


def _read(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise PartnersUnavailable(f"cannot read {path.name}: {exc}") from exc


def load_partners(directory: str | Path) -> list[Partner]:
    """Every partner in every list, with its category attached."""
    directory = Path(directory)
    if not directory.is_dir():
        raise PartnersUnavailable(f"{directory}: not a directory")

    partners: list[Partner] = []
    for path in sorted(directory.glob("*.yaml")):
        if path.name == "routing.yaml":
            continue
        data = _read(path)
        category = data.get("category")
        if not category:
            continue
        for row in data.get("partners", []) or []:
            partners.append(
                Partner(
                    name=row["name"],
                    address=row.get("address"),
                    state=row.get("state"),
                    category=category,
                    category_label=data.get("label", category),
                    source_url=data.get("source_url", ""),
                )
            )
    return partners


def load_routing(directory: str | Path) -> dict:
    routing = _read(Path(directory) / "routing.yaml")
    if not routing.get("rules"):
        raise PartnersUnavailable("routing.yaml names no rules")
    return routing


def states_covered(partners: list[Partner]) -> list[str]:
    return sorted({p.state for p in partners if p.state})


def route(directory: str | Path, scheme_id: str, state: str | None) -> Route:
    """Partners for one scheme, narrowed to one state when given.

    A scheme with no routing rule raises rather than falling back to every partner in
    the country. "We do not know who processes this" is a different answer from "here
    is a list", and the citizen is owed the difference.
    """
    partners = load_partners(directory)
    routing = load_routing(directory)

    rule = next(
        (r for r in routing["rules"] if r.get("scheme_id") == scheme_id), None
    )
    if rule is None:
        raise PartnersUnavailable(
            "The corpus does not record who processes this scheme, so this cannot "
            "tell you where to take it."
        )

    primary_categories = set(rule.get("primary_categories") or [])
    also_categories = set(routing.get("also_categories") or [])

    def wanted(partner: Partner, categories: set[str]) -> bool:
        if partner.category not in categories:
            return False
        if state is None:
            return True
        # EXACT match, and an unknown state does NOT pass. The first version kept
        # partners whose state we could not read, on the reasoning that absence is not
        # evidence of elsewhere. That was wrong at the screen: it put Uttar Pradesh
        # Gramin Bank in front of a citizen who had said Maharashtra, which reads as a
        # claim that it serves her. They are counted instead.
        return partner.state == state

    primary = [p for p in partners if wanted(p, primary_categories)]
    also = [p for p in partners if wanted(p, also_categories)]

    unplaced = 0
    if state is not None:
        relevant = primary_categories | also_categories
        unplaced = sum(1 for p in partners if p.category in relevant and not p.state)

    return Route(
        scheme_id=scheme_id,
        state=state,
        primary=primary,
        also=also,
        unplaced=unplaced,
        quote=(rule.get("quote") or "").strip(),
        also_quote=(routing.get("also_quote") or "").strip(),
        source_url=routing.get("source_url", ""),
    )
