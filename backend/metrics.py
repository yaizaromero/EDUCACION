# backend/metrics.py
import re
import unicodedata
from difflib import SequenceMatcher
from rapidfuzz.distance import Levenshtein as L


# -----------------------------
# Normalización / helpers
# -----------------------------
def _normalize_for_diff(text: str) -> str:
    """
    Normalización mínima:
    - …  → ...
    - — / –  → -
    - “ ”  → "
    - ‘ ’  → '
    Mantiene saltos de línea.
    """
    if not text:
        return ""

    t = text
    t = t.replace("…", "...")
    t = t.replace("“", '"').replace("”", '"')
    t = t.replace("‘", "'").replace("’", "'")
    t = t.replace("—", "-").replace("–", "-")
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    return t.strip()


def _strip_accents(s: str) -> str:
    # Quita tildes/acentos: "había" -> "habia"
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _tokenize_words(text: str):
    """
    Tokeniza palabras. Mantiene letras con acentos y ñ.
    Ej: "llegué," -> "llegué"
    """
    t = _normalize_for_diff(text).lower()
    return re.findall(r"[a-záéíóúüñ]+", t, flags=re.IGNORECASE)


def _count_sentences(text: str) -> int:
    """
    Conteo simple de frases/oraciones.
    Divide por . ! ? y saltos de línea, ignorando vacíos.
    """
    t = _normalize_for_diff(text)
    parts = re.split(r"[.!?]+|\n+", t)
    parts = [p.strip() for p in parts if p.strip()]
    return len(parts)


def word_levenshtein_count(a_text: str, b_text: str) -> int:
    a_tokens = _normalize_for_diff(a_text).split()
    b_tokens = _normalize_for_diff(b_text).split()
    return int(L.distance(a_tokens, b_tokens))


# -----------------------------
# Clasificación de errores
# -----------------------------
def _has_bv_change(a: str, b: str) -> bool:
    return ("b" in a and "v" in b) or ("v" in a and "b" in b)

def _has_gj_change(a: str, b: str) -> bool:
    return ("g" in a and "j" in b) or ("j" in a and "g" in b)

def _has_h_change(a: str, b: str) -> bool:
    # cambio por añadir/quitar h
    return ("h" in a) != ("h" in b)

def _has_yll_change(a: str, b: str) -> bool:
    # caso típico: "ll" <-> "y"
    return (("ll" in a and "y" in b) or ("y" in a and "ll" in b))

def _has_tilde_change(a: str, b: str) -> bool:
    # misma palabra sin tildes, pero distinta con tildes
    # ej: "habia" vs "había"
    return _strip_accents(a) == _strip_accents(b) and a != b


def _classify_word_change(a: str, b: str):
    """
    Devuelve un set de categorías detectadas en el cambio a->b.
    Una sustitución puede contar en varias categorías (ej: bolígrafo: tilde + otra cosa).
    """
    cats = set()
    if _has_bv_change(a, b):
        cats.add("bv")
    if _has_gj_change(a, b):
        cats.add("gj")
    if _has_yll_change(a, b):
        cats.add("yll")
    if _has_h_change(a, b):
        cats.add("h")
    if _has_tilde_change(a, b):
        cats.add("tildes")
    return cats


def _aligned_word_pairs(orig_tokens, corr_tokens):
    """
    Alinea listas de palabras y devuelve pares (orig, corr) para cambios tipo replace.
    No cuenta inserciones/borrados como "errores ortográficos" por defecto.
    """
    sm = SequenceMatcher(a=orig_tokens, b=corr_tokens)
    pairs = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "replace":
            continue

        # Alineación uno-a-uno en el segmento reemplazado
        a_seg = orig_tokens[i1:i2]
        b_seg = corr_tokens[j1:j2]
        m = min(len(a_seg), len(b_seg))
        for k in range(m):
            pairs.append((a_seg[k], b_seg[k]))

        # Si hay desbalance (p.ej. 1 palabra -> 2 palabras), lo ignoramos aquí
        # porque suele ser cambio gramatical/estilístico más que ortográfico.

    return pairs


# -----------------------------
# API principal para tu app
# -----------------------------
def compute_metrics(original_text: str, corrected_text: str) -> dict:
    orig = _normalize_for_diff(original_text)
    corr = _normalize_for_diff(corrected_text)

    orig_tokens = _tokenize_words(orig)
    corr_tokens = _tokenize_words(corr)

    # cambios propuestos: aproximación = nº de palabras que cambian (replace)
    pairs = _aligned_word_pairs(orig_tokens, corr_tokens)

    bv = gj = yll = h = tildes = 0

    for a, b in pairs:
        if a == b:
            continue
        cats = _classify_word_change(a, b)
        bv += 1 if "bv" in cats else 0
        gj += 1 if "gj" in cats else 0
        yll += 1 if "yll" in cats else 0
        h += 1 if "h" in cats else 0
        tildes += 1 if "tildes" in cats else 0

    # si quieres mostrar "cambios propuestos" en la UI:
    cambios_propuestos = len([1 for a, b in pairs if a != b])

    return {
        "total_sentences": _count_sentences(original_text),
        "tu_impersonal_candidates": 0,  # si no lo usas, déjalo a 0
        "errors_bv": int(bv),
        "errors_gj": int(gj),
        "errors_yll": int(yll),
        "errors_h": int(h),
        "errors_tildes": int(tildes),
        "changes_proposed_model": int(cambios_propuestos),
        # lo que hace el usuario es frontend; si tu app lo guarda, rellénalo allí:
        "changes_done_user": int(cambios_propuestos),

        # opcional: tu métrica antigua
        "word_levenshtein": word_levenshtein_count(original_text, corrected_text),
    }