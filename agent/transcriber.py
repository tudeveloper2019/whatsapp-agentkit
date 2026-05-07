# agent/transcriber.py — Transcripción de audios de WhatsApp con OpenAI
# Generado por AgentKit para El Cortijo Parque Acuático

import io
import os
import logging
import httpx
from openai import AsyncOpenAI

logger = logging.getLogger("agentkit")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODELO = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")

MENSAJE_FALLO = "Lo siento, tuve un problema escuchando tu audio. ¿Puedes enviarme tu pregunta por texto? 😊"

# Mapa de content-type → extensión aceptada por OpenAI Whisper
_EXT = {
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "mp4",
    "audio/m4a": "m4a",
    "audio/wav": "wav",
    "audio/webm": "webm",
    "audio/amr": "ogg",   # OpenAI no soporta amr, convertir a ogg falla graceful
}


def _extension(content_type: str) -> str:
    base = content_type.split(";")[0].strip().lower()
    return _EXT.get(base, "ogg")


async def transcribir_audio(audio_url: str) -> str | None:
    """
    Descarga el audio desde Twilio (con autenticación) y lo transcribe con OpenAI.

    Args:
        audio_url: URL del audio enviada por Twilio en el webhook

    Returns:
        Texto transcrito, o None si falla
    """
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY no configurada — no se puede transcribir audio")
        return None

    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")

    try:
        # Descargar audio siguiendo redirects (Twilio responde 307 antes de la URL final)
        logger.info(f"Descargando audio: {audio_url}")
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as http:
            r = await http.get(audio_url, auth=(account_sid, auth_token))
            logger.info(f"Descarga completada — status: {r.status_code} | content-type: {r.headers.get('content-type')} | tamaño: {len(r.content)} bytes")
            if r.status_code != 200:
                logger.error(f"Error descargando audio de Twilio: status {r.status_code}")
                return None
            audio_bytes = r.content
            content_type = r.headers.get("content-type", "audio/ogg")

        ext = _extension(content_type)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = f"audio.{ext}"

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        transcript = await client.audio.transcriptions.create(
            model=MODELO,
            file=audio_file,
            language="es",
        )
        texto = transcript.text.strip()
        logger.info(f"Audio transcrito ({len(texto)} chars): {texto[:80]}...")
        return texto

    except Exception as e:
        logger.error(f"Error en transcripción de audio: {e}")
        return None
