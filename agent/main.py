# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await inicializar_db()
    logger.info("Base de datos inicializada")
    logger.info(f"Servidor AgentKit corriendo en puerto {PORT}")
    logger.info(f"Proveedor: {proveedor.__class__.__name__}")
    yield


app = FastAPI(
    title="AgentKit — Brenda (Tintoreros)",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def health_check():
    return {"status": "ok", "agente": "Brenda", "negocio": "Tintoreros"}


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    """Recibe mensajes de WhatsApp, genera respuesta con Gemini y la envía."""
    try:
        mensajes = await proveedor.parsear_webhook(request)
    except Exception as e:
        logger.error(f"Error al parsear webhook: {e}")
        return {"status": "ok"}  # Siempre 200 para que Twilio/Meta no reintente

    for msg in mensajes:
        if msg.es_propio or not msg.texto:
            continue

        logger.info(f"Mensaje de {msg.telefono}: {msg.texto}")

        try:
            historial = await obtener_historial(msg.telefono)
            respuesta = await generar_respuesta(msg.texto, historial)

            await guardar_mensaje(msg.telefono, "user", msg.texto)
            await guardar_mensaje(msg.telefono, "assistant", respuesta)

            enviado = await proveedor.enviar_mensaje(msg.telefono, respuesta)
            if enviado:
                logger.info(f"Respuesta enviada a {msg.telefono}")
            else:
                logger.error(f"Fallo al enviar respuesta a {msg.telefono}")

        except Exception as e:
            logger.error(f"Error procesando mensaje de {msg.telefono}: {e}")
            # Intenta enviar mensaje de error al usuario para que no quede en silencio
            try:
                await proveedor.enviar_mensaje(
                    msg.telefono,
                    "Lo siento, tuve un problema técnico. Por favor intenta de nuevo en un momento."
                )
            except Exception:
                pass

    return {"status": "ok"}
