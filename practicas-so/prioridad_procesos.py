"""
prioridad_procesos.py — Prioridad de Procesos
==============================================

Concepto de SO: PLANIFICACIÓN (SCHEDULING) POR PRIORIDADES.
El planificador del SO decide qué hilo se ejecuta en cada núcleo y durante
cuánto tiempo (quantum). Windows usa 32 niveles de prioridad; cada proceso
tiene una CLASE de prioridad que fija el nivel base de sus hilos:

    IDLE_PRIORITY_CLASS      (base 4)   → "baja": solo corre si nadie más quiere la CPU
    NORMAL_PRIORITY_CLASS    (base 8)   → la de casi todos los programas
    HIGH_PRIORITY_CLASS      (base 13)  → "alta"
    REALTIME_PRIORITY_CLASS  (base 24)  → "tiempo real": por encima de muchos
                                          hilos del propio sistema

Fijar la prioridad de "tiempo real" requiere el privilegio SeIncreaseBasePriority
(terminal como Administrador). Sin él, Windows NO da error: simplemente aplica
HIGH_PRIORITY_CLASS. Este script lo detecta leyendo la prioridad real después
de cambiarla.

Uso:
    python prioridad_procesos.py --prioridad baja
    python prioridad_procesos.py --prioridad tiempo_real --nucleo 0
    python prioridad_procesos.py --prioridad alta --n 200000      # prueba rápida
"""

import argparse
import os
import sys
import time

import psutil

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ES_WINDOWS = os.name == "nt"

if ES_WINDOWS:
    PRIORIDADES = {
        "baja": psutil.IDLE_PRIORITY_CLASS,
        "normal": psutil.NORMAL_PRIORITY_CLASS,
        "alta": psutil.HIGH_PRIORITY_CLASS,
        "tiempo_real": psutil.REALTIME_PRIORITY_CLASS,
    }
    NOMBRES = {
        psutil.IDLE_PRIORITY_CLASS: "IDLE_PRIORITY_CLASS (baja)",
        psutil.BELOW_NORMAL_PRIORITY_CLASS: "BELOW_NORMAL_PRIORITY_CLASS",
        psutil.NORMAL_PRIORITY_CLASS: "NORMAL_PRIORITY_CLASS",
        psutil.ABOVE_NORMAL_PRIORITY_CLASS: "ABOVE_NORMAL_PRIORITY_CLASS",
        psutil.HIGH_PRIORITY_CLASS: "HIGH_PRIORITY_CLASS (alta)",
        psutil.REALTIME_PRIORITY_CLASS: "REALTIME_PRIORITY_CLASS (tiempo real)",
    }
else:
    # En Linux/macOS la prioridad es el valor "nice" (-20 = máxima, 19 = mínima).
    # Bajar el nice (subir prioridad) también requiere ser root.
    PRIORIDADES = {"baja": 19, "normal": 0, "alta": -10, "tiempo_real": -20}
    NOMBRES = {}


def nombre_prioridad(valor):
    return NOMBRES.get(valor, f"nice={valor}")


def aplicar_prioridad(proceso, clave):
    """
    Cambia la prioridad del propio proceso y verifica cuál se aplicó realmente.
    Devuelve (prioridad_efectiva, aviso_o_None). Nunca lanza excepción.
    """
    deseada = PRIORIDADES[clave]
    aviso = None
    try:
        # psutil → SetPriorityClass() en Windows / setpriority() en Unix
        proceso.nice(deseada)
    except psutil.AccessDenied:
        aviso = ("Permiso denegado para cambiar a esa prioridad. "
                 "Ejecuta la terminal como Administrador.")
    except (OSError, ValueError) as e:
        aviso = f"No se pudo cambiar la prioridad: {e}"

    efectiva = proceso.nice()  # GetPriorityClass(): lo que el SO aplicó de verdad
    if aviso is None and efectiva != deseada:
        if ES_WINDOWS and clave == "tiempo_real" and efectiva == psutil.HIGH_PRIORITY_CLASS:
            aviso = ("Windows no concedió TIEMPO REAL (hace falta terminal como Administrador) "
                     "y la bajó a ALTA (HIGH_PRIORITY_CLASS).")
        else:
            aviso = (f"Se pidió {nombre_prioridad(deseada)} pero el SO aplicó "
                     f"{nombre_prioridad(efectiva)}.")
    return efectiva, aviso


def fijar_nucleo(proceso, nucleo):
    """
    Afinidad de CPU: restringe en qué núcleos puede planificarse el proceso.
    Si dos procesos están fijados al MISMO núcleo, compiten por él y el
    planificador debe elegir según su prioridad.
    """
    try:
        proceso.cpu_affinity([nucleo])  # SetProcessAffinityMask() en Windows
        return None
    except (AttributeError, psutil.AccessDenied, ValueError, OSError) as e:
        return f"No se pudo fijar la afinidad al núcleo {nucleo}: {e}"


def contar_primos(n):
    """
    Trabajo puramente de CPU (CPU-bound): cuenta primos <= n por división
    de prueba. No hace E/S, así que el proceso nunca se bloquea: siempre está
    en estado "listo" o "ejecutando" y su avance depende solo de cuánto tiempo
    de CPU le conceda el planificador.
    """
    cuenta = 0
    for k in range(2, n + 1):
        if k % 2 == 0:
            cuenta += k == 2
            continue
        d = 3
        primo = True
        while d * d <= k:
            if k % d == 0:
                primo = False
                break
            d += 2
        cuenta += primo
    return cuenta


def main():
    parser = argparse.ArgumentParser(description="Cálculo pesado de CPU con prioridad configurable.")
    parser.add_argument("--prioridad", choices=["baja", "normal", "alta", "tiempo_real"], default="normal",
                        help="clase de prioridad del proceso (por defecto normal)")
    parser.add_argument("--n", type=int, default=4_000_000,
                        help="contar primos hasta N (por defecto 4.000.000, ~10-30 s según la PC)")
    parser.add_argument("--nucleo", type=int, default=None,
                        help="fijar el proceso a este núcleo de CPU (opcional, p. ej. 0)")
    parser.add_argument("--etiqueta", default="", help="nombre a mostrar en la salida (lo usa el lanzador)")
    args = parser.parse_args()

    proceso = psutil.Process()
    tag = f"[{args.etiqueta or args.prioridad} | PID {proceso.pid}]"

    efectiva, aviso = aplicar_prioridad(proceso, args.prioridad)
    print(f"{tag} Prioridad solicitada: {args.prioridad}  ->  aplicada: {nombre_prioridad(efectiva)}", flush=True)
    if aviso:
        print(f"{tag} AVISO: {aviso}", flush=True)

    if args.nucleo is not None:
        error = fijar_nucleo(proceso, args.nucleo)
        print(f"{tag} {error or f'Afinidad fijada al núcleo {args.nucleo}'}", flush=True)

    print(f"{tag} Calculando primos hasta {args.n:,}...", flush=True)
    inicio = time.perf_counter()
    cpu_inicio = proceso.cpu_times()
    primos = contar_primos(args.n)
    duracion = time.perf_counter() - inicio
    cpu_fin = proceso.cpu_times()
    cpu_usada = (cpu_fin.user - cpu_inicio.user) + (cpu_fin.system - cpu_inicio.system)

    # Tiempo real (reloj de pared) vs tiempo de CPU: si el proceso tuvo que
    # esperar a que el planificador le diera la CPU, el tiempo de pared será
    # mayor que el de CPU. Esa diferencia es el tiempo en la cola de "listos".
    print(f"{tag} Resultado: {primos:,} primos", flush=True)
    print(f"{tag} Tiempo total: {duracion:.2f} s  |  tiempo de CPU: {cpu_usada:.2f} s  |  "
          f"esperando la CPU: {max(0.0, duracion - cpu_usada):.2f} s", flush=True)
    print(f"{tag} PID: {proceso.pid}  |  Prioridad: {nombre_prioridad(efectiva)}", flush=True)


if __name__ == "__main__":
    main()
