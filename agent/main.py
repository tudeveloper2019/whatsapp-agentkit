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

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("agentkit")

proveedor = obtener_proveedor()
PORT = int(os.getenv("PORT", 8000))
BASE_URL = os.getenv("BASE_URL", f"http://localhost:{PORT}")

MENU_IMG_1 = f"{BASE_URL}/static/menu/menu1.jpeg"
MENU_IMG_2 = f"{BASE_URL}/static/menu/menu2.png"

# Palabras que indican que el cliente quiere ver el menú completo
KEYWORDS_MENU = ["menú", "menu", "carta", "qué tienen de comer", "que tienen de comer"]


def solicita_menu(texto: str) -> bool:
    t = texto.lower()
    return any(k in t for k in KEYWORDS_MENU)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar el servidor."""
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
    """Endpoint de salud para Railway/monitoreo."""
    return {"status": "ok", "agente": "Sofía", "negocio": "El Cortijo Parque Acuático"}


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    """Verificación GET del webhook (requerido por Meta Cloud API, no-op para Twilio)."""
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    """
    Recibe mensajes de WhatsApp via Twilio.
    Si piden el menú, envía las 2 imágenes. Resto de mensajes los responde Claude.
    """
    try:
        mensajes = await proveedor.parsear_webhook(request)

        for msg in mensajes:
            if msg.es_propio or not msg.texto:
                continue

            logger.info(f"Mensaje de {msg.telefono}: {msg.texto}")

            historial = await obtener_historial(msg.telefono)

            if solicita_menu(msg.texto):
                # Enviar las 2 imágenes del menú
                await proveedor.enviar_media(msg.telefono, MENU_IMG_1)
                await proveedor.enviar_media(msg.telefono, MENU_IMG_2)
                respuesta = "¡Aquí está nuestro menú completo! 🍽️😊 ¿Hay algo que te llame la atención o te gustaría pedir?"
            else:
                respuesta = await generar_respuesta(msg.texto, historial)

            await guardar_mensaje(msg.telefono, "user", msg.texto)
            await guardar_mensaje(msg.telefono, "assistant", respuesta)
            await proveedor.enviar_mensaje(msg.telefono, respuesta)

            logger.info(f"Respuesta a {msg.telefono}: {respuesta}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
