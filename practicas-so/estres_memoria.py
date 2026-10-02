"""
estres_memoria.py — Estrés de Memoria y Paginación
===================================================

Concepto de SO: MEMORIA VIRTUAL y PAGINACIÓN.
Cada proceso ve un espacio de direcciones virtual propio, dividido en páginas
(4 KB en x86-64). El SO decide qué páginas están en RAM física (marcos) y
cuáles se mandan al ARCHIVO DE PAGINACIÓN (pagefile.sys en Windows, "swap" en
Linux) cuando la RAM se llena.

Conceptos que se observan al ejecutar este script:
  * RSS / Working Set: páginas del proceso que están AHORA en RAM física.
  * Memoria privada / "Confirmada" (commit): memoria que el SO garantiza al
    proceso, esté en RAM o en el archivo de paginación. En Windows el límite
    de memoria confirmada = RAM + tamaño del archivo de paginación.
  * Uso del archivo de paginación (psutil.swap_memory()): crece cuando el SO
    expulsa páginas de RAM al disco para hacer sitio (page-out).

El script reserva memoria poco a poco con un LÍMITE DE SEGURIDAD para no
congelar la PC: se detiene y libera todo si la RAM del sistema supera un %
o si el propio proceso supera X GB.

Uso:
    python estres_memoria.py                          # límites: 90 % RAM o 4 GB
    python estres_memoria.py --max-ram 85 --max-gb 2
    python estres_memoria.py --max-gb 0.5 --bloque 500000   # prueba corta
"""

import argparse
import gc
import os
import sys
import time

import psutil

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GB = 1024 ** 3
MB = 1024 ** 2


def mostrar_instrucciones():
    print("=" * 72)
    print(" ESTRÉS DE MEMORIA Y PAGINACIÓN")
    print("=" * 72)
    print(" Antes de continuar, abre el Administrador de tareas para observarlo:")
    print("   1. Pulsa Ctrl + Shift + Esc")
    print("   2. Ve a la pestaña 'Rendimiento' > 'Memoria'")
    print("   3. Observa 'En uso', 'Confirmada' (X/Y GB) y el gráfico de memoria.")
    print("      'Confirmada' = memoria virtual reservada (RAM + archivo de paginación).")
    print("   4. En 'Detalles' puedes buscar este proceso python.exe, PID", os.getpid())
    print(" Pulsa Ctrl+C en cualquier momento para detener y liberar la memoria.")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(description="Consume memoria progresivamente con límites de seguridad.")
    parser.add_argument("--max-ram", type=float, default=90.0,
                        help="%% de RAM del sistema a partir del cual se detiene (por defecto 90)")
    parser.add_argument("--max-gb", type=float, default=4.0,
                        help="GB máximos que puede ocupar este proceso (por defecto 4)")
    parser.add_argument("--bloque", type=int, default=1_000_000,
                        help="strings que se agregan por iteración (por defecto 1.000.000)")
    parser.add_argument("--pausa", type=float, default=0.5,
                        help="segundos de pausa entre iteraciones (por defecto 0.5)")
    parser.add_argument("--espera-inicial", type=float, default=5,
                        help="segundos para abrir el Administrador de tareas antes de empezar (por defecto 5)")
    args = parser.parse_args()

    mostrar_instrucciones()
    print(f" Límites de seguridad: RAM del sistema > {args.max_ram:g} %  "
          f"o  proceso > {args.max_gb:.2f} GB")
    if args.espera_inicial > 0:
        print(f" Empezando en {args.espera_inicial:.0f} s...")
        time.sleep(args.espera_inicial)
    print()

    proceso = psutil.Process()  # el proceso actual (nuestro propio PID)
    datos = []  # aquí se acumulan los strings que consumen memoria
    iteracion = 0
    motivo = ""

    print(f"{'Iter':>5} {'Strings':>12} {'RSS proceso':>12} {'Privada':>10} "
          f"{'RAM sist.':>10} {'Paginación usada':>22}")
    print("-" * 76)

    try:
        while True:  # bucle "infinito": solo sale por los límites o por Ctrl+C
            # --- Medir ANTES de reservar más, para respetar los límites ---
            info = proceso.memory_info()
            # rss = Working Set: páginas residentes en RAM física.
            # vms = en Windows es la memoria privada confirmada (Private Bytes),
            #       que cuenta contra el límite de "Confirmada".
            rss_gb = info.rss / GB
            ram = psutil.virtual_memory()
            swap = psutil.swap_memory()  # en Windows: uso del archivo de paginación

            print(f"{iteracion:>5} {len(datos):>12,} {info.rss / MB:>9,.0f} MB "
                  f"{info.vms / MB:>7,.0f} MB {ram.percent:>8.1f} % "
                  f"{swap.used / GB:>7.2f}/{swap.total / GB:.2f} GB ({swap.percent:4.1f}%)")

            # --- LÍMITES DE SEGURIDAD ---
            if ram.percent >= args.max_ram:
                motivo = f"la RAM del sistema llegó al {ram.percent:.1f} % (límite {args.max_ram:g} %)"
                break
            if rss_gb >= args.max_gb:
                motivo = f"el proceso ocupa {rss_gb:.2f} GB (límite {args.max_gb:.2f} GB)"
                break

            # --- Consumir memoria ---
            # Cada string es un objeto distinto en el heap (~70 bytes con su
            # cabecera). Al crecer el heap, Python pide más páginas al SO
            # (VirtualAlloc en Windows); el SO las confirma y les asigna marcos
            # de RAM cuando se escriben por primera vez (fallo de página).
            base = iteracion * args.bloque
            datos.extend(f"pagina-{base + i:012d}-memoria-virtual" for i in range(args.bloque))
            iteracion += 1
            time.sleep(args.pausa)
    except KeyboardInterrupt:
        motivo = "el usuario pulsó Ctrl+C"
    finally:
        # --- LIBERAR LA MEMORIA ---
        # Al borrar la única referencia a la lista, Python destruye los objetos
        # y devuelve las páginas al SO (VirtualFree). La memoria "Confirmada"
        # del Administrador de tareas debería bajar de golpe.
        antes = proceso.memory_info().rss
        cantidad = len(datos)
        datos.clear()
        del datos
        gc.collect()
        despues = proceso.memory_info().rss

        print("-" * 76)
        print(f"DETENIDO: {motivo or 'fin de la ejecución'}.")
        print(f"Se liberaron {cantidad:,} strings: RSS {antes / MB:,.0f} MB -> {despues / MB:,.0f} MB")
        print(f"RAM del sistema ahora: {psutil.virtual_memory().percent:.1f} %")


if __name__ == "__main__":
    main()
