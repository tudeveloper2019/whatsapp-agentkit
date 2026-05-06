# agent/tools.py — Herramientas del agente
# Generado por AgentKit para El Cortijo Centro Parque Acuático

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


def obtener_horario() -> dict:
    """Retorna el horario de atención del parque."""
    info = cargar_info_negocio()
    ahora = datetime.now()
    dia_semana = ahora.weekday()  # 0=lunes, 6=domingo
    hora_actual = ahora.hour

    # Martes (1) está cerrado; resto abre 9-17
    esta_abierto = dia_semana != 1 and 9 <= hora_actual < 17

    return {
        "horario": info.get("negocio", {}).get("horario", "Miércoles a Lunes de 9AM a 5PM"),
        "esta_abierto": esta_abierto,
    }


def obtener_precios() -> dict:
    """Retorna la información de precios del parque."""
    return {
        "entrada_general": "$35.000 por persona",
        "promociones": "2x1 en fechas especiales (consultar disponibilidad)",
        "grupos_empresas": "Consultar precio especial para grupos y eventos empresariales",
    }


def registrar_reserva(telefono: str, nombre: str, fecha: str, personas: int, tipo_visita: str) -> dict:
    """
    Registra una solicitud de reserva.

    Args:
        telefono: Número del cliente
        nombre: Nombre del cliente
        fecha: Fecha deseada de visita
        personas: Número de personas
        tipo_visita: familiar | pareja | grupo | empresarial

    Returns:
        Confirmación con número de reserva
    """
    import random
    numero_reserva = f"EC-{random.randint(1000, 9999)}"
    logger.info(f"Reserva registrada: {numero_reserva} — {nombre} — {fecha} — {personas} personas — {tipo_visita}")
    return {
        "numero_reserva": numero_reserva,
        "nombre": nombre,
        "fecha": fecha,
        "personas": personas,
        "tipo_visita": tipo_visita,
        "estado": "pendiente_confirmacion",
        "mensaje": f"Tu reserva {numero_reserva} fue registrada. El equipo de El Cortijo te confirmará por este mismo chat.",
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

    if resultados:
        return "\n---\n".join(resultados)
    return "No encontré información específica sobre eso en mis archivos."
