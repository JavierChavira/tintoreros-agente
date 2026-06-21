# agent/tools.py — Herramientas de Brenda para Tintoreros
import os
import yaml
import logging
from datetime import datetime

logger = logging.getLogger("agentkit")


def cargar_info_negocio() -> dict:
    """Carga la información del negocio desde business.yaml."""
    try:
        with open("config/business.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config/business.yaml no encontrado")
        return {}


def esta_abierto() -> dict:
    """Verifica si el negocio está abierto en este momento."""
    ahora = datetime.now()
    dia = ahora.weekday()  # 0=lunes, 6=domingo
    hora = ahora.hour + ahora.minute / 60

    if dia == 6:  # domingo
        return {"abierto": False, "mensaje": "Hoy es domingo, estamos cerrados. Te atendemos el lunes de 9am a 6pm."}
    elif dia < 5:  # lunes a viernes
        abierto = 9 <= hora < 18
        horario = "Lunes a Viernes de 9am a 6pm"
    else:  # sábado y festivos
        abierto = 9 <= hora < 15
        horario = "Sábados y Festivos de 9am a 3pm"

    return {
        "abierto": abierto,
        "horario": horario,
        "mensaje": f"Estamos {'abiertos' if abierto else 'cerrados'}. Nuestro horario es {horario}."
    }


def generar_ticket(servicio: str, prendas: list[dict], telefono: str = "") -> str:
    """
    Genera un resumen de ticket/orden de servicio.

    Args:
        servicio: Tipo de servicio (tintoreria, planchado, costura)
        prendas: Lista de dicts con 'prenda', 'cantidad' y 'precio_unitario'
        telefono: Número del cliente

    Returns:
        Texto formateado del ticket
    """
    ahora = datetime.now()
    folio = ahora.strftime("%Y%m%d%H%M")

    total = sum(p.get("cantidad", 1) * p.get("precio_unitario", 0) for p in prendas)

    lineas = [
        "🧺 *TINTOREROS - Orden de Servicio*",
        f"📋 Folio: {folio}",
        f"📅 Fecha: {ahora.strftime('%d/%m/%Y %H:%M')}",
        f"🔧 Servicio: {servicio.capitalize()}",
        "─────────────────────",
    ]

    for p in prendas:
        nombre = p.get("prenda", "Prenda")
        cantidad = p.get("cantidad", 1)
        precio = p.get("precio_unitario", 0)
        subtotal = cantidad * precio
        lineas.append(f"• {nombre} x{cantidad} — ${subtotal}")

    lineas += [
        "─────────────────────",
        f"💰 *Total: ${total}*",
        "",
        "⏰ *Horario de entrega:*",
        "Lun-Vie hasta las 5:00pm",
        "Sábados hasta las 2:00pm",
        "",
        "¡Gracias por confiar en Tintoreros! 🌟",
    ]

    return "\n".join(lineas)


def registrar_pedido(telefono: str, servicio: str, prendas: list[dict]) -> dict:
    """
    Registra un pedido en el sistema (versión básica — sin base de datos dedicada).
    Retorna el resumen del pedido para confirmación.
    """
    total = sum(p.get("cantidad", 1) * p.get("precio_unitario", 0) for p in prendas)
    return {
        "confirmado": True,
        "servicio": servicio,
        "prendas": prendas,
        "total": total,
        "folio": datetime.now().strftime("%Y%m%d%H%M"),
    }


def buscar_en_knowledge(consulta: str) -> str:
    """Busca información relevante en los archivos de /knowledge."""
    resultados = []
    knowledge_dir = "knowledge"

    if not os.path.exists(knowledge_dir):
        return "No hay archivos de conocimiento disponibles."

    for archivo in os.listdir(knowledge_dir):
        ruta = os.path.join(knowledge_dir, archivo)
        if archivo.startswith(".") or not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
                if consulta.lower() in contenido.lower():
                    resultados.append(f"[{archivo}]: {contenido[:500]}")
        except (UnicodeDecodeError, IOError):
            continue

    return "\n---\n".join(resultados) if resultados else "No encontré información específica sobre eso."
