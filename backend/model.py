# backend/model.py
import time
import threading
from typing import List, Optional

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig


MODEL_LOADED: bool = False
LOAD_PROGRESS: int = 0
LOAD_MESSAGE: str = "Modelo no cargado."

_lock = threading.Lock()
_thread = None

_tokenizer: Optional[AutoTokenizer] = None
_model: Optional[AutoModelForCausalLM] = None

MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.3"

PROMPT_TEMPLATE = """<s>[INST] <<SYS>>
Eres un corrector ortográfico extremadamente estricto. Tu ÚNICA tarea es corregir faltas de ortografía en el texto.

Presta especial atención a estas categorías, pero corrige OTROS errores ortográficos si los hay:
   - Confusión entre B y V.
   - Confusión entre G y J.
   - Confusión entre Y y LL.
   - Uso incorrecto u omisión de la letra H.
   - Uso incorrecto u omisión de tildes (acentuación).
   - OTROS errores ortográficos generales (ej. M antes de P, S en lugar de X, etc.).

REGLAS ABSOLUTAMENTE OBLIGATORIAS:
1. NO cambies el sentido de la frase bajo ninguna circunstancia.
2. NO sustituyas palabras por sinónimos. Si la palabra existe pero está mal escrita, corrígela. Si está bien escrita, déjala exactamente igual.
3. NO modifiques la estructura sintáctica, ni la puntuación, ni el estilo, ni el tiempo verbal.
4. Tu salida debe ser EXACTAMENTE el mismo texto original, palabra por palabra, alterando únicamente las letras necesarias para corregir la ortografía.
5. No agregues explicaciones, comentarios ni ningún otro contenido adicional. Solo devuelve el texto corregido.
<</SYS>>

Ejemplos:
1. He perdido las yaves de casa.
He perdido las llaves de casa.
2. Bamos a la plalla.
Vamos a la playa.
3. oy tu tienes examen.
Hoy tú tienes examen.
4. El profesor tiene que correjir los examenes.
El profesor tiene que corregir los exámenes.

Texto a corregir:
[TEXTO]
[/INST]
"""

PROMPT_FEEDBACK = """<s>[INST] <<SYS>>
Eres un tutor de español que ayuda a mejorar la redacción académica.

Tu tarea es explicar de forma sencilla los cambios realizados entre un texto original y su versión corregida.

Explica únicamente los cambios que realmente aparecen en el texto corregido. Categoriza los errores encontrados en:
- Errores ortográficos: B vs V, G vs J, Y vs LL, uso de H, o uso de tildes.

Para cada error corregido:
1. Indica la palabra original y su corrección.
2. Menciona a qué categoría pertenece.
3. Da una brevísima regla ortográfica o gramatical que justifique el cambio.

No inventes errores que no estén en el texto. Redacta el feedback de forma estructurada, clara, directa y pedagógica.
<</SYS>>

Texto original: [ORIGINAL]
Texto corregido: [CORREGIDO]

Explicación:
[/INST]"""


@torch.inference_mode()
def _generate_raw_prompt(prompt: str, max_new_tokens: int = 512) -> str:
    """Genera texto sin envolver en PROMPT_TEMPLATE (necesario para feedback)."""
    global _tokenizer, _model
    if not MODEL_LOADED or _tokenizer is None or _model is None:
        return ""

    inputs = _tokenizer(
        prompt,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=4096,
    )

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


def generate_feedback(original: str, corrected: str) -> str:
    if not MODEL_LOADED:
        return ""

    prompt = (
        PROMPT_FEEDBACK
        .replace("[ORIGINAL]", original.strip())
        .replace("[CORREGIDO]", corrected.strip())
    )

    return _generate_raw_prompt(prompt, max_new_tokens=300)


def _set(progress: int, message: str):
    global LOAD_PROGRESS, LOAD_MESSAGE
    with _lock:
        LOAD_PROGRESS = max(0, min(100, int(progress)))
        LOAD_MESSAGE = message


def _load_impl():
    global MODEL_LOADED, _tokenizer, _model
    MODEL_LOADED = False

    try:
        _set(5, "Inicializando carga…")
        try:
            compute_dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float16
        except Exception:
            compute_dtype = torch.float16

        _set(20, "Preparando configuración de cuantización NF4…")
        nf4_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=compute_dtype,
        )

        _set(40, "Cargando tokenizer…")
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, use_fast=True)
        if _tokenizer.pad_token is None:
            _tokenizer.pad_token = _tokenizer.eos_token

        _set(75, "Cargando modelo (esto puede tardar)…")
        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
            quantization_config=nf4_config,
            device_map="auto",
        )

        _model.eval()

        _set(95, "Finalizando…")
        time.sleep(0.5)
        MODEL_LOADED = True
        _set(100, "✅ Modelo cargado y listo")
    except Exception as e:
        _set(0, f"❌ Error cargando modelo: {e}")
        MODEL_LOADED = False


def ensure_model_loaded(async_load: bool = True):
    global _thread, MODEL_LOADED
    if MODEL_LOADED and _model is not None and _tokenizer is not None:
        return
    if _thread and _thread.is_alive():
        return
    if async_load:
        _thread = threading.Thread(target=_load_impl, daemon=True)
        _thread.start()
    else:
        _load_impl()


def _format_prompt(document_text: str) -> str:
    return PROMPT_TEMPLATE.replace("[TEXTO]", document_text.strip())


@torch.inference_mode()
def _generate_once(text: str, max_new_tokens: int = 512) -> str:
    global _tokenizer, _model
    if not MODEL_LOADED or _tokenizer is None or _model is None:
        raise RuntimeError("El modelo aún no está cargado.")

    prompt = _format_prompt(text)
    inputs = _tokenizer(
        prompt,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=4096,
    )

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
    text_out = _tokenizer.decode(generated, skip_special_tokens=True)
    return text_out.strip()

def correct_text(sentences: List[str], batch_size: int = 4, max_new_tokens: int = 512) -> List[str]:
    document = " ".join(s.strip() for s in sentences if isinstance(s, str) and s.strip())
    if not document:
        return [""]
    corrected = _generate_once(document, max_new_tokens=max_new_tokens)
    return [corrected]

def correct_full_text(text: str) -> str:
    if not text:
        return ""

    return _generate_once(text)
