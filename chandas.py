import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# ------------------------ Toggle: force confidence = 1.0 everywhere ------------------------ #
FORCE_CONFIDENCE_ALWAYS_ONE = False  # set True to always show 1.0

# ------------------------ Unicode sets (Devanagari) ------------------------ #

DEV_INDEP_VOWELS = set("अआइईउऊऋॠऌॡएऐओऔ")
DEV_VOWEL_SIGNS = set("ािीुूृॄॢॣेैोौ")
DEV_CONSONANTS = set("कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहक़ख़ग़ज़ड़ढ़फ़य़ऱऴ")
DEV_ANUSVARA = "ं"
DEV_CHANDRABINDU = "ँ"
DEV_VISARGA = "ः"
DEV_VIRAMA = "्"
DEV_DANDA = "।"
DEV_DDANDA = "॥"
DEV_AVAGRAHA = "ऽ"
OM = "ॐ"

DEV_LONG_VOWELS = set("आईऊॠॡएऐओऔ")
DEV_SHORT_VOWELS = set("अइउऋऌ")

# ------------------------ Latin (IAST-oriented) ------------------------ #

LATIN_VOWEL_CHARS = {
    "a", "ā", "i", "ī", "u", "ū", "ṛ", "ṝ", "ḷ", "ḹ", "e", "o"
}
LATIN_DIPHTHONGS = {"ai", "au"}  # long by nature
LATIN_LONG = {"ā", "ī", "ū", "ṝ", "ḹ", "e", "o"}  # e/o long by nature in Sanskrit
LATIN_SHORT = {"a", "i", "u", "ṛ", "ḷ"}

# Consonant digraphs to treat as one unit for onset counting
DIGRAPHS = {"kh", "gh", "ch", "jh", "ṭh", "ḍh", "th", "dh", "ph", "bh"}
# Consonant letters (IAST)
LATIN_CONSONANTS = set(list("kgṅcjñṭḍṇtdnpbmyrlvśṣsh") + ["h", "ṛ", "ḷ", "f", "q", "z"])
# Anusvara/visarga marks in Latin
LATIN_ANUSVARA = {"ṁ", "ṃ"}  # dot above and dot below variants
LATIN_VISARGA = {"ḥ"}
LATIN_CHANDRABINDU = {"m̐", "n̐"}  # common combining alternatives

# ------------------------ Chandas patterns ------------------------ #
# Classic seven (Saptachandas) with target pada counts
CHANDAS_SAPT = [
    {"name": "Gayatri",   "padas": 3, "syllables_per_pada": 8},
    {"name": "Ushnih",    "padas": 4, "syllables_per_pada": 7},
    {"name": "Anushtubh", "padas": 4, "syllables_per_pada": 8},
    {"name": "Brihati",   "padas": 4, "syllables_per_pada": 9},
    {"name": "Pankti",    "padas": 4, "syllables_per_pada": 10},
    {"name": "Trishtubh", "padas": 4, "syllables_per_pada": 11},
    {"name": "Jagati",    "padas": 4, "syllables_per_pada": 12},
]

# ------------------------ Utilities ------------------------ #

def detect_script(text: str, prefer: str = "auto") -> str:
    if prefer in ("devanagari", "latin"):
        return prefer
    for ch in text:
        if "\u0900" <= ch <= "\u097F":
            return "devanagari"
    return "latin"

def normalize_text(text: str) -> str:
    # Normalize OM to a long-vowel + anusvara to reflect heaviness
    text = text.replace(OM, "ओं")
    # Standardize dandas
    text = text.replace(DEV_DDANDA, DEV_DANDA)
    # Keep: all word chars, full Devanagari block, combining marks, whitespace,
    # danda/double-danda, and the '|' pada separator.
    pattern = r"[^\w\u0900-\u097F\u0300-\u036F\s|{}{}]+".format(DEV_DANDA, DEV_DDANDA)
    text = re.sub(pattern, " ", text, flags=re.UNICODE)
    # Replace underscores left by \w, then collapse spaces
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def split_segments(text: str) -> List[str]:
    # Split on line breaks or danda/vertical bars
    parts = re.split(r"[|{}{}\n\r]+".format(DEV_DANDA, DEV_DDANDA), text)
    parts = [p.strip() for p in parts if p.strip()]
    return parts

@dataclass
class Syllable:
    onset_len: int
    nucleus_char: str       # vowel nucleus (dev: vowel/matra; latin: vowel/diphthong)
    intrinsic_long: bool    # vowel long by nature
    has_mark: bool          # anusvara/chandrabindu/visarga
    heavy: bool = False     # final computed heaviness (guru)
    raw: str = ""           # raw surface chunk (for debugging/preview)

# ------------------------ Devanagari parsing ------------------------ #

def parse_dev_syllables(text: str) -> List[Syllable]:
    sylls: List[Syllable] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]

        # Skip spaces, punctuation except prosodic marks
        if ch in {" ", DEV_AVAGRAHA}:
            i += 1
            continue

        # Independent vowel syllable
        if ch in DEV_INDEP_VOWELS:
            nucleus = ch
            intrinsic_long = ch in DEV_LONG_VOWELS
            marks = ""
            j = i + 1
            while j < n and text[j] in {DEV_ANUSVARA, DEV_CHANDRABINDU, DEV_VISARGA}:
                marks += text[j]
                j += 1
            raw = text[i:j]
            sylls.append(Syllable(
                onset_len=0,
                nucleus_char=nucleus,
                intrinsic_long=intrinsic_long,
                has_mark=len(marks) > 0,
                raw=raw
            ))
            i = j
            continue

        # Consonant onset cluster
        if ch in DEV_CONSONANTS:
            onset_len = 1
            j = i
            raw = ch
            # Consume C + virama + C ... (onset cluster)
            while (j + 2) < n and text[j + 1] == DEV_VIRAMA and text[j + 2] in DEV_CONSONANTS:
                j += 2
                onset_len += 1
                raw += text[j - 1] + text[j]
            j += 1  # move past last onset consonant

            nucleus = None
            intrinsic_long = False

            # vowel sign if present
            if j < n and text[j] in DEV_VOWEL_SIGNS:
                nucleus = text[j]
                intrinsic_long = nucleus in set("ाीूॄॣेैोौ")  # long matras
                raw += nucleus
                j += 1
            else:
                # inherent 'a' (short)
                nucleus = "अ"
                intrinsic_long = False

            # marks
            marks = ""
            while j < n and text[j] in {DEV_ANUSVARA, DEV_CHANDRABINDU, DEV_VISARGA}:
                marks += text[j]
                raw += text[j]
                j += 1

            # Special case: halant at end (coda) -> make previous syllable heavy, consume codas
            if j < n and text[j] == DEV_VIRAMA:
                if sylls:
                    sylls[-1].heavy = True
                while j < n and text[j] == DEV_VIRAMA:
                    raw += text[j]
                    j += 1
                    if j < n and text[j] in DEV_CONSONANTS:
                        raw += text[j]
                        j += 1
                i = j
                continue

            sylls.append(Syllable(
                onset_len=onset_len,
                nucleus_char=nucleus,
                intrinsic_long=intrinsic_long,
                has_mark=len(marks) > 0,
                raw=raw
            ))
            i = j
            continue

        # Prosodic marks alone: attach to previous syllable if possible
        if ch in {DEV_ANUSVARA, DEV_CHANDRABINDU, DEV_VISARGA}:
            if sylls:
                sylls[-1].has_mark = True
                sylls[-1].raw += ch
            i += 1
            continue

        # Danda or other: skip
        i += 1

    return sylls

# ------------------------ Latin parsing ------------------------ #

def is_vowel_start_latin(s: str, i: int) -> int:
    # Returns length (1 or 2) of vowel nucleus if found, else 0
    if i >= len(s):
        return 0
    # diphthongs 'ai','au'
    if i + 1 < len(s) and s[i:i+2].lower() in LATIN_DIPHTHONGS:
        return 2
    ch = s[i]
    if ch.lower() in LATIN_VOWEL_CHARS:
        return 1
    return 0

def consume_consonant_unit(s: str, i: int) -> int:
    # Consume one consonant unit (handles digraphs like kh, gh, etc.)
    if i >= len(s):
        return i
    if i + 1 < len(s) and s[i:i+2].lower() in DIGRAPHS:
        return i + 2
    return i + 1

def parse_latin_syllables(text: str) -> List[Syllable]:
    s = text
    sylls: List[Syllable] = []
    i, n = 0, len(s)

    while i < n:
        ch = s[i]

        # Skip spaces/punct except marks
        if ch.isspace() or ch in "|/\\,.;:!?'\"“”‘’()[]{}-":
            i += 1
            continue

        # Build onset cluster
        onset_len = 0
        j = i
        while j < n and is_vowel_start_latin(s, j) == 0:
            if s[j] in LATIN_ANUSVARA or s[j] in LATIN_VISARGA:
                break
            if s[j].isalpha() or s[j] in "ṅñṇḍṭśṣḥṁṃḷṛ":
                j2 = consume_consonant_unit(s, j)
                if is_vowel_start_latin(s, j) == 0:
                    onset_len += 1
                    j = j2
                    continue
            break

        # Now at vowel
        vlen = is_vowel_start_latin(s, j)
        if vlen == 0:
            i = j + 1 if j == i else j
            continue

        nucleus = s[j:j+vlen]
        nucleus_low = nucleus.lower()
        intrinsic_long = (nucleus_low in LATIN_LONG) or (nucleus_low in LATIN_DIPHTHONGS)

        k = j + vlen
        marks = False
        # Optional prosodic marks
        if k < n:
            nxt2 = s[k:k+2]
            if nxt2 in LATIN_CHANDRABINDU:
                marks = True
                k += 2

        if k < n and s[k] in LATIN_ANUSVARA:
            marks = True
            k += 1
        if k < n and s[k] in LATIN_VISARGA:
            marks = True
            k += 1

        raw = s[i:k]
        sylls.append(Syllable(
            onset_len=onset_len,
            nucleus_char=nucleus,
            intrinsic_long=intrinsic_long,
            has_mark=marks,
            raw=raw
        ))
        i = k

    return sylls

# ------------------------ Prosodic logic ------------------------ #

def finalize_heaviness(padas_sylls: List[List[Syllable]]) -> None:
    # Apply Laghu/Guru rules:
    # - Long vowel nuclei are guru
    # - Anusvara/Visarga/Chandrabindu makes guru
    # - Short vowel becomes guru if:
    #    a) it's the end of a pada, or
    #    b) next syllable onset cluster length >= 2 (conjunct)
    for p in padas_sylls:
        for idx, syl in enumerate(p):
            heavy = syl.intrinsic_long or syl.has_mark
            if not heavy:
                if idx == len(p) - 1:
                    heavy = True  # pada end
                else:
                    nxt = p[idx + 1]
                    if nxt.onset_len >= 2:
                        heavy = True
            syl.heavy = heavy

def syllable_pattern(pada: List[Syllable]) -> str:
    return "".join("G" if s.heavy else "L" for s in pada)

# ------------------------ Confidence model ------------------------ #

def confidence_from_deviations(target_len: int, deviations: List[int]) -> float:
    """
    deviations: per-pada abs(count - target)
    Returns a value in (0, 1], close to 1 for exact or near-exact patterns.
    """
    if not deviations:
        return 0.5
    n = len(deviations)
    exact_ratio = sum(d == 0 for d in deviations) / n
    within1_ratio = sum(d <= 1 for d in deviations) / n
    avg_dev = sum(deviations) / n
    base = 0.6 * exact_ratio + 0.3 * within1_ratio + 0.1 * max(0.0, 1.0 - (avg_dev / max(1, target_len)))
    return round(min(1.0, max(0.1, base)), 2)

# ------------------------ Meter identification ------------------------ #

def best_meter_match(padas_syll_counts: List[int]) -> Dict[str, Any]:
    candidates = []
    total_padas = len(padas_syll_counts)

    for cand in CHANDAS_SAPT:
        target_padas = cand["padas"]
        target_len = cand["syllables_per_pada"]

        # score based on differences and pada mismatch
        pad_penalty = abs(total_padas - target_padas) * 4
        diffs = []
        k = min(total_padas, target_padas)
        for i in range(k):
            diffs.append(abs(padas_syll_counts[i] - target_len))
        if total_padas < target_padas:
            diffs += [target_len] * (target_padas - total_padas)  # missing padas worst-case
        score = pad_penalty + sum(diffs)

        candidates.append({
            "name": cand["name"],
            "target_padas": target_padas,
            "target_len": target_len,
            "score": score,
            "deviations": diffs or [target_len] * target_padas
        })

    candidates.sort(key=lambda x: x["score"])
    best = candidates[0]
    conf = confidence_from_deviations(best["target_len"], best["deviations"])
    return {
        "name": best["name"],
        "target_padas": best["target_padas"],
        "target_len": best["target_len"],
        "confidence": 1.0 if FORCE_CONFIDENCE_ALWAYS_ONE else conf,
        "match_type": "closest",
        "deviations": best["deviations"],
    }

def identify_saptachandas(padas_syll_counts: List[int], tolerance: int = 0) -> Optional[Dict[str, Any]]:
    """
    Returns a dict describing the identified meter if:
      - number of padas matches exactly, and
      - each pada's syllable count is within 'tolerance' of the target length.
    Otherwise returns None.
    """
    total_padas = len(padas_syll_counts)
    matches = []
    for cand in CHANDAS_SAPT:
        if total_padas != cand["padas"]:
            continue
        target = cand["syllables_per_pada"]
        deviations = [abs(c - target) for c in padas_syll_counts]
        if not deviations:
            continue
        max_dev = max(deviations)
        if max_dev <= tolerance:
            matches.append((max_dev, sum(deviations), cand, deviations))

    if not matches:
        return None

    matches.sort(key=lambda x: (x[0], x[1]))
    max_dev, total_dev, cand, deviations = matches[0]
    match_type = "exact" if max_dev == 0 else f"tolerant(±{tolerance})"
    conf = 1.0 if max_dev == 0 else confidence_from_deviations(cand["syllables_per_pada"], deviations)

    return {
        "name": cand["name"],
        "target_padas": cand["padas"],
        "target_len": cand["syllables_per_pada"],
        "deviations": deviations,
        "match_type": match_type,
        "confidence": 1.0 if FORCE_CONFIDENCE_ALWAYS_ONE else conf,
    }

def guess_split_into_padas(segments_sylls: List[List[Syllable]]) -> List[List[Syllable]]:
    # If already 3 or 4 segments, treat each as a pada
    if len(segments_sylls) in (3, 4):
        return segments_sylls
    # If 2 segments, try to split each into two padas at half the syllable count
    if len(segments_sylls) == 2:
        out = []
        for seg in segments_sylls:
            n = len(seg)
            half = n // 2
            out.append(seg[:half])
            out.append(seg[half:])
        return out
    # If single segment, try 4 equal-ish splits
    if len(segments_sylls) == 1:
        seg = segments_sylls[0]
        n = len(seg)
        if n == 0:
            return [seg]
        q = max(1, n // 4)
        return [seg[0:q], seg[q:2*q], seg[2*q:3*q], seg[3*q:]]
    # Fallback: return as-is
    return segments_sylls

def analyze_text(text: str, prefer_script: str = "auto") -> Dict[str, Any]:
    raw = text or ""
    norm = normalize_text(raw)
    script = detect_script(norm, prefer_script)

    # Split into textual segments (lines/padas)
    segments = split_segments(norm)
    # Parse syllables per segment
    seg_sylls: List[List[Syllable]] = []
    for seg in segments:
        if script == "devanagari":
            seg_sylls.append(parse_dev_syllables(seg))
        else:
            seg_sylls.append(parse_latin_syllables(seg))

    # Guess padas if 2-line input etc.
    padas_sylls = guess_split_into_padas(seg_sylls)
    # Finalize heaviness (Laghu/Guru)
    finalize_heaviness(padas_sylls)

    # Build patterns and counts
    padas_info = []
    padas_counts = []
    for p in padas_sylls:
        patt = syllable_pattern(p)
        padas_counts.append(len(p))
        padas_info.append({
            "count": len(p),
            "pattern": patt
        })

    # Identify meter (try exact -> tolerant -> closest)
    exact = identify_saptachandas(padas_counts, tolerance=0)
    tolerant = None if exact else identify_saptachandas(padas_counts, tolerance=1)
    best = exact or tolerant or best_meter_match(padas_counts)

    # Optional: Force 1.0 here as a last resort (if the global toggle is on)
    if FORCE_CONFIDENCE_ALWAYS_ONE and isinstance(best, dict):
        best["confidence"] = 1.0

    return {
        "script": script,
        "input_segments": len(segments),
        "padas": padas_info,
        "pada_counts": padas_counts,
        "guess": best,
        "note": (
            "Exact Sapta-chandas match" if (exact and best is exact) else
            ("Within ±1 tolerance" if (tolerant and best is tolerant) else
             "Closest based on counts; may be approximate")
        )
    }