"""
Entity Resolution Service for Knowledge Graph Canonical Entity Merging.

Implements conservative alias resolution, nickname clustering, honorific stripping,
email artifact sanitization, and type-scoped canonical merging across legal documents.
"""

from __future__ import annotations

import re
import hashlib
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional, Set, Any
from loguru import logger

# ---------------------------------------------------------------------------
# Authoritative Nickname Dictionary
# Maps familiar/diminutive forms strictly to their formal counterparts.
# ---------------------------------------------------------------------------
NICKNAMES: Dict[str, str] = {
    "ken": "kenneth",
    "kenny": "kenneth",
    "jim": "james",
    "jimmy": "james",
    "bill": "william",
    "billy": "william",
    "will": "william",
    "willy": "william",
    "bob": "robert",
    "bobby": "robert",
    "rob": "robert",
    "robbie": "robert",
    "rick": "richard",
    "dick": "richard",
    "rich": "richard",
    "richie": "richard",
    "mike": "michael",
    "mikey": "michael",
    "dan": "daniel",
    "danny": "daniel",
    "jeff": "jeffrey",
    "geoff": "geoffrey",
    "dave": "david",
    "davy": "david",
    "greg": "gregory",
    "joe": "joseph",
    "joey": "joseph",
    "tom": "thomas",
    "tommy": "thomas",
    "tim": "timothy",
    "timmy": "timothy",
    "steve": "steven",
    "stevie": "steven",
    "chuck": "charles",
    "charlie": "charles",
    "chris": "christopher",
    "andy": "andrew",
    "drew": "andrew",
    "don": "donald",
    "donnie": "donald",
    "ed": "edward",
    "eddie": "edward",
    "ted": "edward",
    "tony": "anthony",
    "matt": "matthew",
    "matty": "matthew",
    "phil": "phillip",
    "ray": "raymond",
    "larry": "lawrence",
    "vince": "vincent",
    "al": "alan",
    "doug": "douglas",
    "ron": "ronald",
    "ronnie": "ronald",
    "pete": "peter",
    "gene": "eugene",
    "liz": "elizabeth",
    "beth": "elizabeth",
    "becky": "rebecca",
    "sue": "susan",
    "susie": "susan",
    "pat": "patricia",
    "patty": "patricia",
    "debbie": "debra",
    "deb": "debra",
    "barb": "barbara",
    "ben": "benjamin",
    "benny": "benjamin",
    "alex": "alexander",
    "stan": "stanley",
    "jon": "jonathan",
    "kathy": "katherine",
    "katie": "katherine",
    "cathy": "catherine",
}

# Reverse lookup for bidirectional compatibility
NICKNAME_ROOTS: Dict[str, Set[str]] = defaultdict(set)
for _nick, _formal in NICKNAMES.items():
    NICKNAME_ROOTS[_nick].add(_formal)
    NICKNAME_ROOTS[_formal].add(_nick)
    NICKNAME_ROOTS[_nick].add(_nick)
    NICKNAME_ROOTS[_formal].add(_formal)

# Honorifics & titles to strip
HONORIFICS: Set[str] = {
    "mr", "mr.", "mrs", "mrs.", "ms", "ms.", "dr", "dr.", 
    "chairman", "ceo", "cfo", "coo", "cto", "president", 
    "director", "vp", "judge", "prof", "prof.", "professor", 
    "hon", "hon.", "attorney", "esq", "esq.", "sir", "madam"
}

# Generational suffixes
SUFFIXES: Set[str] = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv"}

# Known mock/fallback artifact entities to filter out
KNOWN_MOCK_NAMES: Set[str] = {
    "meridian corp", "meridian corp.", "dr. james whitfield", "james whitfield",
    "atlas industries", "dr. linda vance", "linda vance", "robert chen",
    "alice thompson", "david ross", "greenfield partners"
}

ROUTING_OFFICE_REGEX = re.compile(r"/([A-Z]{2,4})/")
DOMAIN_REGEX = re.compile(r"@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")


def is_known_mock_entity(name: str) -> bool:
    """Check if entity is an OCR mock fallback artifact."""
    n = name.strip().lower()
    return n in KNOWN_MOCK_NAMES


def extract_routing_metadata(raw: str) -> Dict[str, Optional[str]]:
    """Extracts office and domain from email routing strings for disambiguation."""
    office = None
    domain = None
    m_off = ROUTING_OFFICE_REGEX.search(raw)
    if m_off:
        office = m_off.group(1).upper()
    m_dom = DOMAIN_REGEX.search(raw)
    if m_dom:
        domain = m_dom.group(1).lower()
    return {"office": office, "domain": domain}


def clean_person_string(raw: str) -> str:
    """Sanitize raw person mention string."""
    s = raw.strip()
    # Strip URL artifacts misclassified by NER
    if "http://" in s or "https://" in s or ".html" in s:
        return ""
    # Strip quoted printable artifacts (e.g. '=20')
    s = re.sub(r"=\d{2}", "", s)
    # Strip email routing patterns like /HOU/ECT@ECT or @ENRON or <email>
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"/[A-Za-z0-9_/-]+@[A-Za-z0-9_/-]+", "", s)
    s = re.sub(r"/[A-Za-z0-9_/-]+", "", s)
    s = re.sub(r"@[A-Za-z0-9_.-]+", "", s)
    # Strip possessive 's
    s = re.sub(r"['’]s\b", "", s)
    # Strip brackets, quotes, etc.
    s = re.sub(r"[\"\'`()\[\]<>{}:;]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_person_name(cleaned: str) -> Optional[Dict[str, Any]]:
    """Parse cleaned person string into structural components."""
    if not cleaned:
        return None
    # Check if "Last, First"
    if "," in cleaned:
        parts = cleaned.split(",", 1)
        last = parts[0].strip()
        first_part = parts[1].strip()
        tokens = first_part.split()
        first = tokens[0] if tokens else ""
        middle = " ".join(tokens[1:]) if len(tokens) > 1 else ""
        return {
            "first": first.lower(),
            "middle": middle.lower(),
            "last": last.lower(),
            "suffix": "",
            "raw_first": first,
            "raw_last": last,
            "tokens": [first] + tokens[1:] + [last],
            "is_single": False,
        }
    
    tokens = cleaned.split()
    # Strip leading honorifics
    while tokens and tokens[0].lower().rstrip(".") in HONORIFICS:
        tokens.pop(0)
    # Strip trailing suffixes
    suffix = ""
    if tokens and tokens[-1].lower().rstrip(".") in {s.rstrip(".") for s in SUFFIXES}:
        suffix = tokens.pop(-1).lower().rstrip(".")
        
    if not tokens:
        return None
    if len(tokens) == 1:
        return {
            "first": "",
            "middle": "",
            "last": tokens[0].lower(),
            "suffix": suffix,
            "raw_first": "",
            "raw_last": tokens[0],
            "tokens": tokens,
            "is_single": True,
        }
    
    first = tokens[0]
    last = tokens[-1]
    middle = " ".join(tokens[1:-1]) if len(tokens) > 2 else ""
    return {
        "first": first.lower(),
        "middle": middle.lower(),
        "last": last.lower(),
        "suffix": suffix,
        "raw_first": first,
        "raw_last": last,
        "tokens": tokens,
        "is_single": False,
    }


def are_first_names_compatible(f1: str, f2: str) -> bool:
    """Test compatibility between two first names."""
    f1 = f1.rstrip(".")
    f2 = f2.rstrip(".")
    if not f1 or not f2:
        return False
    if f1 == f2:
        return True
    # Initial match: e.g. "k" and "kenneth"
    if len(f1) == 1 and f2.startswith(f1):
        return True
    if len(f2) == 1 and f1.startswith(f2):
        return True
    # Nickname roots match
    roots1 = NICKNAME_ROOTS.get(f1, {f1}) | {f1}
    roots2 = NICKNAME_ROOTS.get(f2, {f2}) | {f2}
    if roots1 & roots2:
        return True
    return False




def are_middle_names_compatible(m1: str, m2: str) -> bool:
    """Check if middle names/initials are compatible without contradiction."""
    if not m1 or not m2:
        return True
    m1_tokens = [t.rstrip(".") for t in m1.split()]
    m2_tokens = [t.rstrip(".") for t in m2.split()]
    i1 = m1_tokens[0][0] if m1_tokens and m1_tokens[0] else ""
    i2 = m2_tokens[0][0] if m2_tokens and m2_tokens[0] else ""
    if i1 and i2 and i1 != i2:
        return False
    return True


def choose_canonical_display_name(members: List[Dict[str, Any]]) -> str:
    """
    Selects the best display name from cluster members:
    - Prefers complete names (full first name over initial, formal over nickname).
    - Prefers title case.
    - Factors in frequency.
    """
    best_cand = None
    best_score = -1e9
    
    for cand in members:
        p = cand["parsed"]
        score = 0
        cleaned = cand["cleaned"]
        
        # 1. Full first name (not initial)
        if len(p["first"]) > 1:
            score += 200
        elif len(p["first"]) == 1:
            score -= 50
            
        # 2. Formal name over nickname (e.g. Kenneth over Ken)
        if p["first"] in NICKNAMES.values():
            score += 50
            
        # 3. Middle name presence
        if len(p["middle"]) > 0:
            score += 20
            
        # 4. Proper capitalization
        if cleaned.istitle():
            score += 40
        elif cleaned.isupper() or cleaned.islower():
            score -= 30
            
        # 5. Mention frequency in dataset
        score += cand["count"] * 2
        
        # 6. Suffix bonus
        if p.get("suffix"):
            score += 5
            
        if score > best_score:
            best_score = score
            best_cand = cand
            
    name = best_cand["cleaned"] if best_cand else "Unknown"
    if name.islower() or name.isupper():
        name = " ".join(t.capitalize() for t in name.split())
    return name


class EntityResolutionService:
    """
    Resolves, clusters, and canonicalizes entity mentions across documents.
    Scoped strictly by entity type to guarantee zero cross-type merges.
    """

    def __init__(self) -> None:
        self._raw_to_canonical_name: Dict[Tuple[str, str], str] = {} # (type, raw) -> canonical_name
        self._raw_to_canonical_id: Dict[Tuple[str, str], str] = {}   # (type, raw) -> canonical_id
        self._clusters: Dict[str, List[Dict[str, Any]]] = defaultdict(list) # type -> list of cluster dicts
        self._flagged_ambiguous: List[Dict[str, Any]] = []

    def get_flagged_ambiguous(self) -> List[Dict[str, Any]]:
        return self._flagged_ambiguous

    def cluster_entities(self, mentions_by_type: Dict[str, Counter]) -> None:
        """
        Cluster all entity mentions partitioned by entity type.
        Ensures 100% type-scoped clustering with zero cross-type merging.
        """
        self._raw_to_canonical_name.clear()
        self._raw_to_canonical_id.clear()
        self._clusters.clear()
        self._flagged_ambiguous.clear()

        for raw_cat, counter in mentions_by_type.items():
            cat = raw_cat.lower().rstrip("s")
            if cat in ("person", "people"):
                self._cluster_people(counter, cat="person")
            elif cat in ("organization", "org"):
                self._cluster_organizations(counter, cat="organization")
            else:
                self._cluster_generic(counter, cat=cat)

    def _cluster_people(self, counter: Counter, cat: str = "person") -> None:
        """Clusters person entities using conservative rule-based matching."""
        parsed_items: List[Dict[str, Any]] = []
        for raw, count in counter.items():
            # Check mock filter
            if is_known_mock_entity(raw):
                continue
            cleaned = clean_person_string(raw)
            if not cleaned:
                continue
            parsed = parse_person_name(cleaned)
            if not parsed:
                continue
            routing = extract_routing_metadata(raw)
            parsed_items.append({
                "raw": raw,
                "cleaned": cleaned,
                "count": count,
                "parsed": parsed,
                "routing": routing,
            })

        multi_token = [item for item in parsed_items if not item["parsed"]["is_single"]]
        single_token = [item for item in parsed_items if item["parsed"]["is_single"]]

        last_name_buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for item in multi_token:
            last_name_buckets[item["parsed"]["last"]].append(item)

        clusters: List[List[Dict[str, Any]]] = []

        for last_name, items in last_name_buckets.items():
            sub_clusters: List[Dict[str, Any]] = []
            for item in items:
                f = item["parsed"]["first"]
                m = item["parsed"]["middle"]
                s = item["parsed"]["suffix"]
                item_routing = item["routing"]
                
                matched_sc = None
                for sc in sub_clusters:
                    compatible = True
                    for other in sc["items"]:
                        of = other["parsed"]["first"]
                        om = other["parsed"]["middle"]
                        os = other["parsed"]["suffix"]
                        other_routing = other["routing"]
                        
                        # Generational suffix check (e.g. Jr vs Sr)
                        if s and os and s != os:
                            compatible = False
                            break
                        # First name compatibility check
                        if not are_first_names_compatible(f, of):
                            compatible = False
                            break
                        # Middle initial compatibility check
                        if not are_middle_names_compatible(m, om):
                            compatible = False
                            break
                        # Email routing conflict check (different offices or company domains)
                        if item_routing["office"] and other_routing["office"] and item_routing["office"] != other_routing["office"]:
                            compatible = False
                            break
                        if item_routing["domain"] and other_routing["domain"] and item_routing["domain"] != other_routing["domain"]:
                            compatible = False
                            break

                    if compatible:
                        if matched_sc is None:
                            matched_sc = sc
                        else:
                            matched_sc = "AMBIGUOUS"
                            break
                            
                if matched_sc == "AMBIGUOUS":
                    self._flagged_ambiguous.append({
                        "item": item["raw"],
                        "category": "person",
                        "reason": f"Matches multiple distinct first-name clusters under last name '{last_name}'",
                        "candidates": [sc["items"][0]["raw"] for sc in sub_clusters]
                    })
                    sub_clusters.append({"items": [item]})
                elif matched_sc is not None:
                    matched_sc["items"].append(item)
                else:
                    sub_clusters.append({"items": [item]})

            for sc in sub_clusters:
                clusters.append(sc["items"])

        # Single-token handling: conservative flagging, kept separate
        for item in single_token:
            token = item["parsed"]["last"]
            matching_last = [c for c in clusters if c[0]["parsed"]["last"] == token]
            if len(matching_last) == 1:
                self._flagged_ambiguous.append({
                    "item": item["raw"],
                    "category": "person",
                    "reason": f"Single-token last name matches 1 candidate cluster ('{matching_last[0][0]['cleaned']}') - kept separate to prevent false merge",
                    "candidates": [matching_last[0][0]["raw"]]
                })
            elif len(matching_last) > 1:
                self._flagged_ambiguous.append({
                    "item": item["raw"],
                    "category": "person",
                    "reason": f"Single-token name matches {len(matching_last)} distinct clusters with last name '{token}'",
                    "candidates": [c[0]["raw"] for c in matching_last[:3]]
                })
            clusters.append([item])

        # Register canonical IDs and names
        for c in clusters:
            canonical_display = choose_canonical_display_name(c)
            canon_norm = canonical_display.lower().strip()
            cluster_id = f"ent_person_{hashlib.sha256(canon_norm.encode('utf-8')).hexdigest()[:12]}"
            
            c_info = {
                "canonical_id": cluster_id,
                "canonical_name": canonical_display,
                "category": "person",
                "members": [x["raw"] for x in c],
                "total_count": sum(x["count"] for x in c),
            }
            self._clusters["person"].append(c_info)
            
            for x in c:
                self._raw_to_canonical_name[("person", x["raw"])] = canonical_display
                self._raw_to_canonical_id[("person", x["raw"])] = cluster_id

    def _cluster_organizations(self, counter: Counter, cat: str = "organization") -> None:
        """Clusters organization entities by normalized corporate identity."""
        cleaned_groups: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        for raw, count in counter.items():
            if is_known_mock_entity(raw):
                continue
            norm = re.sub(r"\s+", " ", raw.strip()).lower()
            if not norm:
                continue
            cleaned_groups[norm].append((raw, count))

        for norm_key, items in cleaned_groups.items():
            # Pick the cleanest display name (most frequent, title cased if available)
            best_raw = max(items, key=lambda x: (x[0].istitle() or x[0].isupper(), x[1]))[0]
            display_name = best_raw.strip()
            cluster_id = f"ent_org_{hashlib.sha256(norm_key.encode('utf-8')).hexdigest()[:12]}"
            
            c_info = {
                "canonical_id": cluster_id,
                "canonical_name": display_name,
                "category": "organization",
                "members": [x[0] for x in items],
                "total_count": sum(x[1] for x in items),
            }
            self._clusters["organization"].append(c_info)
            for raw, _ in items:
                self._raw_to_canonical_name[("organization", raw)] = display_name
                self._raw_to_canonical_id[("organization", raw)] = cluster_id

    def _cluster_generic(self, counter: Counter, cat: str) -> None:
        """Clusters generic entities (locations, dates, money, etc.) by normalized value."""
        cleaned_groups: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        for raw, count in counter.items():
            norm = re.sub(r"\s+", " ", raw.strip()).lower()
            if not norm:
                continue
            cleaned_groups[norm].append((raw, count))

        for norm_key, items in cleaned_groups.items():
            best_raw = max(items, key=lambda x: x[1])[0]
            display_name = best_raw.strip()
            prefix = cat[:4]
            cluster_id = f"ent_{prefix}_{hashlib.sha256(norm_key.encode('utf-8')).hexdigest()[:12]}"
            
            c_info = {
                "canonical_id": cluster_id,
                "canonical_name": display_name,
                "category": cat,
                "members": [x[0] for x in items],
                "total_count": sum(x[1] for x in items),
            }
            self._clusters[cat].append(c_info)
            for raw, _ in items:
                self._raw_to_canonical_name[(cat, raw)] = display_name
                self._raw_to_canonical_id[(cat, raw)] = cluster_id

    def resolve(self, raw_name: str, entity_type: str) -> Tuple[str, str, str]:
        """
        Resolves a raw entity mention to (canonical_id, canonical_name, normalized_type).
        Guarantees strict type-scoping.
        """
        norm_type = entity_type.lower().rstrip("s")
        if norm_type in ("people", "person", "attorney", "custodian"):
            cat = "person"
        elif norm_type in ("organizations", "organization", "org"):
            cat = "organization"
        else:
            cat = norm_type

        # Check existing map
        key = (cat, raw_name)
        if key in self._raw_to_canonical_id:
            return self._raw_to_canonical_id[key], self._raw_to_canonical_name[key], cat

        # Fallback for dynamic/unseen mentions
        cleaned = clean_person_string(raw_name) if cat == "person" else raw_name.strip()
        if (cat, cleaned) in self._raw_to_canonical_id:
            return self._raw_to_canonical_id[(cat, cleaned)], self._raw_to_canonical_name[(cat, cleaned)], cat

        norm_val = cleaned.lower()
        prefix = "org" if cat == "organization" else cat
        cid = f"ent_{prefix}_{hashlib.sha256(norm_val.encode('utf-8')).hexdigest()[:12]}"
        display = cleaned if cleaned else raw_name
        return cid, display, cat

