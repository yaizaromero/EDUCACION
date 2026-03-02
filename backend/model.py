# backend/model.py
import time
import threading
from typing import List, Optional
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import json
from backend.orthography_report import build_orthography_report

MODEL_LOADED: bool = False
LOAD_PROGRESS: int = 0
LOAD_MESSAGE: str = "Modelo no cargado."

_lock = threading.Lock()
_thread = None
_tokenizer: Optional[AutoTokenizer] = None
_model: Optional[AutoModelForCausalLM] = None

MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.3"

# --- PROMPTS UNIFICADOS Y MEJORADOS ---

PROMPT_ORTOGRAFIA = """<s>[INST] <<SYS>>
Eres un corrector ortográfico automático de español.

Tu única tarea es corregir errores estrictamente ortográficos.
No eres revisor de estilo.
No eres corrector gramatical.
No eres redactor.

REGLAS OBLIGATORIAS:
- Realiza la MÍNIMA cantidad de cambios posible.
- Corrige únicamente errores ortográficos reales.
- Mantén exactamente las mismas palabras y el mismo orden.
- No reformules frases.
- No cambies tiempos verbales ni persona gramatical.
- No añadas ni elimines palabras.
- No cambies puntuación ni mayúsculas salvo que formen parte del error.
- Si una palabra está correctamente escrita, NO la modifiques.
- Si el texto no tiene errores ortográficos, devuélvelo EXACTAMENTE igual.

PUEDES CORREGIR SOLO:
- B/V
- G/J
- Y/LL
- C/Z/S
- H (ausente o añadida incorrectamente)
- Tildes obligatorias según las reglas del español
- Reglas generales como "m" antes de "p/b" o duplicaciones evidentes de letras

REGLA IMPORTANTE SOBRE TILDES:
- Solo añade una tilde si es obligatoria.
- No inventes tildes.
- Si dudas, no cambies la palabra.

FORMATO DE RESPUESTA:
Devuelve únicamente el texto corregido.
No añadas explicaciones ni comentarios.
No uses listas.
No uses comillas.

Ejemplos:
1. mi varco es azul
mi barco es azul

2. El niño bibe en una casa.
El niño vive en una casa.

3. mi barco es azul
mi barco es azul

4. azul
azul

Texto a corregir:
[TEXTO]
[/INST]"""

PROMPT_TU_IMPERSONAL = """<s>[INST] <<SYS>>
Eres un asistente experto en corrección de textos en español.

Tu única tarea es transformar los verbos en segunda persona del singular con valor impersonal a la forma impersonal con “se” + verbo en tercera persona.

REGLAS OBLIGATORIAS:
- Mantén el tiempo verbal original.
- Mantén la concordancia: si el elemento al que se refiere el verbo es plural, el verbo debe ir en plural (ej.: "si vendes manzanas" → "se venden manzanas").
- No cambies palabras, puntuación ni estructura sintáctica salvo lo estrictamente necesario para aplicar la transformación.
- No agregues explicaciones, comentarios ni contenido adicional.
- Mantén un registro formal, académico o científico.

<</SYS>>

Ejemplos:
1. Tú explicas cómo funciona el sistema.
Se explica cómo funciona el sistema.
2. Cuando comes mucho, te duele el estómago.
Cuando se come mucho, duele el estómago.
3. En la investigación científica, si tú interpretas incorrectamente los resultados, puedes generar grandes incongruencias.
En la investigación científica, si se interpretan incorrectamente los resultados, se pueden generar grandes incongruencias.
4. Cuando juegas un partido complicado, y aunque tengas experiencia, tú cometes errores que afectan al resultado final.
Cuando se juega un partido complicado, y aunque se tenga experiencia, se cometen errores que afectan al resultado final.
5. ¿Puedes fumar?
¿Se puede fumar?
6. Si vendes manzanas, obtienes beneficios.
Si se venden manzanas, se obtienen beneficios.

Texto a corregir:
[TEXTO]
[/INST]
"""
PROMPT_FEEDBACK_ORTO = """<s>[INST] <<SYS>>
Eres un tutor de español. Debes redactar un feedback breve y claro BASÁNDOTE SOLO en un reporte JSON ya calculado.

REGLAS ESTRICTAS:
- NO inventes cambios, palabras ni reglas.
- NO menciones nada que no esté en el JSON.
- NO uses listas ni numeraciones.
- Redacta 1 o 2 párrafos breves.
- Menciona las categorías con más cambios (según "top_categories" y "counts").
- Incluye ejemplos reales usando SOLO elementos de "changes_by_cat" (máximo 4 ejemplos en total).
- Da 2 recomendaciones prácticas enfocadas en las categorías más frecuentes.
- Si "non_orthographic_changes" tiene elementos, menciona que se detectaron cambios no ortográficos y que el análisis se centra en ortografía.

<</SYS>>

REPORTE_JSON:
[REPORT]

Feedback:
[/INST]"""

PROMPT_FEEDBACK_TU = """<s>[INST] <<SYS>>
Eres un tutor de español que ayuda a mejorar la redacción académica.

Tu tarea es explicar de forma sencilla los cambios realizados entre un texto original y su versión corregida.

Explica únicamente los cambios que realmente aparecen en el texto corregido.
No menciones errores que no se hayan corregido.
No inventes errores.
No uses listas ni enumeraciones.
Redacta el feedback en uno o dos párrafos breves y claros.

Si se ha cambiado el uso de "tú", explica que en textos escritos y académicos no se habla directamente al lector.
El uso del "tú" impersonal es más propio del lenguaje oral o divulgativo y puede hacer que el texto
suene subjetivo o demasiado cercano.
La forma impersonal con "se" permite expresar las ideas de manera más general, objetiva y adecuada
para este tipo de textos.

Si se ha cambiado la forma del verbo, explica que se ha hecho para que la frase sea correcta y natural en español.
Si no hay otros errores importantes, indícalo claramente.

Mantén un tono claro, directo, profesional y pedagógico.
<</SYS>>

Texto original: [ORIGINAL]
Texto corregido: [CORREGIDO]

Explicación:
[/INST]"""


# --- GENERACIÓN ---

@torch.inference_mode()
def _generate_once(text: str, mode: str = "ortografia", max_new_tokens: int = 512) -> str:
    global _tokenizer, _model
    if not MODEL_LOADED or _tokenizer is None or _model is None:
        raise RuntimeError("El modelo no está cargado.")
    
    # Selección de template según el modo
    template = PROMPT_ORTOGRAFIA if mode == "ortografia" else PROMPT_TU_IMPERSONAL
    prompt = template.replace("[TEXTO]", text.strip())
    
    inputs = _tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=4096)
    if hasattr(_model, "device"):
        inputs = {k: v.to(_model.device) for k, v in inputs.items()}
    
    output_ids = _model.generate(
        **inputs, 
        max_new_tokens=max_new_tokens, 
        do_sample=False, 
        temperature=0.0,
        eos_token_id=_tokenizer.eos_token_id,
        pad_token_id=_tokenizer.pad_token_id
    )
    
    generated = output_ids[0][inputs["input_ids"].shape[-1]:]
    return _tokenizer.decode(generated, skip_special_tokens=True).strip()

@torch.inference_mode()
def _generate_from_prompt(prompt: str, max_new_tokens: int = 512) -> str:
    global _tokenizer, _model
    if not MODEL_LOADED or _tokenizer is None or _model is None:
        raise RuntimeError("El modelo no está cargado.")

    inputs = _tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=4096)
    if hasattr(_model, "device"):
        inputs = {k: v.to(_model.device) for k, v in inputs.items()}

    output_ids = _model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        temperature=0.0,
        eos_token_id=_tokenizer.eos_token_id,
        pad_token_id=_tokenizer.pad_token_id,
    )
    generated = output_ids[0][inputs["input_ids"].shape[-1]:]
    return _tokenizer.decode(generated, skip_special_tokens=True).strip()

def correct_full_text(text: str, mode: str = "ortografia") -> str:
    if not text: return ""
    return _generate_once(text, mode=mode)

# --- FEEDBACK ---
def generate_feedback(original: str, corrected: str, mode: str = "ortografia") -> str:
    if not original or not corrected:
        return ""
    if original.strip() == corrected.strip():
        return "No se han detectado cambios para explicar."

    if mode == "ortografia":
        return feedback_orthography(original, corrected, use_llm=True)

    prompt = PROMPT_FEEDBACK_TU.replace("[ORIGINAL]", original).replace("[CORREGIDO]", corrected)
    return _generate_from_prompt(prompt, max_new_tokens=256).strip()


def feedback_orthography(
    original: str,
    corrected: str,
    errores_extraidos: dict | None = None,
    susceptible_counts: dict | None = None,
    use_llm: bool = True
) -> str:
    report = build_orthography_report(original, corrected)

    total_changes = report.get("total_changes", 0)
    counts = report.get("counts", {})
    otros_count = counts.get("OTRO", counts.get("OTROS", 0))

    # --- modo defensivo SOLO si OTRO es dominante ---
    if total_changes > 0 and (otros_count / total_changes) > 0.4:
        examples = report.get("changes_by_cat", {})
        shown = []
        for cat in ["TILDES", "B_V", "H", "G_J", "Y_LL", "C_Z_S", "OTRO", "OTROS"]:
            for item in examples.get(cat, [])[:2]:
                shown.append(item)  # item ya es "o → c"
                if len(shown) >= 5:
                    break
            if len(shown) >= 5:
                break

        msg = (
            "He detectado algunos cambios que no parecen estrictamente ortográficos, "
            "así que el análisis se limita a las correcciones claramente ortográficas."
        )
        if shown:
            msg += " Algunos ejemplos: " + "; ".join(shown) + "."
        return msg

    # --- modo determinista (sin LLM) ---
    if not use_llm:
        top = [k for k, n in report.get("top_categories", []) if n > 0]
        if not top:
            return "No se han detectado errores ortográficos relevantes. El texto está bien a nivel de ortografía."
        return (
            f"Los errores principales aparecen en: {', '.join(top)}. "
            "Para mejorar, revisa esas reglas y pasa una última revisión lenta antes de entregar."
        )

    # --- LLM: redacta SOLO usando el JSON ---
    prompt = PROMPT_FEEDBACK_ORTO.replace(
        "[REPORT]",
        json.dumps(report, ensure_ascii=False)
    )
    return _generate_from_prompt(prompt, max_new_tokens=500).strip()
# --- CARGA DEL MODELO ---

def _set(progress: int, message: str):
    global LOAD_PROGRESS, LOAD_MESSAGE
    with _lock:
        LOAD_PROGRESS = max(0, min(100, int(progress)))
        LOAD_MESSAGE = message

def _load_impl():
    global MODEL_LOADED, _tokenizer, _model
    try:
        _set(5, "Iniciando carga del modelo...")
        compute_dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float16
        nf4_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=compute_dtype,
        )
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, use_fast=True)
        if _tokenizer.pad_token is None: _tokenizer.pad_token = _tokenizer.eos_token
        
        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID, quantization_config=nf4_config, device_map="auto", trust_remote_code=True
        )
        _model.eval()
        MODEL_LOADED = True
        _set(100, "✅ Modelo cargado y listo")
    except Exception as e:
        _set(0, f"❌ Error: {e}")

def ensure_model_loaded(async_load: bool = True):
    global _thread
    if MODEL_LOADED: return
    if _thread and _thread.is_alive(): return
    if async_load:
        _thread = threading.Thread(target=_load_impl, daemon=True)
        _thread.start()
    else:
        _load_impl()
        
        
def correct_orthography(text: str) -> str:
    if not text:
        return ""
    return _generate_once(text, mode="ortografia").strip()
    
