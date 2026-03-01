# # backend/utils.py
import unicodedata

import pdfplumber
import io
import re
import spacy
import difflib
import unicodedata
import backend.model as model  # Importamos el modelo para poder usarlo desde aquí

nlp = spacy.load("es_core_news_lg")

def extract_text_from_pdf(pdf_bytes):
    pdf_file = io.BytesIO(pdf_bytes)
    with pdfplumber.open(pdf_file) as pdf:
        textos = []
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                textos.append(t)
        return "\n".join(textos)

def split_into_sentences(text):
    """Divide el texto en oraciones usando spaCy."""
    doc = nlp(text or "")
    return [s.text.strip() for s in doc.sents]
 
def es_verbo_segunda_persona(verbo):
    """
    Detecta 2ª persona REAL:
    - Verbos finitos con Person=2 (spaCy)
    - Infinitivos o gerundios con clítico -te (prepararte, corregirte, etc.)
    """

    # 1) Verbos FINITOS (reales)
    if "VerbForm=Fin" in verbo.morph:
        if verbo.morph.get("Person") == ["2"]:
            return True

    # 2) Infinitivos/gerundios con clítico -te
    texto = verbo.text.lower()
    if texto.endswith("te"):
        if verbo.morph.get("VerbForm") in (["Inf"], ["Ger"]):
            return True

    return False


def encontrar_verbos_segunda_persona(sent):
    """
    Encuentra verbos reales (VERB/AUX) en 2.ª persona.
    No se basa en terminaciones, solo spaCy + enclíticos.
    """
    verbos_reales = [t for t in sent if t.pos_ in ["VERB", "AUX"]]
    verbos_2p = [v for v in verbos_reales if es_verbo_segunda_persona(v)]
    return verbos_reales, verbos_2p

def posible_tu_impersonal(texto):
    """
    Evalúa exactamente las mismas oraciones que split_into_sentences().
    Marca las frases que contengan verbos en 2ª persona del singular.
    """
    sentences = split_into_sentences(texto or "")
    posibles = []

    for s in sentences:
        doc = nlp(s)
        _, verbos_2p = encontrar_verbos_segunda_persona(doc)

        if verbos_2p:
            posibles.append(s)

    mensaje = (
        "No se detectaron errores de 'tú' impersonal."
        if not posibles else
        f"Se detectaron {len(posibles)} posibles usos del 'tú' impersonal."
    )

    return posibles, mensaje

def quitar_tildes(s: str) -> str:
    """Elimina las tildes de una cadena para poder compararla."""
    return ''.join(c for c in unicodedata.normalize('NFD', s) 
                   if unicodedata.category(c) != 'Mn')
                   
def normalizar_czs(s: str) -> str:
    """
    Normaliza C/Z/S para comparar cambios típicos:
    - s <-> c (ante e/i) <-> z
    Nota: es heurístico, pero sirve para clasificar.
    """
    s = s.replace("z", "s")
    s = s.replace("c", "s")
    return s

def categorizar_errores_ortograficos(orig: str, corr: str) -> list:
    """Compara la palabra original y la corregida para clasificar TODOS los errores presentes."""
    categorias = set()
    orig_lower = orig.lower()
    corr_lower = corr.lower()
    
    # Comparamos las diferencias internas de la palabra usando SequenceMatcher
    matcher = difflib.SequenceMatcher(None, orig_lower, corr_lower)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ('replace', 'insert', 'delete'):
            o_chunk = orig_lower[i1:i2]
            c_chunk = corr_lower[j1:j2]
            
            chunk_cat = set()
            
            # Verificaciones directas del fragmento
            if quitar_tildes(o_chunk) == quitar_tildes(c_chunk) and o_chunk != c_chunk:
                chunk_cat.add("TILDES")
            elif o_chunk.replace("h", "") == c_chunk.replace("h", ""):
                chunk_cat.add("H")
            elif o_chunk.replace("b", "v") == c_chunk.replace("b", "v"):
                chunk_cat.add("B_V")
            elif o_chunk.replace("g", "j") == c_chunk.replace("g", "j"):
                chunk_cat.add("G_J")
            elif o_chunk.replace("ll", "y") == c_chunk.replace("ll", "y"):
                chunk_cat.add("Y_LL")
            elif normalizar_czs(o_chunk) == normalizar_czs(c_chunk) and o_chunk != c_chunk:
                chunk_cat.add("C_Z")
            else:
                # Si es un fragmento compuesto (ej: "bi" -> "ví" tiene B_V y TILDES)
                o_sin = quitar_tildes(o_chunk)
                c_sin = quitar_tildes(c_chunk)
                
                matched = False
                if o_sin != c_sin:
                    if o_sin.replace("b", "v") == c_sin.replace("b", "v"):
                        chunk_cat.add("B_V")
                        matched = True
                    elif o_sin.replace("g", "j") == c_sin.replace("g", "j"):
                        chunk_cat.add("G_J")
                        matched = True
                    elif o_sin.replace("ll", "y") == c_sin.replace("ll", "y"):
                        chunk_cat.add("Y_LL")
                        matched = True
                    elif o_sin.replace("h", "") == c_sin.replace("h", ""):
                        chunk_cat.add("H")
                        matched = True
                    elif normalizar_czs(o_sin) == normalizar_czs(c_sin):
                        chunk_cat.add("C_Z"); matched = True
                        matched = True
                # Evaluamos tildes en fragmentos compuestos
                if o_chunk != c_chunk and o_sin == c_sin:
                    chunk_cat.add("TILDES")
                    matched = True
                elif o_chunk != o_sin or c_chunk != c_sin:
                    # Si alguna tenía tilde antes o la tiene ahora
                    chunk_cat.add("TILDES")
                
                if not matched and not chunk_cat:
                    chunk_cat.add("OTROS")
                    
            categorias.update(chunk_cat)
            
    if not categorias:
        categorias.add("OTROS")
        
    return list(categorias)


def extraer_listas_errores(texto_original: str, texto_corregido: str) -> dict:
    """Extrae las palabras cambiadas y las clasifica en 6 categorías, permitiendo múltiples apariciones."""
    words_orig = re.findall(r'\b\w+\b', texto_original)
    words_corr = re.findall(r'\b\w+\b', texto_corregido)
    
    listas_errores = {
        "B_V": [],
        "G_J": [],
        "Y_LL": [],
        "C_Z": [],
        "H": [],
        "TILDES": [],
        "OTROS": []
    }
    
    matcher = difflib.SequenceMatcher(None, words_orig, words_corr)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace' and (i2 - i1) == (j2 - j1):
            for w_orig, w_corr in zip(words_orig[i1:i2], words_corr[j1:j2]):
                if w_orig != w_corr:
                    # Aquí recibimos una lista de categorías para esta misma palabra
                    categorias_aplicables = categorizar_errores_ortograficos(w_orig, w_corr)
                    
                    # Añadimos el par (error, corrección) en cada una de sus categorías
                    for cat in categorias_aplicables:
                        listas_errores[cat].append((w_orig, w_corr))
                        
    return listas_errores

def corregir_y_extraer_errores(
    texto: str,
    mode: str = "ortografia",
    corrected_text: str | None = None
):
    """
    - Si corrected_text viene dado, NO vuelve a llamar al LLM.
    - Si no viene, corrige con el LLM (según mode).
    - Devuelve (texto_corregido, listas_errores)
    """
    empty = {"B_V": [], "G_J": [], "Y_LL": [], "H": [], "TILDES": [], "C_Z": [], "OTROS": []}

    if not texto or not texto.strip():
        return "", empty

    if corrected_text is not None:
        texto_corregido = corrected_text
    else:
        texto_corregido = model.correct_full_text(texto, mode=mode)

    listas_errores = extraer_listas_errores(texto, texto_corregido)
    return texto_corregido, listas_errores

def contar_palabras_susceptibles(texto_corregido: str) -> dict:
    import re
    
    palabras = re.findall(r'\b[a-záéíóúüñ]+\b', texto_corregido.lower())
    
    counts = {
        "B_V": 0,
        "G_J": 0,
        "Y_LL": 0,
        "H": 0,
        "C_Z": 0,
        "TILDES": 0,
        "OTROS": len(palabras)
    }
    
    for w in palabras:
        if 'b' in w or 'v' in w:
            counts["B_V"] += 1
        
        if 'j' in w or re.search(r'g[ei]', w):
            counts["G_J"] += 1
        
        if 'y' in w or 'll' in w:
            counts["Y_LL"] += 1
        
        if 'h' in w:
            counts["H"] += 1
        
        if 'c' in w or 'z' in w:
            counts["C_Z"] += 1
        
        if any(c in w for c in 'áéíóú'):
            counts["TILDES"] += 1
    
    return counts