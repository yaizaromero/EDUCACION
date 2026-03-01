# backend/orthography_report.py
from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

CATEGORIES = ["B/V", "G/J", "Y/LL", "C/Z/S", "H", "TILDES", "DUPLICACION", "OTRO"]

def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

def is_word(token: str) -> bool:
    # palabra = contiene alguna letra
    return any(ch.isalpha() for ch in token)

def tokenize_keep_punct(text: str) -> List[str]:
    # Mantiene puntuación/espacios como tokens para alinear sin “mover” cosas
    # Ej: "hola, tío" -> ["hola", ",", " ", "tío"]
    return re.findall(r"\w+|[^\w]", text, flags=re.UNICODE)

def align_tokens(a: List[str], b: List[str]) -> List[Tuple[str, str]]:
    """
    Devuelve pares (orig, corr) donde solo nos interesan reemplazos de tokens.
    Insert/delete también los devolvemos como ("", token) o (token, "").
    """
    sm = SequenceMatcher(a=a, b=b)
    pairs: List[Tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            left = a[i1:i2]
            right = b[j1:j2]
            # empareja por posición lo que se pueda
            m = max(len(left), len(right))
            for k in range(m):
                pairs.append((left[k] if k < len(left) else "", right[k] if k < len(right) else ""))
        elif tag == "delete":
            for tok in a[i1:i2]:
                pairs.append((tok, ""))
        elif tag == "insert":
            for tok in b[j1:j2]:
                pairs.append(("", tok))
    return pairs

def categorize_change(orig: str, corr: str) -> str:
    """
    Categoriza SOLO cambios “tipo ortografía”.
    Si detectamos cambio de palabra por sinónimo/otra palabra, lo marcamos OTRO.
    """
    o = orig
    c = corr

    if not o or not c:
        # insert/delete -> suele ser NO ortográfico en vuestro contexto
        return "OTRO"

    # Solo miramos palabras (ignoramos espacios/puntuación)
    if not (is_word(o) and is_word(c)):
        return "OTRO"

    o_low = o.lower()
    c_low = c.lower()

    # 1) solo tildes: misma palabra sin acentos
    if strip_accents(o_low) == strip_accents(c_low) and o_low != c_low:
        return "TILDES"

    # 2) cambios de una letra típicos
    # H
    if o_low.replace("h", "") == c_low.replace("h", "") and (("h" in o_low) != ("h" in c_low)):
        return "H"

    # B/V
    if o_low.replace("b", "v") == c_low.replace("b", "v") and o_low != c_low:
        # ejemplo: "ba"->"va", "bisto"->"visto"
        return "B/V"

    # G/J
    if o_low.replace("g", "j") == c_low.replace("g", "j") and o_low != c_low:
        return "G/J"

    # Y/LL (aprox): si al normalizar ll<->y coincide
    if o_low.replace("ll", "y") == c_low.replace("ll", "y") and o_low != c_low:
        return "Y/LL"

    # C/Z/S (aprox)
    norm_o = re.sub(r"[czs]", "s", o_low)
    norm_c = re.sub(r"[czs]", "s", c_low)
    if norm_o == norm_c and o_low != c_low:
        return "C/Z/S"

    # 3) duplicaciones de letras (rr, ll, etc.)
    # Si quitando duplicaciones coinciden
    def dedup(x: str) -> str:
        return re.sub(r"(.)\1+", r"\1", x)
    if dedup(o_low) == dedup(c_low) and o_low != c_low:
        return "DUPLICACION"

    # 4) Si NO son “parecidas” en forma ortográfica, es otro (sinónimos, gramática, etc.)
    # Regla simple: si la distancia por SequenceMatcher es baja => otro
    ratio = SequenceMatcher(a=o_low, b=c_low).ratio()
    if ratio < 0.65:
        return "OTRO"

    # Si es parecido pero no detectamos categoría, lo dejamos en OTRO para no mentir
    return "OTRO"

def build_orthography_report(original: str, corrected: str) -> Dict:
    a = tokenize_keep_punct(original)
    b = tokenize_keep_punct(corrected)

    pairs = align_tokens(a, b)

    changes_by_cat: Dict[str, List[str]] = {k: [] for k in CATEGORIES}
    non_orthographic_changes: List[str] = []

    for o, c in pairs:
        if not (is_word(o) or is_word(c)):
            continue
        if o == c:
            continue
        cat = categorize_change(o, c)
        item = f"{o} → {c}"
        changes_by_cat[cat].append(item)
        if cat == "OTRO":
            non_orthographic_changes.append(item)

    counts = {k: len(v) for k, v in changes_by_cat.items()}
    total_changes = sum(counts.values())

    # “nivel” simple por volumen de errores ortográficos (sin OTRO)
    orto_changes = total_changes - counts["OTRO"]
    if orto_changes <= 2:
        level = "bueno"
    elif orto_changes <= 6:
        level = "medio"
    else:
        level = "bajo"

    # top categorías (sin OTRO)
    top = sorted(
        [(k, counts[k]) for k in CATEGORIES if k != "OTRO"],
        key=lambda x: x[1],
        reverse=True
    )

    return {
        "counts": counts,
        "level": level,
        "total_changes": total_changes,
        "top_categories": top[:3],
        "changes_by_cat": changes_by_cat,
        "non_orthographic_changes": non_orthographic_changes[:20],  # recorta para no explotar tokens
    }