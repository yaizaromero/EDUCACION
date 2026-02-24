# backend/metrics.py
import re
import unicodedata
from difflib import SequenceMatcher
from rapidfuzz.distance import Levenshtein as L

# -----------------------------
# Normalización / helpers (Se mantienen igual)
# -----------------------------
def _normalize_for_diff(text: str) -> str:
    if not text: return ""
    t = text
    t = t.replace("…", "...")
    t = t.replace("“", '"').replace("”", '"')
    t = t.replace("‘", "'").replace("’", "'")
    t = t.replace("—", "-").replace("–", "-")
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    return t.strip()

def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

def _tokenize_words(text: str):
    t = _normalize_for_diff(text).lower()
    return re.findall(r"[a-záéíóúüñ]+", t, flags=re.IGNORECASE)

def _count_sentences(text: str) -> int:
    t = _normalize_for_diff(text)
    parts = re.split(r"[.!?]+|\n+", t)
    parts = [p.strip() for p in parts if p.strip()]
    return len(parts)

def word_levenshtein_count(a_text: str, b_text: str) -> int:
    a_tokens = _normalize_for_diff(a_text).split()
    b_tokens = _normalize_for_diff(b_text).split()
    return int(L.distance(a_tokens, b_tokens))

# -----------------------------
# Clasificación de errores (Se mantienen igual)
# -----------------------------
def _has_bv_change(a: str, b: str) -> bool:
    return ("b" in a and "v" in b) or ("v" in a and "b" in b)

def _has_gj_change(a: str, b: str) -> bool:
    return ("g" in a and "j" in b) or ("j" in a and "g" in b)

def _has_h_change(a: str, b: str) -> bool:
    return ("h" in a) != ("h" in b)

def _has_yll_change(a: str, b: str) -> bool:
    return (("ll" in a and "y" in b) or ("y" in a and "ll" in b))

def _has_tilde_change(a: str, b: str) -> bool:
    return _strip_accents(a) == _strip_accents(b) and a != b

def _classify_word_change(a: str, b: str):
    cats = set()
    if _has_bv_change(a, b): cats.add("bv")
    if _has_gj_change(a, b): cats.add("gj")
    if _has_yll_change(a, b): cats.add("yll")
    if _has_h_change(a, b): cats.add("h")
    if _has_tilde_change(a, b): cats.add("tildes")
    return cats

def _aligned_word_pairs(orig_tokens, corr_tokens):
    sm = SequenceMatcher(a=orig_tokens, b=corr_tokens)
    pairs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "replace":
            a_seg, b_seg = orig_tokens[i1:i2], corr_tokens[j1:j2]
            m = min(len(a_seg), len(b_seg))
            for k in range(m):
                pairs.append((a_seg[k], b_seg[k]))
    return pairs

# ------------------------------------------------------------
# API PRINCIPAL ACTUALIZADA
# ------------------------------------------------------------

def compute_metrics(original_text: str, corrected_text: str) -> dict:
    orig = _normalize_for_diff(original_text)
    corr = _normalize_for_diff(corrected_text)

    orig_tokens = _tokenize_words(orig)
    corr_tokens = _tokenize_words(corr)

    pairs = _aligned_word_pairs(orig_tokens, corr_tokens)
    bv = gj = yll = h = tildes = 0

    for a, b in pairs:
        if a == b: continue
        cats = _classify_word_change(a, b)
        if "bv" in cats: bv += 1
        if "gj" in cats: gj += 1
        if "yll" in cats: yll += 1
        if "h" in cats: h += 1
        if "tildes" in cats: tildes += 1

    # Calculamos cambios totales (incluyendo gramaticales como "tú" -> "se")
    # Usamos Levenshtein de palabras para ser más precisos en cambios propuestos
    cambios_propuestos = word_levenshtein_count(original_text, corrected_text)

    return {
        "total_sentences": _count_sentences(original_text),
        "errors_bv": int(bv),
        "errors_gj": int(gj),
        "errors_yll": int(yll),
        "errors_h": int(h),
        "errors_tildes": int(tildes),
        "changes_proposed_model": int(cambios_propuestos),
        "changes_done_user": int(cambios_propuestos),
        "word_levenshtein": cambios_propuestos,
    }

def extract_word_changes(original_text: str, corrected_text: str, max_items: int = 40):
    """
    IMPORTANTE: Si no hay categorías ortográficas, devuelve el cambio como 'gramatical'.
    Esto permite que el feedback explique cambios de "Tú impersonal".
    """
    orig = _normalize_for_diff(original_text)
    corr = _normalize_for_diff(corrected_text)

    orig_tokens = orig.split() # Split simple para mantener puntuación si fuera necesario
    corr_tokens = corr.split()
    
    sm = SequenceMatcher(None, orig_tokens, corr_tokens)
    out = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "delete", "insert"):
            a_seg = " ".join(orig_tokens[i1:i2])
            b_seg = " ".join(corr_tokens[j1:j2])
            
            if not a_seg or not b_seg: continue

            # Limpiamos para clasificar
            a_clean = re.sub(r'[^\w]', '', a_seg.lower())
            b_clean = re.sub(r'[^\w]', '', b_seg.lower())
            
            cats = list(_classify_word_change(a_clean, b_clean))
            
            # Si no hay categorías pero el texto cambió, es un cambio de estilo/gramática
            if not cats and a_seg != b_seg:
                cats = ["estilo"]

            out.append({
                "original": a_seg,
                "corrected": b_seg,
                "categories": cats
            })
            
            if len(out) >= max_items: break
    return out