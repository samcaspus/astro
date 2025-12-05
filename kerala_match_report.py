#!/usr/bin/env python3
"""
Kerala-style Marriage Matching Script with:
- Porutham (Dina, Gana, Yoni, Rasi, Rasi Adhipathi, Stree Dheergha, Vasya, Mahendra, Rajju, Vedha)
- Papasamya & Manglik
- Individual analysis for each person:
    * Career potential
    * Wealth potential
    * Overall life & growth

Uses:
- Rasi planets_from_lagna
- Navamsa navamsa_planets_from_lagna
- current_dasha string

Usage:
    python kerala_match_report.py match_input.json
"""

import json
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Tuple


# -------------------------
# Data structures
# -------------------------

@dataclass
class PersonChart:
    name: str
    dob: str
    tob: str
    place: str
    rasi: str
    nakshatra: str
    nakshatra_pada: int
    lagna: str
    current_dasha: str
    planets_from_lagna: Dict[str, int]            # Rasi
    navamsa_planets_from_lagna: Dict[str, int]    # Navamsa (D9)


@dataclass
class PapasamyaResult:
    girl_total: int
    boy_total: int
    difference: int
    verdict: str


@dataclass
class ManglikResult:
    girl_manglik: bool
    boy_manglik: bool
    combined_verdict: str


@dataclass
class PoruthamResult:
    name: str
    status: str          # e.g., "Good", "Average", "Neutral", "Bad", "Safe"
    comment: str = ""    # short summary: what this check means + result
    detail: str = ""     # pair-specific reasoning
    logic: str = ""      # long explanation for modal


@dataclass
class OverallMatchResult:
    papasamya: PapasamyaResult
    manglik: ManglikResult
    poruthams: List[PoruthamResult]
    final_comment: str
    score_estimate: float


# -------------------------
# Core constants
# -------------------------

MALEFIC_PLANETS = ["Mars", "Saturn", "Sun", "Rahu", "Ketu"]
BENEFIC_PLANETS = ["Jupiter", "Venus", "Mercury", "Moon"]

PAPAM_HOUSES = {1, 2, 4, 7, 8, 12}  # Houses counted as papam from each reference

# 27 nakshatra order (canonical)
NAK_ORDER = [
    "ashwini",
    "bharani",
    "krittika",
    "rohini",
    "mrigasira",
    "ardra",
    "punarvasu",
    "pushya",
    "ashlesha",
    "magha",
    "purvaphalguni",
    "uttaraphalguni",
    "hasta",
    "chitra",
    "swati",
    "vishakha",
    "anuradha",
    "jyeshta",
    "moola",
    "purvashadha",
    "uttarashadha",
    "shravana",
    "dhanishta",
    "satabhisha",
    "purvabhadra",
    "uttarabhadrapada",
    "revati",
]


def norm_nak_name(name: str) -> str:
    """Normalize nakshatra name to a compact key: letters only, lowercase."""
    return "".join(ch.lower() for ch in name if ch.isalpha())


def get_nak_index(nakshatra: str) -> int:
    """
    Return 1..27 index of nakshatra in NAK_ORDER using normalized name.
    Raises ValueError if not found.
    """
    key = norm_nak_name(nakshatra)
    if key not in NAK_ORDER:
        raise ValueError(f"Nakshatra '{nakshatra}' not recognized (normalized='{key}').")
    return NAK_ORDER.index(key) + 1  # 1..27


# -------------------------
# House helpers
# -------------------------

def derive_positions_from_reference(
    planets_from_lagna: Dict[str, int], reference_planet: str
) -> Dict[str, int]:
    """
    Given houses from Lagna (1–12) and a reference planet (Moon or Venus),
    compute houses from that reference:

        house_from_ref(P) = ((house_from_lagna(P) - house_from_lagna(ref)) % 12) + 1
    """
    if reference_planet not in planets_from_lagna:
        raise ValueError(f"{reference_planet} not found in planets_from_lagna")

    ref_house = planets_from_lagna[reference_planet]
    result: Dict[str, int] = {}

    for planet, h_lagna in planets_from_lagna.items():
        result[planet] = ((h_lagna - ref_house) % 12) + 1  # 1..12

    return result


def planets_in_house(planets_map: Dict[str, int], house: int) -> List[str]:
    """Return list of planets in the given house."""
    return [p for p, h in planets_map.items() if h == house]


def list_str(planets: List[str]) -> str:
    return ", ".join(planets) if planets else "none"


# -------------------------
# Papasamya
# -------------------------

def compute_papasamya_for_person(person: PersonChart) -> int:
    """
    Kerala-style papasamya:
    For each of Mars, Saturn, Sun, Rahu:
        - If from Lagna / Moon / Venus the planet is in 1,2,4,7,8,12 -> 1 point.
    Houses from Moon and Venus are derived from Lagna placements.
    """
    total = 0
    lagna_map = person.planets_from_lagna
    moon_map = derive_positions_from_reference(lagna_map, "Moon")
    venus_map = derive_positions_from_reference(lagna_map, "Venus")

    for planet in ["Mars", "Saturn", "Sun", "Rahu"]:
        # From Lagna
        h_lagna = lagna_map.get(planet)
        if h_lagna in PAPAM_HOUSES:
            total += 1

        # From Moon
        h_moon = moon_map.get(planet)
        if h_moon in PAPAM_HOUSES:
            total += 1

        # From Venus
        h_venus = venus_map.get(planet)
        if h_venus in PAPAM_HOUSES:
            total += 1

    return total


def papasamya_match(girl: PersonChart, boy: PersonChart) -> PapasamyaResult:
    girl_total = compute_papasamya_for_person(girl)
    boy_total = compute_papasamya_for_person(boy)
    diff = abs(girl_total - boy_total)

    if diff == 0:
        verdict = "Excellent (Thulya Papam – perfectly balanced)"
    elif diff <= 2:
        verdict = "Acceptable (within Kerala limit)"
    else:
        verdict = "Not acceptable (Papasamya difference too high)"

    return PapasamyaResult(
        girl_total=girl_total,
        boy_total=boy_total,
        difference=diff,
        verdict=verdict,
    )


# -------------------------
# Manglik (Kuja dosha)
# -------------------------

def is_manglik_from_lagna(house: int) -> bool:
    """Typical Kuja dosha houses from Lagna."""
    return house in {1, 2, 4, 7, 8, 12}


def compute_manglik(person: PersonChart) -> bool:
    """
    Basic Kuja dosha check:
        If Mars from Lagna is in 1,2,4,7,8,12 -> Manglik.
    """
    mars_house_from_lagna = person.planets_from_lagna.get("Mars")
    return bool(mars_house_from_lagna and is_manglik_from_lagna(mars_house_from_lagna))


def manglik_match(girl: PersonChart, boy: PersonChart) -> ManglikResult:
    girl_m = compute_manglik(girl)
    boy_m = compute_manglik(boy)

    if girl_m and boy_m:
        combined = (
            "Kuja dosha check: both charts have Manglik-type placement, "
            "so the dosha is balanced/cancelled in Kerala logic."
        )
    elif girl_m and not boy_m:
        combined = (
            "Kuja dosha check: girl has Manglik placement, boy does not. "
            "Needs more detailed individual analysis or remedial handling."
        )
    elif not girl_m and boy_m:
        combined = (
            "Kuja dosha check: boy has Manglik placement, girl does not. "
            "Needs more detailed individual analysis or remedial handling."
        )
    else:
        combined = "Kuja dosha check: neither chart is Manglik – no Kuja dosha issue."

    return ManglikResult(
        girl_manglik=girl_m,
        boy_manglik=boy_m,
        combined_verdict=combined,
    )


# -------------------------
# YONI DATA & LOGIC
# -------------------------

# Map each nakshatra to (yoni_key, yoni_sanskrit, animal_english, inimical_yoni_key)
YONI_BY_NAK: Dict[str, Tuple[str, str, str, str]] = {
    # Horse (Ashwa) – enemy Buffalo (Mahish)
    "ashwini": ("ashwa", "Ashwa", "Horse", "mahish"),
    "satabhisha": ("ashwa", "Ashwa", "Horse", "mahish"),
    "shatataraka": ("ashwa", "Ashwa", "Horse", "mahish"),

    # Elephant (Gaja) – enemy Lion (Simha)
    "bharani": ("gaja", "Gaja", "Elephant", "simha"),
    "revati": ("gaja", "Gaja", "Elephant", "simha"),

    # Sheep/Goat (Mesha) – enemy Monkey (Vanar)
    "krittika": ("mesha", "Mesha", "Sheep/Goat", "vanar"),
    "pushya": ("mesha", "Mesha", "Sheep/Goat", "vanar"),
    "pushyami": ("mesha", "Mesha", "Sheep/Goat", "vanar"),

    # Serpent (Sarpa) – enemy Mongoose (Nakul)
    "rohini": ("sarpa", "Sarpa", "Serpent", "nakul"),
    "mrigasira": ("sarpa", "Sarpa", "Serpent", "nakul"),
    "mrigashirsha": ("sarpa", "Sarpa", "Serpent", "nakul"),

    # Dog (Shwan) – enemy Deer (Mriga)
    "moola": ("shwan", "Shwan", "Dog", "mriga"),
    "mula": ("shwan", "Shwan", "Dog", "mriga"),
    "ardra": ("shwan", "Shwan", "Dog", "mriga"),

    # Cat (Marjar) – enemy Rat (Mushak)
    "ashlesha": ("marjar", "Marjar", "Cat", "mushak"),
    "aslesha": ("marjar", "Marjar", "Cat", "mushak"),
    "punarvasu": ("marjar", "Marjar", "Cat", "mushak"),

    # Rat (Mushak) – enemy Cat (Marjar)
    "magha": ("mushak", "Mushak", "Rat", "marjar"),
    "purvaphalguni": ("mushak", "Mushak", "Rat", "marjar"),

    # Cow (Go) – enemy Tiger (Vyaghra)
    "uttaraphalguni": ("go", "Go", "Cow", "vyaghra"),
    "uttarabhadrapada": ("go", "Go", "Cow", "vyaghra"),

    # Buffalo (Mahish) – enemy Horse (Ashwa)
    "swati": ("mahish", "Mahish", "Buffalo", "ashwa"),
    "hasta": ("mahish", "Mahish", "Buffalo", "ashwa"),

    # Tiger (Vyaghra) – enemy Cow (Go)
    "vishakha": ("vyaghra", "Vyaghra", "Tiger", "go"),
    "visakha": ("vyaghra", "Vyaghra", "Tiger", "go"),
    "chitra": ("vyaghra", "Vyaghra", "Tiger", "go"),

    # Deer (Mriga) – enemy Dog (Shwan)
    "jyeshta": ("mriga", "Mriga", "Deer", "shwan"),
    "jyestha": ("mriga", "Mriga", "Deer", "shwan"),
    "anuradha": ("mriga", "Mriga", "Deer", "shwan"),

    # Monkey (Vanar) – enemy Sheep/Goat (Mesha)
    "purvashadha": ("vanar", "Vanar", "Monkey", "mesha"),
    "purvashada": ("vanar", "Vanar", "Monkey", "mesha"),
    "shravana": ("vanar", "Vanar", "Monkey", "mesha"),

    # Lion (Simha) – enemy Elephant (Gaja)
    "purvabhadra": ("simha", "Simha", "Lion", "gaja"),
    "purvabhadrapada": ("simha", "Simha", "Lion", "gaja"),
    "dhanishta": ("simha", "Simha", "Lion", "gaja"),

    # Mongoose (Nakul) – enemy Serpent (Sarpa)
    "uttarashadha": ("nakul", "Nakul", "Mongoose", "sarpa"),
    "uttarashada": ("nakul", "Nakul", "Mongoose", "sarpa"),
    "abhijit": ("nakul", "Nakul", "Mongoose", "sarpa"),
}

YONI_META = {
    "ashwa": ("Ashwa", "Horse", "Mahish (Buffalo)"),
    "gaja": ("Gaja", "Elephant", "Simha (Lion)"),
    "mesha": ("Mesha", "Sheep/Goat", "Vanar (Monkey)"),
    "sarpa": ("Sarpa", "Serpent", "Nakul (Mongoose)"),
    "shwan": ("Shwan", "Dog", "Mriga (Deer)"),
    "marjar": ("Marjar", "Cat", "Mushak (Rat)"),
    "mushak": ("Mushak", "Rat", "Marjar (Cat)"),
    "go": ("Go", "Cow", "Vyaghra (Tiger)"),
    "mahish": ("Mahish", "Buffalo", "Ashwa (Horse)"),
    "vyaghra": ("Vyaghra", "Tiger", "Go (Cow)"),
    "mriga": ("Mriga", "Deer", "Shwan (Dog)"),
    "vanar": ("Vanar", "Monkey", "Mesha (Sheep/Goat)"),
    "simha": ("Simha", "Lion", "Gaja (Elephant)"),
    "nakul": ("Nakul", "Mongoose", "Sarpa (Serpent)"),
}


def get_yoni_info(nakshatra: str):
    key = norm_nak_name(nakshatra)
    return YONI_BY_NAK.get(key)


def build_yoni_table_text() -> str:
    lines = ["Yoni table (Yoni → Animal → Inimical Yoni):"]
    for key, (san, animal, enemy) in YONI_META.items():
        lines.append(f"• {san} ({animal}) → enemy: {enemy}")
    return "\n".join(lines)


def compute_yoni_porutham(girl: PersonChart, boy: PersonChart) -> PoruthamResult:
    g_info = get_yoni_info(girl.nakshatra)
    b_info = get_yoni_info(boy.nakshatra)

    if not g_info or not b_info:
        return PoruthamResult(
            name="Yoni",
            status="Unknown",
            comment="Yoni porutham shows instinctive/physical attraction and compatibility; here it could not be computed because one or both nakshatras are missing from the Yoni table.",
            detail=f"Girl nakshatra: {girl.nakshatra}, Boy nakshatra: {boy.nakshatra}",
            logic=(
                "Yoni porutham compares the animal symbols (yoni) of the birth stars.\n"
                "For full automation, each nakshatra must be mapped to a yoni animal.\n\n"
                + build_yoni_table_text()
            ),
        )

    g_key, g_sanskrit, g_animal, g_enemy_key = g_info
    b_key, b_sanskrit, b_animal, b_enemy_key = b_info

    if g_key == b_key:
        status = "Very Good"
        relation = "same"
        comment = (
            "Yoni porutham shows instinctive, emotional and physical compatibility. "
            "Here both stars share the same yoni, so attraction and basic instincts are very well aligned."
        )
    elif g_enemy_key == b_key or b_enemy_key == g_key:
        status = "Bad"
        relation = "enemy"
        comment = (
            "Yoni porutham shows instinctive, emotional and physical compatibility. "
            "This pair forms an inimical yoni combination, so there can be strong friction and clashes in instincts."
        )
    else:
        status = "Neutral"
        relation = "neutral"
        comment = (
            "Yoni porutham shows instinctive, emotional and physical compatibility. "
            "These yonis are neither the same nor classical enemies, so the result is neutral/average – "
            "no big problem and no extreme attraction purely from Yoni."
        )

    detail = (
        f"Girl nakshatra {girl.nakshatra} → {g_sanskrit} yoni ({g_animal}). "
        f"Boy nakshatra {boy.nakshatra} → {b_sanskrit} yoni ({b_animal}). "
        f"These yonis are {relation} to each other: "
        f"the enemy of {g_animal} is {g_enemy_key.capitalize()} yoni, "
        f"and the enemy of {b_animal} is {b_enemy_key.capitalize()} yoni, "
        "so this pair is not in the direct enemy list (like Rat–Cat or Cow–Tiger)."
    )

    yoni_table = build_yoni_table_text()

    logic = (
        "HOW YONI PORUTHAM IS CALCULATED\n"
        "--------------------------------\n"
        "1. Each nakshatra is assigned a 'yoni' (animal symbol).\n"
        "2. Each yoni has one specific inimical yoni (enemy pair).\n"
        "3. For compatibility:\n"
        "   • Same yoni → Very Good\n"
        "   • Inimical pair (one is the enemy of the other) → Bad\n"
        "   • All other combinations → Neutral/Average\n\n"
        f"In this match:\n"
        f"• Girl nakshatra = {girl.nakshatra}\n"
        f"  → Yoni = {g_sanskrit} ({g_animal}), enemy yoni = {g_enemy_key.capitalize()}.\n"
        f"• Boy nakshatra = {boy.nakshatra}\n"
        f"  → Yoni = {b_sanskrit} ({b_animal}), enemy yoni = {b_enemy_key.capitalize()}.\n\n"
        "Decision:\n"
        f"• Are they same yoni?  { 'Yes' if g_key == b_key else 'No' }\n"
        f"• Is girl's yoni enemy of boy's?  { 'Yes' if g_enemy_key == b_key else 'No' }\n"
        f"• Is boy's yoni enemy of girl's?  { 'Yes' if b_enemy_key == g_key else 'No' }\n"
        "→ Therefore this pair is classified as: "
        f"{status.upper()}.\n\n"
        "Gender note:\n"
        "Classical texts sometimes discuss male vs female yoni, but for match compatibility, "
        "the enemy/friend logic is symmetric – Rat vs Cat is considered hostile regardless of "
        "which one is male/female. This script uses that symmetric rule.\n\n"
        + yoni_table
    )

    return PoruthamResult(
        name="Yoni",
        status=status,
        comment=comment,
        detail=detail,
        logic=logic,
    )


# -------------------------
# GANA DATA & LOGIC (Kerala-style)
# -------------------------

# Each nakshatra → one of: Deva, Manushya, Rakshasa
GANA_BY_NAK: Dict[str, str] = {
    # Deva
    "ashwini": "Deva",
    "mrigasira": "Deva",
    "mrigashirsha": "Deva",
    "punarvasu": "Deva",
    "pushya": "Deva",
    "pushyami": "Deva",
    "hasta": "Deva",
    "swati": "Deva",
    "anuradha": "Deva",
    "shravana": "Deva",
    "sravana": "Deva",
    "revati": "Deva",

    # Manushya (Nara)
    "bharani": "Manushya",
    "rohini": "Manushya",
    "ardra": "Manushya",
    "arudra": "Manushya",
    "purvaphalguni": "Manushya",
    "purva_phalguni": "Manushya",
    "uttaraphalguni": "Manushya",
    "uttara_phalguni": "Manushya",
    "purvashadha": "Manushya",
    "purvashada": "Manushya",
    "uttarashadha": "Manushya",
    "uttarashada": "Manushya",
    "purvabhadra": "Manushya",
    "purvabhadrapada": "Manushya",
    "uttarabhadrapada": "Manushya",

    # Rakshasa
    "krittika": "Rakshasa",
    "kritika": "Rakshasa",
    "ashlesha": "Rakshasa",
    "aslesha": "Rakshasa",
    "magha": "Rakshasa",
    "chitra": "Rakshasa",
    "vishakha": "Rakshasa",
    "visakha": "Rakshasa",
    "jyeshta": "Rakshasa",
    "jyestha": "Rakshasa",
    "moola": "Rakshasa",
    "mula": "Rakshasa",
    "dhanishta": "Rakshasa",
    "satabhisha": "Rakshasa",
    "shatataraka": "Rakshasa",
}

# For Kerala-style rule: higher gana rank for the male is considered acceptable;
# woman having higher gana than man is considered a mismatch.
GANA_RANK = {
    "Deva": 1,
    "Manushya": 2,
    "Rakshasa": 3,
}


def get_gana(nakshatra: str) -> str | None:
    """Return 'Deva' / 'Manushya' / 'Rakshasa' for the nakshatra, or None if unknown."""
    key = norm_nak_name(nakshatra)
    return GANA_BY_NAK.get(key)


def compute_gana_porutham(girl: PersonChart, boy: PersonChart) -> PoruthamResult:
    """
    Kerala-style Gana porutham.

    Logic:
      1) Each nakshatra belongs to Deva, Manushya, or Rakshasa.
      2) Assign rank: Deva=1 < Manushya=2 < Rakshasa=3.
      3) For marriage, tradition prefers that the boy's gana rank
         is >= girl's gana rank.
         - If same gana: Very Good.
         - If boy_rank > girl_rank: Good (heavier temperament on male side is acceptable).
         - If girl_rank > boy_rank: Bad (Kerala astrologers usually dislike this).
    """

    g_gana = get_gana(girl.nakshatra)
    b_gana = get_gana(boy.nakshatra)

    if not g_gana or not b_gana:
        detail = (
            f"Girl nakshatra: {girl.nakshatra} → Gana: {g_gana or 'Unknown'}; "
            f"Boy nakshatra: {boy.nakshatra} → Gana: {b_gana or 'Unknown'}."
        )
        logic = (
            "Gana porutham needs each nakshatra to be classified into Deva, "
            "Manushya, or Rakshasa. At least one of the stars could not be "
            "mapped in the internal table, so result is marked Unknown.\n\n"
            "If you follow a different gana table, update GANA_BY_NAK accordingly."
        )
        return PoruthamResult(
            name="Gana",
            status="Unknown",
            comment=(
                "Gana porutham compares basic temperament groups (Deva, Manushya, Rakshasa); "
                "here it could not be computed fully from the internal gana table."
            ),
            detail=detail,
            logic=logic,
        )

    # Gana compatibility matrix based on the chart
    # Format: (girl_gana, boy_gana) -> (status, description)
    compatibility_map = {
        ("Deva", "Deva"): ("Excellent", "excellent match"),
        ("Deva", "Manushya"): ("Good", "good match"),
        ("Deva", "Rakshasa"): ("Not Preferred", "not preferred"),
        
        ("Manushya", "Deva"): ("Good", "good match"),
        ("Manushya", "Manushya"): ("Good", "good match"),
        ("Manushya", "Rakshasa"): ("Acceptable", "may be stressful, depends on other factors"),
        
        ("Rakshasa", "Deva"): ("Good", "good match"),
        ("Rakshasa", "Manushya"): ("OK", "acceptable match"),
        ("Rakshasa", "Rakshasa"): ("Acceptable", "acceptable match"),
    }
    
    status, description = compatibility_map[(g_gana, b_gana)]
    
    if status == "Excellent":
        comment = (
            f"Gana porutham: Girl's {g_gana} gana with Boy's {b_gana} gana is an {description}. "
            "This indicates excellent harmony and understanding between the couple."
        )
    elif status == "Good":
        comment = (
            f"Gana porutham: Girl's {g_gana} gana with Boy's {b_gana} gana is a {description}. "
            "This indicates good compatibility and harmony."
        )
    elif status == "OK":
        comment = (
            f"Gana porutham: Girl's {g_gana} gana with Boy's {b_gana} gana is an {description}. "
            "This is acceptable but may require understanding and adjustment."
        )
    elif status == "Acceptable":
        comment = (
            f"Gana porutham: Girl's {g_gana} gana with Boy's {b_gana} gana is an {description}. "
            "This combination is acceptable for marriage."
        )
    elif status == "Depends":
        comment = (
            f"Gana porutham: Girl's {g_gana} gana with Boy's {b_gana} gana {description}. "
            "This combination may work if other poruthams are strong."
        )
    else:  # "Not Preferred"
        comment = (
            f"Gana porutham: Girl's {g_gana} gana with Boy's {b_gana} gana is {description}. "
            "This combination may lead to temperamental differences and is generally not recommended."
        )

    detail = (
        f"Girl nakshatra {girl.nakshatra} → {g_gana} gana.\n"
        f"Boy nakshatra {boy.nakshatra} → {b_gana} gana.\n"
        f"Compatibility: {status} (based on Gana compatibility chart)."
    )

    logic = (
        "HOW GANA PORUTHAM IS CHECKED\n"
        "----------------------------\n"
        "1) Each nakshatra is assigned one of three ganas:\n"
        "   • Deva      – softer, sattvic temperament\n"
        "   • Manushya  – mixed, human temperament\n"
        "   • Rakshasa  – intense, rajasic/tamasic temperament\n\n"
        "2) Compatibility is determined by the combination:\n\n"
        "   GANA COMPATIBILITY CHART (Girl ↓ \\ Boy →):\n"
        "   ┌──────────────┬────────────┬──────────────┬────────────┐\n"
        "   │              │  Deva Boy  │ Manushya Boy │Rakshasa Boy│\n"
        "   ├──────────────┼────────────┼──────────────┼────────────┤\n"
        "   │ Deva Girl    │ Excellent  │     Good     │Not Preferred│\n"
        "   │ Manushya Girl│    Good    │     Good     │  Depends   │\n"
        "   │ Rakshasa Girl│    Good    │      OK      │ Acceptable │\n"
        "   └──────────────┴────────────┴──────────────┴────────────┘\n\n"
        "3) Status meanings:\n"
        "   • Excellent      - Best match, excellent harmony\n"
        "   • Good           - Good compatibility\n"
        "   • OK/Acceptable  - Acceptable, may need adjustment\n"
        "   • Depends        - May be stressful, needs strong other poruthams\n"
        "   • Not Preferred  - Not recommended\n\n"
        f"FOR THIS PAIR:\n"
        f"   • Girl: {girl.nakshatra} → {g_gana} gana\n"
        f"   • Boy:  {boy.nakshatra} → {b_gana} gana\n"
        f"   • Compatibility: {status}\n\n"
        "This matching is based on traditional Gana porutham rules where\n"
        "compatibility depends on the specific combination of ganas."
    )

    return PoruthamResult(
        name="Gana",
        status=status,
        comment=comment,
        detail=detail,
        logic=logic,
    )


# -------------------------
# RASI / LORDSHIP / FRIENDSHIP DATA
# -------------------------

RASI_CANON = [
    "mesha", "vrishabha", "mithuna", "karka", "simha", "kanya",
    "tula", "vrischika", "dhanu", "makara", "kumbha", "meena",
]

def norm_rasi_name(name: str) -> str:
    """
    Normalize rasi name to a canonical key (mesha..meena).
    Accepts English sign names too (Aries..Pisces).
    """
    key = "".join(ch.lower() for ch in name if ch.isalpha())

    aliases = {
        "aries": "mesha",
        "taurus": "vrishabha",
        "gemini": "mithuna",
        "cancer": "karka",
        "leo": "simha",
        "virgo": "kanya",
        "libra": "tula",
        "scorpio": "vrischika",
        "sagittarius": "dhanu",
        "capricorn": "makara",
        "aquarius": "kumbha",
        "pisces": "meena",
        "thula": "tula",
        "vrischikam": "vrischika",
    }

    if key in RASI_CANON:
        return key
    return aliases.get(key, key)


RASI_INDEX = {name: i + 1 for i, name in enumerate(RASI_CANON)}  # 1..12

RASI_LORD = {
    "mesha": "Mars",
    "vrishabha": "Venus",
    "mithuna": "Mercury",
    "karka": "Moon",
    "simha": "Sun",
    "kanya": "Mercury",
    "tula": "Venus",
    "vrischika": "Mars",   # (ignoring Ketu co-lord)
    "dhanu": "Jupiter",
    "makara": "Saturn",
    "kumbha": "Saturn",    # (ignoring Rahu co-lord)
    "meena": "Jupiter",
}

# Natural Planetary Relationships (for Rasi Adhipathi)
# Format: Planet -> {Friends, Neutrals, Enemies}
PLANET_RELATIONSHIPS = {
    "Sun": {
        "friends": {"Moon", "Mars", "Jupiter"},
        "neutrals": {"Mercury"},
        "enemies": {"Venus", "Saturn"},
    },
    "Moon": {
        "friends": {"Sun", "Mercury"},
        "neutrals": {"Mars", "Jupiter", "Venus", "Saturn"},
        "enemies": set(),
    },
    "Mars": {
        "friends": {"Sun", "Moon", "Jupiter"},
        "neutrals": {"Venus", "Saturn"},
        "enemies": {"Mercury"},
    },
    "Mercury": {
        "friends": {"Sun", "Venus"},
        "neutrals": {"Mars", "Jupiter", "Saturn"},
        "enemies": {"Moon"},
    },
    "Jupiter": {
        "friends": {"Sun", "Moon", "Mars"},
        "neutrals": {"Saturn"},
        "enemies": {"Mercury", "Venus"},
    },
    "Venus": {
        "friends": {"Mercury", "Saturn"},
        "neutrals": {"Mars", "Jupiter"},
        "enemies": {"Sun", "Moon"},
    },
    "Saturn": {
        "friends": {"Mercury", "Venus"},
        "neutrals": {"Jupiter"},
        "enemies": {"Sun", "Moon", "Mars"},
    },
}


def get_planet_relationship(planet1: str, planet2: str) -> tuple[str, str]:
    """
    Get the relationship from planet1's perspective and planet2's perspective.
    Returns: (planet1_to_planet2, planet2_to_planet1)
    Each can be: 'friend', 'neutral', 'enemy'
    """
    if planet1 == planet2:
        return ("same", "same")
    
    rel1 = PLANET_RELATIONSHIPS.get(planet1, {})
    rel2 = PLANET_RELATIONSHIPS.get(planet2, {})
    
    # Check planet1's view of planet2
    if planet2 in rel1.get("friends", set()):
        p1_to_p2 = "friend"
    elif planet2 in rel1.get("enemies", set()):
        p1_to_p2 = "enemy"
    else:
        p1_to_p2 = "neutral"
    
    # Check planet2's view of planet1
    if planet1 in rel2.get("friends", set()):
        p2_to_p1 = "friend"
    elif planet1 in rel2.get("enemies", set()):
        p2_to_p1 = "enemy"
    else:
        p2_to_p1 = "neutral"
    
    return (p1_to_p2, p2_to_p1)


# -------------------------
# VASYA DATA (sign-to-sign attraction)
# -------------------------

# Vasya groups for each rasi
# Vasya compatibility matrix (Girl rasi as row, Boy rasi as column)
# G = Good, O = OK, B = Bad
VASYA_MATRIX = {
    "mesha": {
        "mesha": "Good", "vrishabha": "Good", "mithuna": "OK", "karka": "Bad",
        "simha": "Good", "kanya": "OK", "tula": "OK", "vrischika": "OK",
        "dhanu": "Good", "makara": "Good", "kumbha": "OK", "meena": "Bad"
    },
    "vrishabha": {
        "mesha": "Good", "vrishabha": "Good", "mithuna": "OK", "karka": "Bad",
        "simha": "Good", "kanya": "OK", "tula": "OK", "vrischika": "OK",
        "dhanu": "Good", "makara": "Good", "kumbha": "OK", "meena": "Bad"
    },
    "mithuna": {
        "mesha": "OK", "vrishabha": "OK", "mithuna": "Good", "karka": "OK",
        "simha": "Bad", "kanya": "Good", "tula": "Good", "vrischika": "Bad",
        "dhanu": "OK", "makara": "OK", "kumbha": "Good", "meena": "OK"
    },
    "karka": {
        "mesha": "Bad", "vrishabha": "Bad", "mithuna": "OK", "karka": "Good",
        "simha": "OK", "kanya": "OK", "tula": "OK", "vrischika": "OK",
        "dhanu": "Bad", "makara": "Bad", "kumbha": "OK", "meena": "Good"
    },
    "simha": {
        "mesha": "Good", "vrishabha": "Good", "mithuna": "Bad", "karka": "OK",
        "simha": "Good", "kanya": "Bad", "tula": "Bad", "vrischika": "OK",
        "dhanu": "Good", "makara": "Good", "kumbha": "Bad", "meena": "OK"
    },
    "kanya": {
        "mesha": "OK", "vrishabha": "OK", "mithuna": "Good", "karka": "OK",
        "simha": "Bad", "kanya": "Good", "tula": "Good", "vrischika": "OK",
        "dhanu": "OK", "makara": "OK", "kumbha": "Good", "meena": "OK"
    },
    "tula": {
        "mesha": "OK", "vrishabha": "OK", "mithuna": "Good", "karka": "OK",
        "simha": "Bad", "kanya": "Good", "tula": "Good", "vrischika": "OK",
        "dhanu": "OK", "makara": "OK", "kumbha": "Good", "meena": "OK"
    },
    "vrischika": {
        "mesha": "OK", "vrishabha": "OK", "mithuna": "Bad", "karka": "OK",
        "simha": "OK", "kanya": "OK", "tula": "OK", "vrischika": "Good",
        "dhanu": "Bad", "makara": "OK", "kumbha": "Bad", "meena": "OK"
    },
    "dhanu": {
        "mesha": "Good", "vrishabha": "Good", "mithuna": "OK", "karka": "Bad",
        "simha": "Good", "kanya": "OK", "tula": "OK", "vrischika": "OK",
        "dhanu": "Good", "makara": "Good", "kumbha": "OK", "meena": "Bad"
    },
    "makara": {
        "mesha": "Good", "vrishabha": "Good", "mithuna": "OK", "karka": "Bad",
        "simha": "Good", "kanya": "OK", "tula": "OK", "vrischika": "OK",
        "dhanu": "Good", "makara": "Good", "kumbha": "OK", "meena": "Bad"
    },
    "kumbha": {
        "mesha": "OK", "vrishabha": "OK", "mithuna": "Good", "karka": "OK",
        "simha": "Bad", "kanya": "Good", "tula": "Good", "vrischika": "Bad",
        "dhanu": "OK", "makara": "OK", "kumbha": "Good", "meena": "OK"
    },
    "meena": {
        "mesha": "Bad", "vrishabha": "Bad", "mithuna": "OK", "karka": "Good",
        "simha": "OK", "kanya": "OK", "tula": "OK", "vrischika": "OK",
        "dhanu": "Bad", "makara": "Bad", "kumbha": "OK", "meena": "Good"
    },
}

def get_vasya_compatibility(girl_rasi: str, boy_rasi: str) -> str:
    """
    Returns: 'Good', 'OK', 'Bad', or 'Unknown'
    Direct lookup from Vasya matrix.
    """
    g_r = norm_rasi_name(girl_rasi)
    b_r = norm_rasi_name(boy_rasi)
    
    if g_r not in VASYA_MATRIX or b_r not in VASYA_MATRIX.get(g_r, {}):
        return "Unknown"
    
    return VASYA_MATRIX[g_r][b_r]


# -------------------------
# VEDHA DATA (nakshatra obstruction pairs)
# -------------------------

# Vedha pairs - each nakshatra has exactly one nakshatra that causes obstruction
# The mapping is bidirectional (symmetric)
VEDHA_PAIRS = {
    "ashwini": "jyeshta",
    "bharani": "anuradha",
    "krittika": "vishakha",
    "rohini": "swati",
    "mrigasira": "chitra",
    "mrigashirsha": "chitra",  # Alternate spelling
    "ardra": "hasta",
    "arudra": "hasta",  # Alternate spelling
    "punarvasu": "uttaraphalguni",
    "pushya": "purvaphalguni",
    "pushyami": "purvaphalguni",  # Alternate spelling
    "ashlesha": "magha",
    "aslesha": "magha",  # Alternate spelling
    "magha": "ashlesha",
    "purvaphalguni": "pushya",
    "purva_phalguni": "pushya",  # Alternate spelling
    "uttaraphalguni": "punarvasu",
    "uttara_phalguni": "punarvasu",  # Alternate spelling
    "hasta": "ardra",
    "chitra": "mrigasira",
    "swati": "rohini",
    "vishakha": "krittika",
    "visakha": "krittika",  # Alternate spelling
    "anuradha": "bharani",
    "jyeshta": "ashwini",
    "jyestha": "ashwini",  # Alternate spelling
    "moola": "revati",
    "mula": "revati",  # Alternate spelling
    "purvashadha": "uttarabhadrapada",
    "purvashada": "uttarabhadrapada",  # Alternate spelling
    "uttarashadha": "purvabhadrapada",
    "uttarashada": "purvabhadrapada",  # Alternate spelling
    "shravana": "satabhisha",
    "sravana": "satabhisha",  # Alternate spelling
    "dhanishta": "revati",
    "satabhisha": "shravana",
    "shatataraka": "shravana",  # Alternate spelling
    "purvabhadrapada": "uttarashadha",
    "purvabhadra": "uttarashadha",  # Alternate spelling
    "uttarabhadrapada": "purvashadha",
    "revati": "moola",
}

def nakshatra_has_vedha(n1: str, n2: str) -> bool:
    """Check if two nakshatras form a Vedha (obstruction) pair."""
    n1_norm = norm_nak_name(n1)
    n2_norm = norm_nak_name(n2)
    
    # Check if n1's vedha partner is n2
    vedha_partner = VEDHA_PAIRS.get(n1_norm)
    if vedha_partner and norm_nak_name(vedha_partner) == n2_norm:
        return True
    
    # Check if n2's vedha partner is n1 (symmetric check)
    vedha_partner = VEDHA_PAIRS.get(n2_norm)
    if vedha_partner and norm_nak_name(vedha_partner) == n1_norm:
        return True
    
    return False


# -------------------------
# RAJJU DATA & LOGIC
# -------------------------

RAJJU_GROUPS = {
    "Siro": {
        "body": "Head",
        "nakshatras": ["Chitra", "Mrigasira", "Dhanishta"],
    },
    "Kanta": {
        "body": "Neck",
        "nakshatras": ["Ardra", "Rohini", "Swati", "Hasta", "Shravana", "Satabhisha"],
    },
    "Nabhi": {
        "body": "Navel",
        "nakshatras": [
            "Krittika", "Uttaraphalguni", "Punarvasu",
            "Vishakha", "Purvabhadra", "Uttarashadha",
        ],
    },
    "Kati": {
        "body": "Thigh",
        "nakshatras": [
            "Pushya", "Bharani", "Purvaphalguni",
            "Anuradha", "Uttarabhadrapada", "Purvashadha",
        ],
    },
    "Pada": {
        "body": "Feet",
        "nakshatras": ["Ashwini", "Ashlesha", "Magha", "Moola", "Jyeshta", "Revati"],
    },
}

RAJJU_BY_NAK: Dict[str, Tuple[str, str]] = {}
for group, info in RAJJU_GROUPS.items():
    body = info["body"]
    for n in info["nakshatras"]:
        RAJJU_BY_NAK[norm_nak_name(n)] = (group, body)


def compute_rajju_porutham(girl: PersonChart, boy: PersonChart) -> PoruthamResult:
    """
    Rajju porutham using explicit Rajju groups.

    Rule:
      - If both nakshatras fall in the SAME Rajju group → Rajju dosha (Not Safe).
      - If they fall in DIFFERENT Rajju groups → SAFE.
    """
    g_key = norm_nak_name(girl.nakshatra)
    b_key = norm_nak_name(boy.nakshatra)

    g_info = RAJJU_BY_NAK.get(g_key)
    b_info = RAJJU_BY_NAK.get(b_key)

    if not g_info or not b_info:
        detail = (
            f"Girl nakshatra: {girl.nakshatra} "
            f"({g_key}, mapped Rajju: {'unknown' if not g_info else g_info[0]}), "
            f"Boy nakshatra: {boy.nakshatra} "
            f"({b_key}, mapped Rajju: {'unknown' if not b_info else b_info[0]})."
        )
        logic = (
            "Rajju porutham groups each nakshatra into one of five Rajju: "
            "Siro (Head), Kanta (Neck), Nabhi (Navel), Kati (Thigh), Pada (Feet).\n"
            "If both belong to the same Rajju group, it is considered Rajju dosha. "
            "Here, at least one nakshatra could not be mapped in the internal table, "
            "so result is marked Unknown.\n\n"
            "Refer to the 'Reference / Knowledge Base' section in the report to see "
            "which nakshatras are listed under each Rajju group."
        )
        return PoruthamResult(
            name="Rajju",
            status="Unknown",
            comment="Rajju porutham is about the safety and longevity of marriage; here it could not be fully evaluated from the internal Rajju table.",
            detail=detail,
            logic=logic,
        )

    g_group, g_body = g_info
    b_group, b_body = b_info

    same_group = (g_group == b_group)

    if same_group:
        status = "Bad"
        comment = (
            "Rajju porutham is about the structural safety and longevity of marriage. "
            f"Both stars fall in the same Rajju group ({g_group}), so this indicates Rajju dosha and is usually avoided."
        )
    else:
        status = "SAFE"
        comment = (
            "Rajju porutham is about the structural safety and longevity of marriage. "
            f"Here girl and boy belong to different Rajju groups ({g_group} vs {b_group}), so Rajju is SAFE."
        )

    detail = (
        f"Girl nakshatra {girl.nakshatra} → {g_group} Rajju ({g_body}).\n"
        f"Boy nakshatra {boy.nakshatra} → {b_group} Rajju ({b_body}).\n"
        f"Since their Rajju groups are "
        f"{'the SAME → Rajju dosha' if same_group else 'DIFFERENT → SAFE'}."
    )

    logic = (
        "HOW RAJJU PORUTHAM IS CHECKED\n"
        "------------------------------\n"
        "1) Each nakshatra is assigned to one of five Rajju groups:\n"
        "   • Siro  (Head)\n"
        "   • Kanta (Neck)\n"
        "   • Nabhi (Navel)\n"
        "   • Kati  (Thigh)\n"
        "   • Pada  (Feet)\n\n"
        "2) Principle: if BOTH partners' stars fall in the SAME Rajju group,\n"
        "   it is considered Rajju dosha and is usually avoided.\n"
        "   Different Rajju groups → SAFE.\n\n"
        f"For this pair:\n"
        f"   • Girl: {girl.nakshatra} → {g_group} Rajju ({g_body}).\n"
        f"   • Boy:  {boy.nakshatra} → {b_group} Rajju ({b_body}).\n"
        f"   • Same group?  {'Yes → Rajju dosha' if same_group else 'No → SAFE'}.\n\n"
        "You can cross-check this in the 'Reference / Knowledge Base' card at the bottom "
        "of the report, where all nakshatras are listed under their Rajju group."
    )

    return PoruthamResult(
        name="Rajju",
        status=status,
        comment=comment,
        detail=detail,
        logic=logic,
    )


# -------------------------
# DINA PORUTHAM – REAL CALCULATION
# -------------------------

def compute_dina_porutham(girl: PersonChart, boy: PersonChart) -> PoruthamResult:
    """
    Compute Dina (Tara) porutham using the 9-Tara cycle.

    Steps:
      1. Count from girl's nakshatra to boy's nakshatra (forward, inclusive)
      2. Reduce count to 9-Tara cycle using modulo 9
      3. Good Taras: Sampat(2), Kshema(4), Sadhana(6), Mitra(8), Param-Mitra(9/0)
      4. Bad Taras: Janma(1), Vipat(3), Pratyari(5), Naidhana(7)
    """
    try:
        g_idx = get_nak_index(girl.nakshatra)
        b_idx = get_nak_index(boy.nakshatra)
    except ValueError as e:
        return PoruthamResult(
            name="Dina",
            status="Unknown",
            comment="Dina (Tara) porutham shows health, day-to-day harmony and general well-being; here it could not be computed because nakshatra index could not be determined.",
            detail=str(e),
            logic=(
                "Dina porutham uses the Tara cycle to count from girl's star to boy's star. "
                "Count forward from girl → boy (inclusive), then reduce to 9-Tara cycle."
            ),
        )

    # Convert to 0-based indices for modulo arithmetic
    G0 = g_idx - 1  # 0..26
    B0 = b_idx - 1  # 0..26
    
    # Count from girl to boy (forward, inclusive)
    # Formula: steps = (B0 - G0) % 27, then count = steps + 1
    steps = (B0 - G0) % 27
    count = steps + 1  # 1..27 inclusive
    
    # Reduce to 9-Tara cycle
    tara = count % 9
    if tara == 0:
        tara = 9  # 9 and multiples of 9 are Param-Mitra (9th Tara)
    
    # Tara names
    tara_names = {
        1: "Janma",
        2: "Sampat",
        3: "Vipat",
        4: "Kshema",
        5: "Pratyari",
        6: "Sadhana",
        7: "Naidhana",
        8: "Mitra",
        9: "Param-Mitra"
    }
    tara_name = tara_names.get(tara, "Unknown")
    
    # Classify Taras
    # Good Taras: 2, 4, 6, 8, 9 (Sampat, Kshema, Sadhana, Mitra, Param-Mitra)
    # Neutral Tara: 1 (Janma - same nakshatra)
    # Bad Taras: 3, 5, 7 (Vipat, Pratyari, Naidhana)
    
    if tara in {2, 4, 6, 8, 9}:
        status = "Good"
        comment = (
            f"Dina (Tara) porutham shows health, daily comfort and general harmony. "
            f"Count from girl → boy is {count}, which reduces to Tara {tara} ({tara_name}). "
            f"This is an auspicious Tara indicating good compatibility, ease, and prosperity."
        )
    elif tara == 1:
        status = "Average"
        comment = (
            f"Dina (Tara) porutham shows health, daily comfort and general harmony. "
            f"Count from girl → boy is {count}, which reduces to Tara {tara} ({tara_name}). "
            f"This is a neutral Tara (same nakshatra or Janma Tara), considered average/mixed - "
            f"neither particularly auspicious nor inauspicious."
        )
    else:  # tara in {3, 5, 7}
        status = "Bad"
        comment = (
            f"Dina (Tara) porutham shows health, daily comfort and general harmony. "
            f"Count from girl → boy is {count}, which reduces to Tara {tara} ({tara_name}). "
            f"This is an inauspicious Tara that may bring obstacles or challenges."
        )

    detail = (
        f"Girl nakshatra: {girl.nakshatra} (1-based index: {g_idx}, 0-based: {G0}).\n"
        f"Boy nakshatra: {boy.nakshatra} (1-based index: {b_idx}, 0-based: {B0}).\n"
        f"Steps: ({B0} - {G0}) % 27 = {steps}.\n"
        f"Count (inclusive): {steps} + 1 = {count}.\n"
        f"Tara number: {count} % 9 = {tara} ({tara_name}).\n"
        f"Result: {status} (good Taras are 2, 4, 6, 8, 9)."
    )

    logic = (
        "HOW DINA (TARA) PORUTHAM IS CALCULATED\n"
        "--------------------------------------\n"
        "Dina porutham counts from the girl's nakshatra forward to the boy's nakshatra\n"
        "through the 27-star wheel, then interprets that count via the 9-Tara cycle.\n\n"
        "FORMULA (using 0-based indices):\n"
        "   G0 = girl_index - 1  (0..26)\n"
        "   B0 = boy_index - 1   (0..26)\n"
        "   steps = (B0 - G0) % 27  (handles wrap-around automatically)\n"
        "   count = steps + 1       (1..27 inclusive)\n"
        "   tara = count % 9\n"
        "   if tara == 0: tara = 9\n\n"
        "THE NINE TARAS:\n"
        "   Tara 1 - Janma (birth)        - neutral/mixed\n"
        "   Tara 2 - Sampat (wealth)      - good ✓\n"
        "   Tara 3 - Vipat (danger)       - bad\n"
        "   Tara 4 - Kshema (well-being)  - good ✓\n"
        "   Tara 5 - Pratyari (obstacle)  - bad\n"
        "   Tara 6 - Sadhana (achievement)- good ✓\n"
        "   Tara 7 - Naidhana (death)     - bad\n"
        "   Tara 8 - Mitra (friend)       - good ✓\n"
        "   Tara 9 - Param-Mitra (best)   - very good ✓\n\n"
        "INTERPRETATION:\n"
        "   • Good Taras: 2, 4, 6, 8, 9 → positive Dina\n"
        "   • Bad Taras: 3, 5, 7 → negative Dina\n"
        "   • Tara 1: neutral/average\n\n"
        f"FOR THIS PAIR:\n"
        f"   • Girl: {girl.nakshatra} (1-based: {g_idx}, 0-based: {G0})\n"
        f"   • Boy: {boy.nakshatra} (1-based: {b_idx}, 0-based: {B0})\n"
        f"   • steps = ({B0} - {G0}) % 27 = {steps}\n"
        f"   • count = {steps} + 1 = {count}\n"
        f"   • Tara = {count} % 9 = {tara} ({tara_name})\n"
        f"   • Classification: {status.upper()}\n\n"
        "EXAMPLES:\n"
        "   • Girl=Ashwini(1), Boy=Rohini(4): steps=3, count=4, tara=4 (Kshema) → Good\n"
        "   • Girl=Anuradha(17), Boy=Vishakha(16): steps=26, count=27, tara=9 (Param-Mitra) → Very Good\n\n"
        "Common good counts: 2, 4, 8, 9, 11, 13, 15, 18, 20, 24, 26"
    )

    return PoruthamResult(
        name="Dina",
        status=status,
        comment=comment,
        detail=detail,
        logic=logic,
    )


# -------------------------
# Extra Porutham logics (Rasi, Rasi Adhipathi, Stree Dheergha, Vasya, Mahendra, Vedha)
# -------------------------

def compute_rasi_porutham(girl: PersonChart, boy: PersonChart) -> PoruthamResult:
    """
    Kerala-style Rasi porutham.
    
    Count forward distance from girl's rasi to boy's rasi on the zodiac wheel.
    Favorable distances: 1, 3, 4, 7, 10, 11, 12
    Unfavorable distances: 2, 5, 6, 8, 9
    """
    g_r = norm_rasi_name(girl.rasi)
    b_r = norm_rasi_name(boy.rasi)

    if g_r not in RASI_INDEX or b_r not in RASI_INDEX:
        return PoruthamResult(
            name="Rasi",
            status="Unknown",
            comment="Rasi porutham could not be computed because one of the Moon signs is not recognized.",
            detail=f"Girl Rasi: {girl.rasi}, Boy Rasi: {boy.rasi}",
            logic="Update RASI_CANON / norm_rasi_name() if you use different sign names.",
        )

    g_idx = RASI_INDEX[g_r]
    b_idx = RASI_INDEX[b_r]

    # Count forward distance from girl to boy (girl's rasi = position 1)
    # If same rasi: going full circle = 12
    # Otherwise: count positions forward from girl to boy
    if g_idx == b_idx:
        distance = 12  # Same rasi, full circle
    else:
        # Steps from girl to boy (not including girl, including boy)
        steps = (b_idx - g_idx) % 12
        distance = steps + 1  # Add 1 because we start counting from girl's rasi as "1"

    # Favorable distances: 1, 3, 4, 7, 10, 11, 12
    # Unfavorable distances: 2, 5, 6, 8, 9
    favorable = {1, 3, 4, 7, 10, 11, 12}
    
    if distance in favorable:
        status = "Good"
        comment = (
            "Rasi porutham checks emotional compatibility via Moon sign relationship. "
            f"Distance from girl's rasi to boy's rasi is {distance}, which is favorable. "
            "This indicates friendship, similarity, mutual support, attraction, and domestic harmony."
        )
    else:
        status = "Bad"
    comment = (
        "Rasi porutham checks emotional compatibility via Moon sign relationship. "
            f"Distance from girl's rasi to boy's rasi is {distance}, which is unfavorable. "
            "This may indicate tension, ego clashes, or obstruction between partners."
    )

    detail = (
        f"Girl Rasi: {girl.rasi} (index {g_idx}), "
        f"Boy Rasi: {boy.rasi} (index {b_idx}).\n"
        f"Distance from Girl → Boy (forward) = {distance}.\n"
        f"Favorable distances: 1, 3, 4, 7, 10, 11, 12.\n"
        f"Unfavorable distances: 2, 5, 6, 8, 9."
    )

    logic = (
        "HOW RASI PORUTHAM IS CHECKED (KERALA TRADITION)\n"
        "-----------------------------------------------\n"
        "1) The twelve rasis are arranged in cyclical order:\n"
        "   Mesha(1), Vrishabha(2), Mithuna(3), Karka(4), Simha(5), Kanya(6),\n"
        "   Tula(7), Vrischika(8), Dhanu(9), Makara(10), Kumbha(11), Meena(12).\n\n"
        "2) Count forward from girl's rasi to boy's rasi:\n"
        "   - Start at girl's rasi as position 1\n"
        "   - Count forward around the zodiac wheel\n"
        "   - If boy's rasi comes before girl's, wrap around after Meena to Mesha\n"
        "   - Formula: distance = (boy_index - girl_index) % 12\n"
        "   - If distance = 0 (same rasi), use distance = 12\n\n"
        "3) Interpretation:\n"
        "   • Favorable distances: 1, 3, 4, 7, 10, 11, 12\n"
        "     (friendship, similarity, support, attraction, stability)\n"
        "   • Unfavorable distances: 2, 5, 6, 8, 9\n"
        "     (tension, ego clashes, disease, obstruction)\n\n"
        f"FOR THIS PAIR:\n"
        f"   • Girl: {girl.rasi} (index {g_idx})\n"
        f"   • Boy: {boy.rasi} (index {b_idx})\n"
        f"   • Distance: ({b_idx} - {g_idx}) % 12 = {distance}\n"
        f"   • Classification: {status.upper()}\n\n"
        "This method is based on traditional Kerala texts measuring emotional\n"
        "compatibility and domestic harmony through rasi distance."
    )

    return PoruthamResult(
        name="Rasi",
        status=status,
        comment=comment,
        detail=detail,
        logic=logic,
    )


def compute_rasi_adhipati_porutham(girl: PersonChart, boy: PersonChart) -> PoruthamResult:
    """
    Rasi Adhipathi checks the natural friendship between the ruling planets
    of the boy's and girl's Moon signs.
    
    Classification:
      - Friend-Friend: Very Good
      - Friend-Neutral or Neutral-Neutral: Good
      - Neutral-Enemy: Average
      - Enemy-Enemy: Bad
    """
    g_r = norm_rasi_name(girl.rasi)
    b_r = norm_rasi_name(boy.rasi)

    g_lord = RASI_LORD.get(g_r)
    b_lord = RASI_LORD.get(b_r)

    if not g_lord or not b_lord:
        return PoruthamResult(
            name="Rasi Adhipathi",
            status="Unknown",
            comment="Moon sign lords could not be determined from the internal table.",
            detail=f"Girl Rasi: {girl.rasi} → {g_lord}, Boy Rasi: {boy.rasi} → {b_lord}",
            logic="Extend RASI_LORD if you are using different sign names or lordship scheme.",
        )

    # Get bidirectional relationship
    g_to_b, b_to_g = get_planet_relationship(g_lord, b_lord)

    if g_to_b == "same":
        status = "Very Good"
        comment_base = "Both Moon signs share the same planetary lord, indicating perfect harmony."
        relation_desc = "same lord"
    elif g_to_b == "friend" and b_to_g == "friend":
        status = "Very Good"
        comment_base = f"{g_lord} and {b_lord} are mutual friends, indicating excellent emotional cooperation."
        relation_desc = "friend–friend"
    elif (g_to_b == "friend" and b_to_g == "neutral") or (g_to_b == "neutral" and b_to_g == "friend"):
        status = "Good"
        comment_base = f"One treats the other as friend, indicating good emotional support."
        relation_desc = "friend–neutral"
    elif g_to_b == "neutral" and b_to_g == "neutral":
        status = "Good"
        comment_base = f"{g_lord} and {b_lord} are neutral to each other, indicating acceptable compatibility."
        relation_desc = "neutral–neutral"
    elif (g_to_b == "neutral" and b_to_g == "enemy") or (g_to_b == "enemy" and b_to_g == "neutral"):
        status = "Average"
        comment_base = f"One neutral, one enemy relationship - average compatibility."
        relation_desc = "neutral–enemy"
    elif (g_to_b == "friend" and b_to_g == "enemy") or (g_to_b == "enemy" and b_to_g == "friend"):
        status = "Average"
        comment_base = f"Mixed relationship (friend and enemy) - average compatibility."
        relation_desc = "friend–enemy (mixed)"
    else:  # enemy-enemy
        status = "Bad"
        comment_base = f"{g_lord} and {b_lord} are mutual enemies, indicating emotional strain."
        relation_desc = "enemy–enemy"

    comment = (
        "Rasi Adhipathi porutham checks the natural friendship between the ruling planets "
        f"of the Moon signs. {comment_base}"
    )

    detail = (
        f"Girl Rasi: {girl.rasi} → lord {g_lord}\n"
        f"Boy Rasi: {boy.rasi} → lord {b_lord}\n"
        f"{g_lord} treats {b_lord} as: {g_to_b}\n"
        f"{b_lord} treats {g_lord} as: {b_to_g}\n"
        f"Combined relationship: {relation_desc} → {status}"
    )

    logic = (
        "HOW RASI ADHIPATHI PORUTHAM IS CHECKED\n"
        "--------------------------------------\n"
        "1) Identify the ruling planet of each Moon sign:\n"
        "   Mesha→Mars, Vrishabha→Venus, Mithuna→Mercury, Karka→Moon,\n"
        "   Simha→Sun, Kanya→Mercury, Tula→Venus, Vrischika→Mars,\n"
        "   Dhanu→Jupiter, Makara→Saturn, Kumbha→Saturn, Meena→Jupiter\n\n"
        "2) Check natural planetary friendships (both directions):\n"
        "   Each planet has friends, neutrals, and enemies.\n\n"
        "3) Classification:\n"
        "   • Friend–Friend        → Very Good\n"
        "   • Friend–Neutral       → Good\n"
        "   • Neutral–Neutral      → Good\n"
        "   • Neutral–Enemy        → Average\n"
        "   • Friend–Enemy (mixed) → Average\n"
        "   • Enemy–Enemy          → Bad\n\n"
        f"FOR THIS PAIR:\n"
        f"   • Girl lord: {g_lord} treats {b_lord} as {g_to_b}\n"
        f"   • Boy lord: {b_lord} treats {g_lord} as {b_to_g}\n"
        f"   • Combined: {relation_desc}\n"
        f"   • Classification: {status.upper()}\n\n"
        "This tells how naturally the emotional patterns and mental temperaments\n"
        "of the two people will cooperate or conflict."
    )

    return PoruthamResult(
        name="Rasi Adhipathi",
        status=status,
        comment=comment,
        detail=detail,
        logic=logic,
    )


def compute_stree_dheergha_porutham(girl: PersonChart, boy: PersonChart) -> PoruthamResult:
    """
    Stree Dheergha checks the distance from girl's star to boy's star.
    
    Count forward from girl to boy (not including girl, including boy).
    - If distance < 7: FAIL (Bad)
    - If distance >= 7: PASS (Good)
    """
    try:
        g_idx = get_nak_index(girl.nakshatra)
        b_idx = get_nak_index(boy.nakshatra)
    except ValueError as e:
        return PoruthamResult(
            name="Stree Dheergha",
            status="Unknown",
            comment="Stree Dheergha could not be computed because nakshatra index could not be determined.",
            detail=str(e),
            logic="Ensure nakshatra names match NAK_ORDER or extend NAK_ORDER/norm_nak_name().",
        )

    # Count forward from girl to boy (not including girl's star)
    # Convert to 0-based for calculation
    G0 = g_idx - 1
    B0 = b_idx - 1
    
    # Distance = steps forward from girl to boy
    distance = (B0 - G0) % 27
    
    if distance == 0:
        # Same nakshatra - distance is 0
        status = "Bad"
        comment = (
            "Stree Dheergha: Both have the same nakshatra (distance = 0). "
            "This fails the minimum requirement of 7 stars."
        )
    elif distance >= 7:
        status = "Good"
        comment = (
            f"Stree Dheergha is present (distance from girl to boy is {distance} stars, ≥ 7). "
            "This indicates adequate emotional protection and longevity for the woman."
        )
    else:
        status = "Bad"
        comment = (
            f"Stree Dheergha is not present (distance from girl to boy is only {distance} stars, < 7). "
            "This is considered a weakness in emotional protection."
        )

    detail = (
        f"Girl nakshatra: {girl.nakshatra} (index {g_idx}).\n"
        f"Boy nakshatra: {boy.nakshatra} (index {b_idx}).\n"
        f"Distance (forward from girl to boy, not including girl): {distance}.\n"
        f"Rule: distance ≥ 7 → Good, distance < 7 → Bad."
    )

    logic = (
        "HOW STREE DHEERGHA IS CHECKED\n"
        "------------------------------\n"
        "1) Count forward from girl's nakshatra to boy's nakshatra.\n"
        "   Do NOT include girl's star in the count (start from the next star).\n"
        "   DO include boy's star.\n\n"
        "2) Formula:\n"
        "   G0 = girl_index - 1 (convert to 0-based)\n"
        "   B0 = boy_index - 1 (convert to 0-based)\n"
        "   distance = (B0 - G0) % 27\n\n"
        "3) Classification:\n"
        "   • distance ≥ 7  → Good (Stree Dheergha present)\n"
        "   • distance < 7  → Bad (Stree Dheergha absent)\n\n"
        f"FOR THIS PAIR:\n"
        f"   • Girl: {girl.nakshatra} (index {g_idx}, 0-based: {G0})\n"
        f"   • Boy: {boy.nakshatra} (index {b_idx}, 0-based: {B0})\n"
        f"   • distance = ({B0} - {G0}) % 27 = {distance}\n"
        f"   • Classification: {status.upper()}\n\n"
        "EXAMPLE:\n"
        "   Girl: Ashwini (index 1, 0-based: 0)\n"
        "   Boy: Rohini (index 4, 0-based: 3)\n"
        "   Counting: Ashwini → Bharani(1) → Krittika(2) → Rohini(3)\n"
        "   distance = (3 - 0) % 27 = 3 → Bad (< 7)\n\n"
        "This porutham ensures the boy's star is sufficiently ahead,\n"
        "symbolizing longevity and emotional protection for the woman."
    )

    return PoruthamResult(
        name="Stree Dheergha",
        status=status,
        comment=comment,
        detail=detail,
        logic=logic,
    )


def compute_vasya_porutham(girl: PersonChart, boy: PersonChart) -> PoruthamResult:
    """
    Vasya porutham checks attraction and mutual control between rasis.
    Uses a direct rasi-to-rasi compatibility matrix.
    """
    status = get_vasya_compatibility(girl.rasi, boy.rasi)
    
    if status == "Unknown":
        return PoruthamResult(
            name="Vasya",
            status="Unknown",
            comment="Vasya porutham could not be computed because rasi could not be determined.",
            detail=f"Girl Rasi: {girl.rasi}, Boy Rasi: {boy.rasi}",
            logic="Update VASYA_MATRIX if needed.",
        )
    
    g_r = norm_rasi_name(girl.rasi)
    b_r = norm_rasi_name(boy.rasi)
    
    if status == "Good":
        comment = (
            f"Vasya porutham: Girl's {girl.rasi} and Boy's {boy.rasi} form a good combination. "
            "This indicates natural attraction, mutual control, and willingness to adjust."
        )
    elif status == "OK":
        comment = (
            f"Vasya porutham: Girl's {girl.rasi} and Boy's {boy.rasi} form an acceptable combination. "
            "This is okay but may require some adjustment."
        )
    else:  # Bad
        comment = (
            f"Vasya porutham: Girl's {girl.rasi} and Boy's {boy.rasi} form an unfavorable combination. "
            "This may indicate lack of mutual attraction or control issues."
        )

    detail = (
        f"Girl Rasi: {girl.rasi}\n"
        f"Boy Rasi: {boy.rasi}\n"
        f"Vasya compatibility: {status}"
    )

    logic = (
        "HOW VASYA PORUTHAM IS CHECKED\n"
        "------------------------------\n"
        "Vasya porutham uses a direct rasi-to-rasi compatibility matrix.\n"
        "The compatibility is looked up from girl's rasi (row) to boy's rasi (column).\n\n"
        "VASYA MATRIX:\n"
        "   Girl ↓ \\ Boy →  | Mesha | Vrishabha | Mithuna | Karka | ... | Meena\n"
        "   ─────────────────┼───────┼───────────┼─────────┼───────┼─────┼──────\n"
        "   Mesha            |   G   |     G     |    O    |   B   | ... |   B\n"
        "   Vrishabha        |   G   |     G     |    O    |   B   | ... |   B\n"
        "   Mithuna          |   O   |     O     |    G    |   O   | ... |   O\n"
        "   ...\n\n"
        "   Where: G = Good, O = OK, B = Bad\n\n"
        f"FOR THIS PAIR:\n"
        f"   • Girl: {girl.rasi} (normalized: {g_r})\n"
        f"   • Boy: {boy.rasi} (normalized: {b_r})\n"
        f"   • Matrix lookup [{g_r}][{b_r}] = {status}\n\n"
        "Vasya porutham indicates natural attraction, mutual control,\n"
        "and willingness to adjust between partners."
    )

    return PoruthamResult(
        name="Vasya",
        status=status,
        comment=comment,
        detail=detail,
        logic=logic,
    )


def compute_mahendra_porutham(girl: PersonChart, boy: PersonChart) -> PoruthamResult:
    """
    Mahendra porutham is counted starting from the Girl's star.
    
    The girl's star counts as 1, and you count forward to the boy's star (inclusive).
    Good if count is in {4, 7, 10, 13, 16, 19, 22, 25}
    """
    try:
        g_idx = get_nak_index(girl.nakshatra)
        b_idx = get_nak_index(boy.nakshatra)
    except ValueError as e:
        return PoruthamResult(
            name="Mahendra",
            status="Unknown",
            comment="Mahendra porutham could not be computed because nakshatra index could not be determined.",
            detail=str(e),
            logic="Ensure nakshatra names match NAK_ORDER or extend NAK_ORDER/norm_nak_name().",
        )

    # Count from girl's star to boy's star (girl's star = 1, inclusive)
    # Convert to 0-based for calculation
    G0 = g_idx - 1
    B0 = b_idx - 1
    
    # Steps forward (not including girl's star position)
    steps = (B0 - G0) % 27
    
    # Count includes girl's star as position 1
    count = steps + 1
    
    # Good Mahendra counts
    good_counts = {4, 7, 10, 13, 16, 19, 22, 25}

    if count in good_counts:
        status = "Good"
        comment = (
            f"Mahendra porutham is present (count = {count}). "
            "This supports prosperity, protection, and general support from the boy's side."
        )
    else:
        status = "Bad"
        comment = (
            f"Mahendra porutham is not present (count = {count}). "
            "This may indicate lack of strong support, though it's not a rejection factor if other poruthams are healthy."
        )

    detail = (
        f"Girl nakshatra: {girl.nakshatra} (index {g_idx}).\n"
        f"Boy nakshatra: {boy.nakshatra} (index {b_idx}).\n"
        f"Count from girl to boy (girl = 1): {count}.\n"
        f"Good Mahendra counts: {sorted(good_counts)}."
    )

    logic = (
        "HOW MAHENDRA PORUTHAM IS CHECKED\n"
        "---------------------------------\n"
        "Mahendra is always counted starting from the Girl's star.\n\n"
        "1) Take the girl's nakshatra and treat it as number 1.\n"
        "2) Count forward until you reach the boy's nakshatra (inclusive).\n"
        "3) The count is good if it equals: 4, 7, 10, 13, 16, 19, 22, or 25.\n\n"
        "FORMULA:\n"
        "   G0 = girl_index - 1 (convert to 0-based)\n"
        "   B0 = boy_index - 1 (convert to 0-based)\n"
        "   steps = (B0 - G0) % 27\n"
        "   count = steps + 1 (girl's star counts as 1)\n\n"
        f"FOR THIS PAIR:\n"
        f"   • Girl: {girl.nakshatra} (index {g_idx}, 0-based: {G0})\n"
        f"   • Boy: {boy.nakshatra} (index {b_idx}, 0-based: {B0})\n"
        f"   • steps = ({B0} - {G0}) % 27 = {steps}\n"
        f"   • count = {steps} + 1 = {count}\n"
        f"   • Result: {status.upper()}\n\n"
        "EXAMPLE:\n"
        "   Girl: Ashwini (index 1, 0-based: 0)\n"
        "   Boy: Rohini (index 4, 0-based: 3)\n"
        "   Counting: Ashwini(1) → Bharani(2) → Krittika(3) → Rohini(4)\n"
        "   count = 4 → Good ✓\n\n"
        "Mahendra porutham indicates prosperity and protection."
    )

    return PoruthamResult(
        name="Mahendra",
        status=status,
        comment=comment,
        detail=detail,
        logic=logic,
    )


def compute_vedha_porutham(girl: PersonChart, boy: PersonChart) -> PoruthamResult:
    """
    Vedha Porutham checks if the couple's nakshatras form an obstructing pair.
    
    Each nakshatra has exactly one nakshatra that causes Vedha (obstruction).
    The relationship is symmetric: if A obstructs B, then B obstructs A.
    """
    g_nak_norm = norm_nak_name(girl.nakshatra)
    b_nak_norm = norm_nak_name(boy.nakshatra)
    
    has_v = nakshatra_has_vedha(girl.nakshatra, boy.nakshatra)
    
    # Get the vedha partner for reference in detail
    g_vedha_partner = VEDHA_PAIRS.get(g_nak_norm, "Unknown")

    if has_v:
        status = "Bad"
        comment = (
            f"Vedha porutham: {girl.nakshatra} and {boy.nakshatra} form a Vedha (obstruction) pair. "
            "This is considered a significant caution as it indicates mutual obstruction and should be carefully evaluated."
        )
        detail = (
            f"Girl nakshatra: {girl.nakshatra}\n"
            f"Boy nakshatra: {boy.nakshatra}\n"
            f"Result: These nakshatras form a Vedha pair (obstruction).\n"
            f"Note: {girl.nakshatra}'s Vedha partner is {g_vedha_partner.capitalize()}."
        )
    else:
        status = "Good"
        comment = (
            f"Vedha porutham: {girl.nakshatra} and {boy.nakshatra} do not form a Vedha pair. "
            "This factor is safe and poses no obstruction."
        )
        detail = (
            f"Girl nakshatra: {girl.nakshatra}\n"
            f"Boy nakshatra: {boy.nakshatra}\n"
            f"Result: These nakshatras do not form a Vedha pair.\n"
            f"Note: {girl.nakshatra}'s Vedha partner is {g_vedha_partner.capitalize()}."
        )

    logic = (
        "HOW VEDHA PORUTHAM IS CHECKED\n"
        "------------------------------\n"
        "Vedha Porutham is computed by checking a fixed list of nakshatra pairs that obstruct each other.\n\n"
        "RULES:\n"
        "1) Each nakshatra has exactly one nakshatra that causes Vedha (obstruction).\n"
        "2) You do NOT count distances or cycles - it's a simple lookup.\n"
        "3) The relationship is symmetric: if A clashes with B, then B clashes with A.\n"
        "4) If the boy's nakshatra is the Vedha pair of the girl's nakshatra → Bad.\n"
        "5) If it's any other nakshatra → Good (Safe).\n\n"
        "VEDHA PAIRS:\n"
        "• Ashwini ↔ Jyeshtha\n"
        "• Bharani ↔ Anuradha\n"
        "• Krittika ↔ Vishakha\n"
        "• Rohini ↔ Swati\n"
        "• Mrigashira ↔ Chitra\n"
        "• Ardra ↔ Hasta\n"
        "• Punarvasu ↔ Uttara Phalguni\n"
        "• Pushya ↔ Purva Phalguni\n"
        "• Ashlesha ↔ Magha\n"
        "• Magha ↔ Ashlesha\n"
        "• Purva Phalguni ↔ Pushya\n"
        "• Uttara Phalguni ↔ Punarvasu\n"
        "• Hasta ↔ Ardra\n"
        "• Chitra ↔ Mrigashira\n"
        "• Swati ↔ Rohini\n"
        "• Vishakha ↔ Krittika\n"
        "• Anuradha ↔ Bharani\n"
        "• Jyeshtha ↔ Ashwini\n"
        "• Mula ↔ Revati\n"
        "• Purvashadha ↔ Uttarabhadra\n"
        "• Uttarashadha ↔ Purvabhadra\n"
        "• Shravana ↔ Shatabhisha\n"
        "• Dhanishta ↔ Revati\n"
        "• Shatabhisha ↔ Shravana\n"
        "• Purvabhadra ↔ Uttarashadha\n"
        "• Uttarabhadra ↔ Purvashadha\n"
        "• Revati ↔ Mula\n\n"
        f"FOR THIS PAIR:\n"
        f"• Girl: {girl.nakshatra} → Vedha partner: {g_vedha_partner.capitalize()}\n"
        f"• Boy: {boy.nakshatra}\n"
        f"• Vedha present: {'YES' if has_v else 'NO'}\n"
        f"• Result: {status.upper()}"
    )

    return PoruthamResult(
        name="Vedha",
        status=status,
        comment=comment,
        detail=detail,
        logic=logic,
    )


# -------------------------
# Porutham framework
# -------------------------

def compute_poruthams(girl: PersonChart, boy: PersonChart) -> List[PoruthamResult]:
    """
    Porutham framework.
    Fully computed:
      - Dina (Tara)
      - Gana
      - Yoni
      - Rasi
      - Rasi Adhipathi
      - Stree Dheergha
      - Vasya
      - Mahendra
      - Rajju
      - Vedha
    """
    results: List[PoruthamResult] = []

    # 1) Core nakshatra-based poruthams
    results.append(compute_dina_porutham(girl, boy))
    results.append(compute_gana_porutham(girl, boy))
    results.append(compute_yoni_porutham(girl, boy))

    # 2) Rasi & lord-based
    results.append(compute_rasi_porutham(girl, boy))
    results.append(compute_rasi_adhipati_porutham(girl, boy))

    # 3) Stree Dheergha, Vasya, Mahendra
    results.append(compute_stree_dheergha_porutham(girl, boy))
    results.append(compute_vasya_porutham(girl, boy))
    results.append(compute_mahendra_porutham(girl, boy))

    # 4) Rajju & Vedha
    results.append(compute_rajju_porutham(girl, boy))
    results.append(compute_vedha_porutham(girl, boy))

    return results


# -------------------------
# Scoring
# -------------------------

def score_porutham_status(status: str) -> float:
    """
    Convert a porutham status string into a numeric quality in [0, 1].
    """
    s = status.lower()
    if "very good" in s:
        return 1.0
    if "good" in s:
        return 0.85
    if "safe" in s or "acceptable" in s:
        return 0.8
    if "neutral" in s or "average" in s or "weak" in s:
        return 0.6
    if "not present" in s or "unknown" in s:
        return 0.5
    if "bad" in s or "enemy" in s or "not acceptable" in s:
        return 0.2
    return 0.6  # default mild value


def compute_score(papasamya: PapasamyaResult, manglik: ManglikResult,
                  poruthams: List[PoruthamResult]) -> float:
    """
    Overall score out of 10, based on:
      - Porutham statuses
      - Papasamya difference
      - Manglik combination

    Kerala-style tweaks:
      - Rajju dosha → hard cap (even if other poruthams are good).
      - High Papasamya difference → cap.
      - Unbalanced Manglik → cap.
    """

    # 1) Poruthams → up to 6 points (base)
    if poruthams:
        avg_porutham_quality = sum(
            score_porutham_status(p.status) for p in poruthams
        ) / len(poruthams)
    else:
        avg_porutham_quality = 0.6
    porutham_score = avg_porutham_quality * 6.0  # 0..6

    # 2) Papasamya → up to 2 points
    d = papasamya.difference
    if d == 0:
        pap_score = 2.0
    elif d <= 2:
        pap_score = 1.5
    elif d <= 4:
        pap_score = 0.7
    else:
        pap_score = 0.2

    # 3) Manglik → up to 2 points
    if (manglik.girl_manglik and manglik.boy_manglik) or \
       (not manglik.girl_manglik and not manglik.boy_manglik):
        mang_score = 2.0   # balanced (both same)
    else:
        mang_score = 1.0   # some risk but not zero

    total = porutham_score + pap_score + mang_score  # base ~0..10

    # -----------------------------
    # Kerala-style HARD CAPS / FLAGS
    # -----------------------------
    has_rajju_dosha = any(
        (p.name.lower() == "rajju") and ("bad" in p.status.lower())
        for p in poruthams
    )

    has_vedha_block = any(
        (p.name.lower() == "vedha") and ("bad" in p.status.lower())
        for p in poruthams
    )

    unbalanced_manglik = (
        (manglik.girl_manglik and not manglik.boy_manglik) or
        (manglik.boy_manglik and not manglik.girl_manglik)
    )

    if has_rajju_dosha:
        total = min(total, 4.5)

    if d > 2:
        total = min(total, 5.0)

    if unbalanced_manglik:
        total = min(total, 6.0)

    if has_vedha_block:
        total = min(total, 5.5)

    return max(0.0, min(10.0, total))  # clamp 0..10


# -------------------------
# Individual analysis (career, wealth, life)
# -------------------------

def analyze_individual(person: PersonChart) -> Dict[str, Any]:
    """
    Compute career, wealth, and overall life/growth scores (0–10 range)
    based on simple jyotish logic using planets_from_lagna and current dasha.
    
    Returns:
        {
            "career_score": float,
            "career_label": str,
            "career_detail": str,
            "wealth_score": float,
            "wealth_label": str,
            "wealth_detail": str,
            "life_score": float,
            "life_label": str,
            "life_detail": str,
        }
    """
    planets = person.planets_from_lagna or {}
    d9 = person.navamsa_planets_from_lagna or {}
    current_dasha_raw = person.current_dasha or ""
    
    # Extract just the planet name from "Saturn (till 2026)" → "Saturn"
    dasha_lord = current_dasha_raw.split()[0] if current_dasha_raw else None
    
    BENEFICS = {"Jupiter", "Venus", "Moon", "Mercury"}
    MALEFICS = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}
    
    # --- CAREER SCORE --------------------------------------------------------
    def score_career() -> float:
        score = 5.0  # neutral base
        
        # 1) Benefics in kendras (1,4,7,10) support career generally
        for planet, house in planets.items():
            if house in (1, 4, 7, 10) and planet in BENEFICS:
                score += 0.4
            # Malefic in Lagna or 10th gives strength but also stress
            if house in (1, 10) and planet in MALEFICS:
                score -= 0.3
        
        # 2) Planets in 10th bhava directly impact profession
        for planet, house in planets.items():
            if house == 10:
                if planet in BENEFICS:
                    score += 0.7
                else:
                    score += 0.4
        
        # 3) Navamsa planets in 10th show hidden karma-strength
        for planet, house in d9.items():
            if house == 10:
                score += 0.4
        
        # 4) Current dasha lord placement
        if dasha_lord and dasha_lord in planets:
            h = planets[dasha_lord]
            if h in (1, 4, 5, 7, 9, 10):  # kendra/trikona
                score += 0.5
            if h in (6, 8, 12):  # dusthana
                score -= 0.7
        
        # 5) Classic career stress: Saturn/Rahu in 8 or 12
        for planet, house in planets.items():
            if planet in {"Saturn", "Rahu"} and house in (8, 12):
                score -= 0.6
        
        # Clamp to a sane range
        score = max(3.5, min(9.0, score))
        return round(score, 1)
    
    # --- WEALTH SCORE --------------------------------------------------------
    def score_wealth() -> float:
        score = 5.0
        
        # 1) Benefics in 2, 5, 9, 11 = dhana houses
        for planet, house in planets.items():
            if planet in BENEFICS and house in (2, 5, 9, 11):
                score += 0.5
            # Moon specifically in 2 or 11 is good for flow of money
            if planet == "Moon" and house in (2, 11):
                score += 0.4
        
        # 2) General support: Venus/Jupiter/Moon in strong houses
        for planet in ("Venus", "Jupiter", "Moon"):
            if planet in planets:
                h = planets[planet]
                if h in (1, 2, 4, 5, 7, 9, 10, 11):
                    score += 0.3
        
        # 3) Malefics directly in 2 or 11 can disturb cashflow
        for planet, house in planets.items():
            if house in (2, 11) and planet in MALEFICS:
                score -= 0.4
        
        # 4) Dasha tone for wealth
        if dasha_lord in ("Venus", "Jupiter", "Moon"):
            score += 0.3
        if dasha_lord and dasha_lord in planets and planets[dasha_lord] in (6, 8, 12):
            score -= 0.5
        
        # 5) Saturn or Rahu in 8th → ups/downs, sudden events
        for planet, house in planets.items():
            if planet in {"Saturn", "Rahu"} and house == 8:
                score -= 0.5
        
        score = max(3.5, min(9.0, score))
        return round(score, 1)
    
    # --- OVERALL LIFE / GROWTH SCORE ----------------------------------------
    def score_overall() -> float:
        score = 5.0
        
        # 1) Benefics in lagna give overall protection
        for planet, house in planets.items():
            if house == 1 and planet in BENEFICS:
                score += 0.6
            if house == 1 and planet in MALEFICS:
                # adds grit, but also stress
                score += 0.1
        
        # 2) Jupiter & Venus in kendras/trikonas
        for planet in ("Jupiter", "Venus"):
            if planet in planets:
                h = planets[planet]
                if h in (1, 4, 7, 10, 5, 9):
                    score += 0.6
        
        # 3) Harsh malefics in 6/8/12 reduce ease of life
        for planet, house in planets.items():
            if planet in MALEFICS and house in (6, 8, 12):
                score -= 0.5
        
        # 4) Dasha mood
        if dasha_lord == "Jupiter":
            score += 0.4
        elif dasha_lord == "Venus":
            score += 0.4
        elif dasha_lord == "Moon":
            # Moon dasha: here we treat mildly positive if Moon is not badly placed
            if "Moon" in planets and planets["Moon"] not in (6, 8, 12):
                score += 0.2
            else:
                score -= 0.2
        elif dasha_lord == "Saturn":
            score -= 0.3
        
        score = max(3.5, min(9.0, score))
        return round(score, 1)
    
    career_score = score_career()
    wealth_score = score_wealth()
    overall_score = score_overall()
    
    # --- LABELS ---
    if career_score >= 8:
        career_label = "Strong career potential (good long-term growth)"
    elif career_score >= 6:
        career_label = "Good/steady career potential"
    elif career_score >= 4:
        career_label = "Average, requires effort and right choices"
    else:
        career_label = "Challenging career pattern"

    if wealth_score >= 7.5:
        wealth_label = "Exceptional / very strong wealth potential"
    elif wealth_score >= 6.0:
        wealth_label = "Strong wealth potential"
    elif wealth_score >= 4.5:
        wealth_label = "Good financial potential over time"
    elif wealth_score >= 3.0:
        wealth_label = "Average, finances depend heavily on choices"
    else:
        wealth_label = "Financial pattern requires care"

    if overall_score >= 8:
        life_label = "Overall life pattern looks strong with good growth potential."
    elif overall_score >= 6:
        life_label = "Overall life pattern is good, with normal ups and downs."
    elif overall_score >= 4:
        life_label = "Mixed life pattern – some good areas, some lessons."
    else:
        life_label = "Challenging life pattern – needs conscious effort."

    # --- DETAILS ---
    # Helper to list planets in houses
    def planets_in_houses(pdict, houses):
        return [p for p, h in pdict.items() if h in houses]
    
    career_detail = (
        "CAREER ANALYSIS (Transparent Jyotish Rules)\n"
        "--------------------------------------------\n"
        f"Current Dasha: {current_dasha_raw} (Lord: {dasha_lord or 'Unknown'})\n"
        f"Planets from Lagna: {dict(planets)}\n"
        f"Navamsa planets: {dict(d9)}\n\n"
        "CAREER SCORING LOGIC:\n"
        "1) Benefics in kendras (1,4,7,10): +0.4 each\n"
        "2) Malefics in 1st or 10th: -0.3 each (stress but strength)\n"
        "3) Benefics in 10th: +0.7 each; Malefics in 10th: +0.4 each\n"
        "4) Navamsa planets in 10th: +0.4 each\n"
        "5) Dasha lord in kendra/trikona (1,4,5,7,9,10): +0.5\n"
        "6) Dasha lord in dusthana (6,8,12): -0.7\n"
        "7) Saturn/Rahu in 8th or 12th: -0.6 each\n\n"
        f"10th house planets (Rasi): {planets_in_houses(planets, [10])}\n"
        f"10th house planets (Navamsa): {planets_in_houses(d9, [10])}\n"
        f"Kendras (1,4,7,10) benefics: {[p for p,h in planets.items() if h in (1,4,7,10) and p in BENEFICS]}\n\n"
        f"Final Career Score: {career_score}/10\n"
        f"Interpretation: {career_label}\n"
    )
    
    wealth_detail = (
        "WEALTH / INCOME ANALYSIS\n"
        "------------------------\n"
        f"Planets from Lagna: {dict(planets)}\n\n"
        "WEALTH SCORING LOGIC:\n"
        "1) Benefics in dhana houses (2,5,9,11): +0.5 each\n"
        "2) Moon in 2nd or 11th: +0.4 (cashflow)\n"
        "3) Venus/Jupiter/Moon in strong houses (1,2,4,5,7,9,10,11): +0.3 each\n"
        "4) Malefics in 2nd or 11th: -0.4 each (disturbs flow)\n"
        "5) Dasha lord is Venus/Jupiter/Moon: +0.3\n"
        "6) Dasha lord in dusthana (6,8,12): -0.5\n"
        "7) Saturn/Rahu in 8th: -0.5 each (sudden ups/downs)\n\n"
        f"2nd house planets: {planets_in_houses(planets, [2])}\n"
        f"11th house planets: {planets_in_houses(planets, [11])}\n"
        f"5th house planets: {planets_in_houses(planets, [5])}\n"
        f"9th house planets: {planets_in_houses(planets, [9])}\n\n"
        f"Final Wealth Score: {wealth_score}/10\n"
        f"Interpretation: {wealth_label}\n"
    )
    
    life_detail = (
        "OVERALL LIFE / GROWTH ANALYSIS\n"
        "-------------------------------\n"
        f"Planets from Lagna: {dict(planets)}\n\n"
        "OVERALL LIFE SCORING LOGIC:\n"
        "1) Benefics in Lagna (1st): +0.6 (protection)\n"
        "2) Malefics in Lagna: +0.1 (grit but stress)\n"
        "3) Jupiter/Venus in kendras/trikonas (1,4,5,7,9,10): +0.6 each\n"
        "4) Malefics in dusthana (6,8,12): -0.5 each (reduces ease)\n"
        "5) Dasha lord Jupiter/Venus: +0.4; Moon (well-placed): +0.2; Saturn: -0.3\n\n"
        f"Lagna (1st) planets: {planets_in_houses(planets, [1])}\n"
        f"Jupiter position: {planets.get('Jupiter', 'Not found')}\n"
        f"Venus position: {planets.get('Venus', 'Not found')}\n"
        f"Dasha Lord: {dasha_lord or 'Unknown'}\n\n"
        f"Final Overall Score: {overall_score}/10\n"
        f"Interpretation: {life_label}\n"
    )

    return {
        "career_score": career_score,
        "career_label": career_label,
        "career_detail": career_detail,
        "wealth_score": wealth_score,
        "wealth_label": wealth_label,
        "wealth_detail": wealth_detail,
        "life_score": overall_score,
        "life_label": life_label,
        "life_detail": life_detail,
    }


# -------------------------
# Overall match computation
# -------------------------

def compute_overall_match(girl: PersonChart, boy: PersonChart) -> OverallMatchResult:
    papasamya = papasamya_match(girl, boy)
    manglik = manglik_match(girl, boy)
    poruthams = compute_poruthams(girl, boy)

    score_estimate = compute_score(papasamya, manglik, poruthams)

    # ----- Extract key danger / safety flags -----
    rajju_result = next((p for p in poruthams if p.name.lower() == "rajju"), None)
    vedha_result = next((p for p in poruthams if p.name.lower() == "vedha"), None)

    has_rajju_dosha = bool(
        rajju_result and ("bad" in rajju_result.status.lower())
    )
    rajju_safe = bool(
        rajju_result and ("safe" in rajju_result.status.lower())
    )

    has_vedha_block = bool(
        vedha_result and ("safe" not in vedha_result.status.lower())
    )
    vedha_safe = bool(
        vedha_result and ("safe" in vedha_result.status.lower())
    )

    d = papasamya.difference
    girl_m = manglik.girl_manglik
    boy_m = manglik.boy_manglik
    unbalanced_manglik = (girl_m != boy_m)

    lines: List[str] = []
    lines.append(f"Astro score (with Kerala caps) ≈ {score_estimate:.1f}/10.")

    if has_rajju_dosha:
        lines.append(
            "• **Rajju**: Rajju dosha is present (both stars fall in the same Rajju group). "
            "In strict Kerala matching this is treated as a serious NO for marriage, "
            "even if other poruthams look good."
        )
    elif rajju_safe:
        lines.append(
            "• **Rajju**: SAFE – bride and groom fall in different Rajju groups, "
            "so there is no Rajju dosha."
        )
    else:
        lines.append(
            "• **Rajju**: Could not be fully evaluated from the internal table (status Unknown)."
        )

    if has_vedha_block:
        lines.append(
            "• **Vedha**: Stars form a Vedha pair / obstruction. This is a significant caution factor."
        )
    elif vedha_safe:
        lines.append(
            "• **Vedha**: SAFE – no obstructing Vedha pair between their nakshatras."
        )

    if d == 0:
        lines.append(
            f"• **Papasamya**: Thulya Papam (difference {d}) – perfectly balanced papa points."
        )
    elif d <= 2:
        lines.append(
            f"• **Papasamya**: Acceptable (difference {d}) – within Kerala limit."
        )
    else:
        lines.append(
            f"• **Papasamya**: High difference ({d}), which many Kerala astrologers "
            "treat as NOT acceptable unless there are strong mitigating factors."
        )

    if girl_m and boy_m:
        lines.append(
            "• **Kuja dosha (Manglik)**: Both are Manglik → dosha tends to balance/cancel in pair."
        )
    elif not girl_m and not boy_m:
        lines.append(
            "• **Kuja dosha (Manglik)**: Neither chart is Manglik → no Kuja dosha issue."
        )
    else:
        who = "girl" if girl_m else "boy"
        lines.append(
            f"• **Kuja dosha (Manglik)**: Only the {who} is Manglik. "
            "This is considered a sensitive mismatch; remedies or detailed personal analysis are recommended."
        )

    if has_rajju_dosha:
        level = (
            "Traditional verdict: NOT RECOMMENDED as a marriage match due to Rajju dosha, "
            "even though the computed score is shown for transparency."
        )
    elif d > 2:
        level = (
            "Traditional verdict: Borderline / often rejected in strict Kerala matching "
            "because of high Papasamya difference, even if other poruthams are supportive."
        )
    elif has_vedha_block:
        level = (
            "Verdict: Match has an obstruction (Vedha); many astrologers will be cautious, "
            "and may accept only if other factors and individual charts are very strong."
        )
    else:
        if score_estimate >= 8.5:
            level = "Verdict: Excellent & safe match with strong overall compatibility."
        elif score_estimate >= 7.0:
            level = "Verdict: Good & generally safe match with solid long-term potential."
        elif score_estimate >= 5.5:
            level = "Verdict: Average / workable match – depends on mutual understanding and maturity."
        else:
            level = "Verdict: Weak match – noticeable astrological challenges; proceed only with caution."

    lines.append("")
    lines.append(level)

    final_comment = "\n".join(lines)

    return OverallMatchResult(
        papasamya=papasamya,
        manglik=manglik,
        poruthams=poruthams,
        final_comment=final_comment,
        score_estimate=score_estimate,
    )


# -------------------------
# HTML report generation (with modal help)
# -------------------------

def html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def generate_html_report(girl: PersonChart, boy: PersonChart, match: OverallMatchResult) -> str:
    def attr_escape(text: str) -> str:
        return html_escape(text).replace("\n", "&#10;")

    rows = []
    for p in match.poruthams:
        combined_help = (p.detail or "") + ("\n\n" + p.logic if p.logic else "")
        title_attr = attr_escape(p.name)
        logic_attr = attr_escape(combined_help.strip())

        rows.append(
            "<tr>"
            f"<td>{html_escape(p.name)}</td>"
            f"<td>{html_escape(p.status)}</td>"
            f"<td>{html_escape(p.comment)}</td>"
            f"<td>{html_escape(p.detail)}</td>"
            f"<td><button type=\"button\" "
            f"data-title=\"{title_attr}\" "
            f"data-logic=\"{logic_attr}\" "
            f"onclick=\"showHelpFromButton(this)\">?</button></td>"
            "</tr>"
        )

    porutham_rows = "\n".join(rows)

    girl_an = analyze_individual(girl)
    boy_an = analyze_individual(boy)

    rajju_rows = []
    for group, info in RAJJU_GROUPS.items():
        body = info["body"]
        nak_list = ", ".join(info["nakshatras"])
        rajju_rows.append(
            f"<tr><td>{html_escape(group)} Rajju</td>"
            f"<td>{html_escape(body)}</td>"
            f"<td>{html_escape(nak_list)}</td></tr>"
        )
    rajju_table_html = "\n".join(rajju_rows)

    yoni_to_naks: Dict[str, List[str]] = {}
    for nak_norm, (yoni_key, y_san, animal, enemy_key) in YONI_BY_NAK.items():
        yoni_to_naks.setdefault(yoni_key, []).append(nak_norm)

    yoni_rows = []
    for y_key, (y_san, animal, enemy) in YONI_META.items():
        naks = yoni_to_naks.get(y_key, [])
        nak_list = ", ".join(n.capitalize() for n in naks) if naks else "—"
        yoni_rows.append(
            f"<tr><td>{html_escape(y_san)}</td>"
            f"<td>{html_escape(animal)}</td>"
            f"<td>{html_escape(enemy)}</td>"
            f"<td>{html_escape(nak_list)}</td></tr>"
        )
    yoni_table_html = "\n".join(yoni_rows)

    joint_life_avg = (girl_an["life_score"] + boy_an["life_score"]) / 2
    if joint_life_avg >= 8:
        joint_text = "As a couple, they have strong combined life and growth potential (both charts supportive)."
    elif joint_life_avg >= 6:
        joint_text = "As a couple, they show good overall growth with normal ups and downs."
    elif joint_life_avg >= 4:
        joint_text = "As a couple, the pattern is mixed – requires conscious cooperation to get the best results."
    else:
        joint_text = "As a couple, there are notable challenges; success depends heavily on awareness and effort."

    girl_career_help = attr_escape(girl_an["career_detail"])
    girl_wealth_help = attr_escape(girl_an["wealth_detail"])
    girl_life_help = attr_escape(girl_an["life_detail"])

    boy_career_help = attr_escape(boy_an["career_detail"])
    boy_wealth_help = attr_escape(boy_an["wealth_detail"])
    boy_life_help = attr_escape(boy_an["life_detail"])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Kerala Marriage Match Report</title>
<style>
body {{
    font-family: Arial, sans-serif;
    margin: 20px;
    background: #f6f7fb;
}}
h1, h2, h3 {{
    color: #333;
}}
.card {{
    background: #fff;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 20px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}}
table {{
    border-collapse: collapse;
    width: 100%;
    margin-top: 10px;
}}
th, td {{
    border: 1px solid #ccc;
    padding: 8px 10px;
    text-align: left;
    font-size: 14px;
}}
th {{
    background: #e8ebf7;
}}
button {{
    padding: 4px 8px;
    border-radius: 6px;
    border: 1px solid #999;
    cursor: pointer;
    background: #f0f0f0;
}}
button:hover {{
    background: #e0e0e0;
}}

/* Modal */
#helpModalOverlay {{
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.4);
    z-index: 1000;
}}
#helpModal {{
    background: #fff;
    max-width: 700px;
    margin: 80px auto;
    padding: 16px 20px;
    border-radius: 10px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.2);
}}
#helpModal h3 {{
    margin-top: 0;
}}
#helpModal pre {{
    white-space: pre-wrap;
    font-family: inherit;
}}
#helpClose {{
    float: right;
    cursor: pointer;
    font-weight: bold;
}}
</style>
<script>
function showHelpFromButton(btn) {{
    var title = btn.getAttribute('data-title') || '';
    var text = btn.getAttribute('data-logic') || '';
    text = text.replace(/&#10;/g, '\\n');
    document.getElementById('helpTitle').innerText = title;
    document.getElementById('helpBody').innerText = text;
    document.getElementById('helpModalOverlay').style.display = 'block';
}}
function closeHelp() {{
    document.getElementById('helpModalOverlay').style.display = 'none';
}}
</script>
</head>
<body>

<h1>Kerala Marriage Matching Report</h1>

<div class="card">
  <h2>Basic Details</h2>
  <table>
    <tr>
      <th>Attribute</th>
      <th>Girl</th>
      <th>Boy</th>
    </tr>
    <tr>
      <td>Name</td>
      <td>{html_escape(girl.name)}</td>
      <td>{html_escape(boy.name)}</td>
    </tr>
    <tr>
      <td>DOB / TOB / Place</td>
      <td>{html_escape(girl.dob)} &nbsp; {html_escape(girl.tob)}<br>{html_escape(girl.place)}</td>
      <td>{html_escape(boy.dob)} &nbsp; {html_escape(boy.tob)}<br>{html_escape(boy.place)}</td>
    </tr>
    <tr>
      <td>Rasi (Moon sign)</td>
      <td>{html_escape(girl.rasi)}</td>
      <td>{html_escape(boy.rasi)}</td>
    </tr>
    <tr>
      <td>Nakshatra / Pada</td>
      <td>{html_escape(girl.nakshatra)} (Pada {girl.nakshatra_pada})</td>
      <td>{html_escape(boy.nakshatra)} (Pada {boy.nakshatra_pada})</td>
    </tr>
    <tr>
      <td>Lagna</td>
      <td>{html_escape(girl.lagna)}</td>
      <td>{html_escape(boy.lagna)}</td>
    </tr>
    <tr>
      <td>Current Dasha</td>
      <td>{html_escape(girl.current_dasha)}</td>
      <td>{html_escape(boy.current_dasha)}</td>
    </tr>
  </table>
</div>

<div class="card">
  <h2>Papasamya (Papa Points)</h2>
  <table>
    <tr>
      <th>Side</th>
      <th>Total Papam</th>
    </tr>
    <tr>
      <td>Girl</td>
      <td>{match.papasamya.girl_total}</td>
    </tr>
    <tr>
      <td>Boy</td>
      <td>{match.papasamya.boy_total}</td>
    </tr>
    <tr>
      <td>Difference</td>
      <td>{match.papasamya.difference}</td>
    </tr>
  </table>
  <p><strong>Verdict:</strong> {html_escape(match.papasamya.verdict)}</p>
</div>

<div class="card">
  <h2>Kuja Dosha (Manglik)</h2>
  <table>
    <tr>
      <th>Side</th>
      <th>Manglik?</th>
    </tr>
    <tr>
      <td>Girl</td>
      <td>{"Yes" if match.manglik.girl_manglik else "No"}</td>
    </tr>
    <tr>
      <td>Boy</td>
      <td>{"Yes" if match.manglik.boy_manglik else "No"}</td>
    </tr>
  </table>
  <p><strong>Combined Verdict:</strong> {html_escape(match.manglik.combined_verdict)}</p>
</div>

<div class="card">
  <h2>Porutham Summary (Kerala Style)</h2>
  <table>
    <tr>
      <th>Porutham</th>
      <th>Status</th>
      <th>What this checks / Significance</th>
      <th>Pair-specific reasoning</th>
      <th>Help</th>
    </tr>
    {porutham_rows}
  </table>
</div>

<div class="card">
  <h2>Individual Analysis – Girl ({html_escape(girl.name)})</h2>
  <p><strong>Career:</strong> {html_escape(girl_an['career_label'])} (≈ {girl_an['career_score']:.1f}/10)
     <button type="button"
       data-title="Girl – Career analysis"
       data-logic="{girl_career_help}"
       onclick="showHelpFromButton(this)">details</button>
  </p>
  <p><strong>Wealth:</strong> {html_escape(girl_an['wealth_label'])} (≈ {girl_an['wealth_score']:.1f}/10)
     <button type="button"
       data-title="Girl – Wealth analysis"
       data-logic="{girl_wealth_help}"
       onclick="showHelpFromButton(this)">details</button>
  </p>
  <p><strong>Overall life/growth:</strong> {html_escape(girl_an['life_label'])}
     <button type="button"
       data-title="Girl – Life pattern"
       data-logic="{girl_life_help}"
       onclick="showHelpFromButton(this)">details</button>
  </p>
</div>

<div class="card">
  <h2>Individual Analysis – Boy ({html_escape(boy.name)})</h2>
  <p><strong>Career:</strong> {html_escape(boy_an['career_label'])} (≈ {boy_an['career_score']:.1f}/10)
     <button type="button"
       data-title="Boy – Career analysis"
       data-logic="{boy_career_help}"
       onclick="showHelpFromButton(this)">details</button>
  </p>
  <p><strong>Wealth:</strong> {html_escape(boy_an['wealth_label'])} (≈ {boy_an['wealth_score']:.1f}/10)
     <button type="button"
       data-title="Boy – Wealth analysis"
       data-logic="{boy_wealth_help}"
       onclick="showHelpFromButton(this)">details</button>
  </p>
  <p><strong>Overall life/growth:</strong> {html_escape(boy_an['life_label'])}
     <button type="button"
       data-title="Boy – Life pattern"
       data-logic="{boy_life_help}"
       onclick="showHelpFromButton(this)">details</button>
  </p>
</div>

<div class="card">
  <h2>Joint Growth / Life Outlook</h2>
  <p>{html_escape(joint_text)}</p>
</div>

<div class="card">
  <h2>Reference / Knowledge Base</h2>

  <h3>Rajju groups (Nakshatra → body part)</h3>
  <p>This table is what the Rajju porutham logic is based on. If bride and groom
     stars fall in the <strong>same</strong> Rajju group, it is Rajju dosha.
     Different groups → SAFE.</p>
  <table>
    <tr>
      <th>Rajju Group</th>
      <th>Body Part</th>
      <th>Nakshatras in this Rajju</th>
    </tr>
    {rajju_table_html}
  </table>

  <h3>Yoni groups (animal symbols & enemies)</h3>
  <p>This table shows each Yoni (animal), the <strong>inimical Yoni</strong>,
     and which nakshatras belong to that Yoni. Yoni porutham here uses a simple rule:</p>
  <ul>
    <li>Same Yoni → Very Good</li>
    <li>Enemy Yoni pair → Bad</li>
    <li>Anything else → Neutral</li>
  </ul>
  <table>
    <tr>
      <th>Yoni (Sanskrit)</th>
      <th>Animal</th>
      <th>Inimical Yoni</th>
      <th>Nakshatras belonging to this Yoni</th>
    </tr>
    {yoni_table_html}
  </table>

  <p>Using this, anyone can manually check: for example, if girl is Purva Phalguni
     and boy is Vishakha, you can see which Rajju each falls under and which Yoni
     animals they belong to, and confirm whether the script's
     &quot;SAFE Rajju&quot; and &quot;Neutral/Good Yoni&quot; decisions are consistent.</p>
</div>

<div class="card">
  <h2>Overall Match Verdict</h2>
  <p><strong>Computed Score:</strong> {match.score_estimate:.1f} / 10</p>
  <p><strong>Conclusion:</strong> {html_escape(match.final_comment)}</p>
</div>

<div id="helpModalOverlay" onclick="closeHelp()">
  <div id="helpModal" onclick="event.stopPropagation();">
    <span id="helpClose" onclick="closeHelp()">✕</span>
    <h3 id="helpTitle">Porutham – How it works</h3>
    <pre id="helpBody"></pre>
  </div>
</div>

</body>
</html>
"""
    return html


# -------------------------
# Input handling
# -------------------------

def normalize_planet_keys(raw: Dict[str, Any]) -> Dict[str, int]:
    """
    Normalize planet names so JSON can use any case:
      'mars', 'MARS', 'MaRs' -> 'Mars'
      'moon', 'MOON' -> 'Moon'
    """
    normalized: Dict[str, int] = {}
    for k, v in raw.items():
        key = k.strip().lower()
        if key == "sun":
            pname = "Sun"
        elif key == "moon":
            pname = "Moon"
        elif key == "mars":
            pname = "Mars"
        elif key == "mercury":
            pname = "Mercury"
        elif key == "jupiter":
            pname = "Jupiter"
        elif key == "venus":
            pname = "Venus"
        elif key == "saturn":
            pname = "Saturn"
        elif key == "rahu":
            pname = "Rahu"
        elif key == "ketu":
            pname = "Ketu"
        else:
            pname = k.strip().title()
        normalized[pname] = int(v)
    return normalized


def load_input(path: Path) -> Tuple[PersonChart, PersonChart]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    def build_person(d: Dict[str, Any]) -> PersonChart:
        planets_rasi = normalize_planet_keys(d["planets_from_lagna"])
        planets_d9 = normalize_planet_keys(d["navamsa_planets_from_lagna"])

        if "Moon" not in planets_rasi:
            raise ValueError(f"planets_from_lagna for {d.get('name', 'Unknown')} must include 'Moon'")
        if "Venus" not in planets_rasi:
            raise ValueError(f"planets_from_lagna for {d.get('name', 'Unknown')} must include 'Venus'")

        return PersonChart(
            name=d["name"],
            dob=d["dob"],
            tob=d["tob"],
            place=d["place"],
            rasi=d["rasi"],
            nakshatra=d["nakshatra"],
            nakshatra_pada=int(d["nakshatra_pada"]),
            lagna=d["lagna"],
            current_dasha=d["current_dasha"],
            planets_from_lagna=planets_rasi,
            navamsa_planets_from_lagna=planets_d9,
        )

    girl = build_person(data["girl"])
    boy = build_person(data["boy"])
    return girl, boy


# -------------------------
# Interactive input helpers
# -------------------------

PLANET_LIST = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

RASI_OPTIONS = [
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena",
]

LAGNA_OPTIONS = RASI_OPTIONS

NAKSHATRA_OPTIONS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigasira", "Ardra", "Punarvasu",
    "Pushya", "Ashlesha", "Magha", "Purvaphalguni", "Uttaraphalguni", "Hasta",
    "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshta", "Moola", "Purvashadha",
    "Uttarashadha", "Shravana", "Dhanishta", "Satabhisha", "Purvabhadra",
    "Uttarabhadrapada", "Revati",
]


def prompt_choice(prompt: str, options: List[str]) -> str:
    print()
    print(prompt)
    for i, opt in enumerate(options, start=1):
        print(f"  {i}. {opt}")
    while True:
        s = input("Enter option number or type a custom value: ").strip()
        if not s:
            print("Please enter something.")
            continue
        if s.isdigit():
            idx = int(s)
            if 1 <= idx <= len(options):
                return options[idx - 1]
            else:
                print(f"Please enter a number between 1 and {len(options)}, or type a custom value.")
        else:
            return s


def prompt_int(prompt: str, minimum: int = None, maximum: int = None, allow_blank: bool = False) -> int | None:
    while True:
        s = input(prompt).strip()
        if not s and allow_blank:
            return None
        try:
            val = int(s)
        except ValueError:
            print("Please enter a valid integer.")
            continue
        if minimum is not None and val < minimum:
            print(f"Value must be >= {minimum}.")
            continue
        if maximum is not None and val > maximum:
            print(f"Value must be <= {maximum}.")
            continue
        return val


def prompt_planet_houses(label: str) -> Dict[str, int]:
    print()
    print("------------------------------------------------------------")
    print(f"ENTER PLANET HOUSE PLACEMENTS FOR {label}")
    print("------------------------------------------------------------")
    print("IMPORTANT NOTES:")
    print("• Lagna is considered the 1st house.")
    print("• For each house, type planets present there, comma-separated.")
    print("• Leave blank if no planets in that house.")
    print()
    print("ACCEPTED PLANET NAMES (case-insensitive):")
    print("  Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu")
    print()
    print("EXAMPLES of valid input:")
    print("  Sun, Moon")
    print("  mars jupiter")
    print("  VENUS")
    print("  (leave blank if no planets in that house)")
    print("------------------------------------------------------------")
    print()

    def canon_planet_name(raw: str) -> str | None:
        s = raw.strip().lower()
        if not s:
            return None
        mapping = {
            "sun": "Sun",
            "moon": "Moon",
            "mars": "Mars",
            "mercury": "Mercury",
            "jupiter": "Jupiter",
            "venus": "Venus",
            "saturn": "Saturn",
            "rahu": "Rahu",
            "ketu": "Ketu",
        }
        return mapping.get(s, raw.strip().title())

    placements: Dict[str, int] = {}

    for house in range(1, 13):
        print()
        prompt = (
            f"House {house} from Lagna — enter planets here "
            "(comma-separated, blank = none): "
        )
        entry = input(prompt).strip()
        if not entry:
            continue

        raw_items = [x for x in entry.replace(",", " ").split(" ") if x.strip()]

        for raw in raw_items:
            name = canon_planet_name(raw)
            if not name:
                continue

            if name in placements:
                print(
                    f"  ⚠️  Note: {name} already assigned to house "
                    f"{placements[name]}, ignored duplicate in house {house}"
                )
                continue

            placements[name] = house
            print(f"  → Placed {name} in house {house}")

    return placements


def build_person_interactive(role: str) -> Dict[str, Any]:
    print()
    print("=" * 60)
    print(f"Enter details for the {role}:")
    print("=" * 60)

    name = input(f"{role} name: ").strip() or role
    dob = input(f"{role} DOB (free text, e.g. 03-07-1995): ").strip()
    tob = input(f"{role} TOB (time, e.g. 10:04 AM): ").strip()
    place = input(f"{role} place of birth: ").strip()

    rasi = prompt_choice(f"{role} Rasi (Moon sign):", RASI_OPTIONS)
    nakshatra = prompt_choice(f"{role} Nakshatra:", NAKSHATRA_OPTIONS)
    nakshatra_pada = prompt_int(f"{role} Nakshatra Pada (1-4): ", minimum=1, maximum=4)
    lagna = prompt_choice(f"{role} Lagna (Ascendant sign):", LAGNA_OPTIONS)

    current_dasha = input(
        f"{role} current mahadasha planet (e.g. 'Moon', 'Saturn', 'Venus'; "
        "you can also type full like 'Saturn (till 2026)'): "
    ).strip() or "Unknown"

    print()
    print(f"Now enter Rasi chart positions (houses from Lagna) for the {role}:")
    planets_rasi = prompt_planet_houses(f"{role} – Rasi chart")
    print()
    print(f"Now enter Navamsa (D9) positions (houses from Navamsa Lagna) for the {role}:")
    planets_d9 = prompt_planet_houses(f"{role} – Navamsa (D9) chart")

    if "Moon" not in planets_rasi:
        print("WARNING: Moon was not entered in Rasi planets – adding dummy placeholder in 1st house.")
        planets_rasi["Moon"] = 1
    if "Venus" not in planets_rasi:
        print("WARNING: Venus was not entered in Rasi planets – adding dummy placeholder in 1st house.")
        planets_rasi["Venus"] = 1

    return {
        "name": name,
        "dob": dob,
        "tob": tob,
        "place": place,
        "rasi": rasi,
        "nakshatra": nakshatra,
        "nakshatra_pada": nakshatra_pada,
        "lagna": lagna,
        "current_dasha": current_dasha,
        "planets_from_lagna": planets_rasi,
        "navamsa_planets_from_lagna": planets_d9,
    }


def interactive_build_json() -> Path:
    print("No JSON file argument provided.")
    print("Entering interactive mode to collect chart details and create a JSON input file.\n")

    girl_data = build_person_interactive("Girl")
    boy_data = build_person_interactive("Boy")

    data = {
        "girl": girl_data,
        "boy": boy_data,
    }

    default_name = "match_input_interactive.json"
    out_name = input(
        f"\nEnter output JSON filename "
        f"(press Enter for default '{default_name}'): "
    ).strip() or default_name

    out_path = Path(out_name).expanduser().resolve()
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nJSON input file saved as: {out_path}")
    print("This file can be reused later by running:")
    print(f"  python kerala_match_report.py {out_path.name}\n")
    return out_path


# -------------------------
# Main
# -------------------------

def main():
   
    if len(sys.argv) == 2:
        input_path = Path(sys.argv[1]).expanduser().resolve()
    else:
        webbrowser.open("https://www.prokerala.com/astrology/jathakam.php")
        input_path = interactive_build_json()

    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        sys.exit(1)

    girl, boy = load_input(input_path)
    match = compute_overall_match(girl, boy)

    output_path = input_path.with_suffix(".match_report.html")
    html = generate_html_report(girl, boy, match)
    output_path.write_text(html, encoding="utf-8")

    print(f"\nReport generated: {output_path}")
    webbrowser.open(output_path.as_uri())


if __name__ == "__main__":
    main()
