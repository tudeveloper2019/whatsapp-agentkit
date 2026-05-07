# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
# Generado por AgentKit para El Cortijo Parque Acuático

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial
from agent.providers import obtener_proveedor
from agent.transcriber import transcribir_audio, MENSAJE_FALLO as AUDIO_FALLO

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("agentkit")

proveedor = obtener_proveedor()
PORT = int(os.getenv("PORT", 8000))
BASE_URL = os.getenv("BASE_URL", f"http://localhost:{PORT}")

MENU_PDF = f"{BASE_URL}/static/menu/menu.pdf"

KEYWORDS_MENU = ["menú", "menu", "carta", "qué tienen de comer", "que tienen de comer"]


def solicita_menu(texto: str) -> bool:
    t = texto.lower()
    return any(k in t for k in KEYWORDS_MENU)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await inicializar_db()
    logger.info("Base de datos inicializada")
    logger.info(f"Servidor AgentKit corriendo en puerto {PORT}")
    logger.info(f"Proveedor de WhatsApp: {proveedor.__class__.__name__}")
    yield


app = FastAPI(
    title="AgentKit — Sofía | El Cortijo Parque Acuático",
    version="1.0.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def health_check():
    return {"status": "ok", "agente": "Sofía", "negocio": "El Cortijo Parque Acuático"}


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    """
    Recibe mensajes de WhatsApp via Twilio.
    Soporta texto, audio/notas de voz y solicitudes de menú (envía PDF).
    """
    try:
        mensajes = await proveedor.parsear_webhook(request)

        for msg in mensajes:
            if msg.es_propio:
                continue

            historial = await obtener_historial(msg.telefono)
            texto_efectivo = msg.texto

            # — Audio: transcribir primero —
            if msg.audio_url:
                logger.info(f"Audio recibido de {msg.telefono} ({msg.audio_content_type})")
                transcripcion = await transcribir_audio(msg.audio_url)

                if not transcripcion:
                    await guardar_mensaje(msg.telefono, "user", "[Audio no transcribible]")
                    await guardar_mensaje(msg.telefono, "assistant", AUDIO_FALLO)
                    await proveedor.enviar_mensaje(msg.telefono, AUDIO_FALLO)
                    continue

                logger.info(f"Transcripción de {msg.telefono}: {transcripcion}")
                texto_efectivo = transcripcion

            if not texto_efectivo:
                continue

            logger.info(f"Mensaje de {msg.telefono}: {texto_efectivo}")

            # — Menú: enviar PDF —
            if solicita_menu(texto_efectivo):
                await proveedor.enviar_media(msg.telefono, MENU_PDF)
                respuesta = "¡Aquí está nuestro menú completo! 🍽️😊 ¿Hay algo que te llame la atención o te gustaría pedir?"
            else:
                respuesta = await generar_respuesta(texto_efectivo, historial)

            await guardar_mensaje(msg.telefono, "user", texto_efectivo)
            await guardar_mensaje(msg.telefono, "assistant", respuesta)
            await proveedor.enviar_mensaje(msg.telefono, respuesta)

            logger.info(f"Respuesta a {msg.telefono}: {respuesta}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
