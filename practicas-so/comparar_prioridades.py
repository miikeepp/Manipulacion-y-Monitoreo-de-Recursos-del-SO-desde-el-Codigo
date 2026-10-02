"""
comparar_prioridades.py — Lanzador de la carrera de prioridades
================================================================

Concepto de SO: CREACIÓN DE PROCESOS y COMPETENCIA POR LA CPU.
Con subprocess.Popen el SO crea dos procesos hijos nuevos (CreateProcess en
Windows), cada uno con su propio PID y espacio de memoria. Ambos ejecutan el
mismo cálculo, pero uno con prioridad BAJA y otro con TIEMPO REAL.

Si los fijamos al MISMO núcleo (afinidad), solo uno puede ejecutarse a la vez
en él, y el planificador favorece al de mayor prioridad: el de prioridad baja
apenas avanza hasta que el otro termina.

Uso:
    python comparar_prioridades.py                 # ambos en el núcleo 0
    python comparar_prioridades.py --sin-afinidad  # cada uno donde quiera el SO
    python comparar_prioridades.py --n 300000      # prueba rápida
"""

import argparse
import os
import subprocess
import sys
import threading
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prioridad_procesos.py")


def reenviar_salida(proc, nombre):
    """Muestra en vivo lo que imprime cada proceso hijo (leído por su pipe)."""
    for linea in proc.stdout:
        print(linea.rstrip(), flush=True)


def main():
    parser = argparse.ArgumentParser(description="Carrera entre un proceso de prioridad baja y uno de tiempo real.")
    parser.add_argument("--n", type=int, default=4_000_000, help="contar primos hasta N en cada proceso")
    parser.add_argument("--nucleo", type=int, default=0, help="núcleo compartido por ambos (por defecto 0)")
    parser.add_argument("--sin-afinidad", action="store_true", help="no fijar los procesos a un núcleo")
    args = parser.parse_args()

    competidores = [("baja", "BAJA"), ("tiempo_real", "TIEMPO_REAL")]
    print("=== CARRERA DE PRIORIDADES ===")
    print(f"Cálculo: primos hasta {args.n:,} en cada proceso.")
    print("Afinidad: " + ("libre (el SO reparte los núcleos)" if args.sin_afinidad
                          else f"ambos fijados al núcleo {args.nucleo} → compiten por la misma CPU"))
    print("-" * 72, flush=True)

    entorno = dict(os.environ, PYTHONIOENCODING="utf-8")
    procesos = []
    inicio = time.perf_counter()
    for prioridad, etiqueta in competidores:
        cmd = [sys.executable, SCRIPT, "--prioridad", prioridad, "--n", str(args.n), "--etiqueta", etiqueta]
        if not args.sin_afinidad:
            cmd += ["--nucleo", str(args.nucleo)]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace", env=entorno)
        hilo = threading.Thread(target=reenviar_salida, args=(p, etiqueta), daemon=True)
        hilo.start()
        procesos.append({"nombre": etiqueta, "proc": p, "hilo": hilo, "fin": None})

    # Sondeo: anotamos el instante en que termina cada hijo.
    try:
        while any(c["fin"] is None for c in procesos):
            for c in procesos:
                if c["fin"] is None and c["proc"].poll() is not None:
                    c["fin"] = time.perf_counter() - inicio
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nInterrumpido: terminando los procesos hijos...")
        for c in procesos:
            c["proc"].kill()
        return

    for c in procesos:
        c["hilo"].join(timeout=2)

    orden = sorted(procesos, key=lambda c: c["fin"])
    print("-" * 72)
    print("RESULTADO")
    for i, c in enumerate(orden, 1):
        estado = "" if c["proc"].returncode == 0 else f"  (código de salida {c['proc'].returncode})"
        print(f"  {i}º {c['nombre']:<12} PID {c['proc'].pid:<7} terminó a los {c['fin']:.2f} s{estado}")
    diferencia = orden[1]["fin"] - orden[0]["fin"]
    print(f"\nGanó {orden[0]['nombre']}, con {diferencia:.2f} s de ventaja.")
    if orden[0]["nombre"] == "BAJA":
        print("(Resultado inesperado: puede pasar si no se fijó la afinidad y había núcleos libres.)")


if __name__ == "__main__":
    main()
