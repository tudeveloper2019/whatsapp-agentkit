# tests/test_local.py — Simulador de chat en terminal
# Generado por AgentKit para El Cortijo Parque Acuático

"""
Prueba a Sofía sin necesitar WhatsApp.
Simula una conversación en la terminal como si fueras un cliente.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial, limpiar_historial
from agent.main import solicita_menu

TELEFONO_TEST = "test-local-001"


async def main():
    """Loop principal del chat de prueba."""
    await inicializar_db()

    print()
    print("=" * 55)
    print("   El Cortijo Parque Acuático — Test Local")
    print("   Agente: Sofía")
    print("=" * 55)
    print()
    print("  Escribe mensajes como si fueras un cliente.")
    print("  Comandos especiales:")
    print("    'limpiar'  — borra el historial")
    print("    'salir'    — termina el test")
    print()
    print("-" * 55)
    print()

    while True:
        try:
            mensaje = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nTest finalizado.")
            break

        if not mensaje:
            continue

        if mensaje.lower() == "salir":
            print("\nTest finalizado. ¡Hasta pronto!")
            break

        if mensaje.lower() == "limpiar":
            await limpiar_historial(TELEFONO_TEST)
            print("[Historial borrado]\n")
            continue

        historial = await obtener_historial(TELEFONO_TEST)

        if solicita_menu(mensaje):
            print("\n  📸 [Imagen del menú — menu.png]")
            respuesta = "¡Aquí está nuestro menú completo! 🍽️😊 ¿Hay algo que te llame la atención o te gustaría pedir?"
            print(f"\nSofía: {respuesta}")
        else:
            print("\nSofía: ", end="", flush=True)
            respuesta = await generar_respuesta(mensaje, historial)
            print(respuesta)

        print()

        await guardar_mensaje(TELEFONO_TEST, "user", mensaje)
        await guardar_mensaje(TELEFONO_TEST, "assistant", respuesta)


if __name__ == "__main__":
    asyncio.run(main())
