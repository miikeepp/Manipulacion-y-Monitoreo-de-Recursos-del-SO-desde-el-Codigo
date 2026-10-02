"""
monitor_recursos.py — Vigilante de Recursos
============================================

Concepto de SO: el sistema operativo es el GESTOR DE RECURSOS de la máquina.
Lleva la contabilidad de cuánto tiempo de CPU consume cada proceso (planificador)
y de qué marcos de memoria física están ocupados (gestor de memoria). Esa
información la expone a los programas de usuario mediante llamadas al sistema;
en Windows, psutil usa por debajo APIs como GetSystemTimes() y
GlobalMemoryStatusEx().

Además, el script demuestra la E/S a disco: cuando se detecta un problema, se
escribe una línea en un archivo de log. Esa escritura pasa por el sistema de
archivos del SO (buffers en RAM → disco).

Uso:
    python monitor_recursos.py                     # umbral 80 %, cada 1 s
    python monitor_recursos.py --umbral 30         # para forzar la alerta
    python monitor_recursos.py --intervalo 2 --duracion 10
"""

import argparse
import os
import sys
from datetime import datetime

import psutil

# La consola de Windows puede usar una página de códigos antigua (cp1252/cp850);
# forzamos UTF-8 para que las barras y los acentos se vean bien.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# En Windows, esta llamada "vacía" activa el procesamiento de secuencias ANSI
# (colores y limpiar pantalla) en la consola clásica.
os.system("")

ROJO = "\033[91m"
VERDE = "\033[92m"
AMARILLO = "\033[93m"
NEGRITA = "\033[1m"
RESET = "\033[0m"
LIMPIAR = "\033[2J\033[H"  # borra la pantalla y lleva el cursor al inicio

ARCHIVO_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log_ram.txt")
GB = 1024 ** 3


def barra(porcentaje, ancho=40):
    """Dibuja una barra de progreso de texto coloreada según el nivel de uso."""
    llenos = int(ancho * porcentaje / 100)
    color = VERDE if porcentaje < 60 else AMARILLO if porcentaje < 80 else ROJO
    return f"{color}{'█' * llenos}{'░' * (ancho - llenos)}{RESET}"


def registrar_alerta(ram_pct, cpu_pct):
    """
    Agrega una línea al log (modo 'a' = append).
    Concepto de SO: E/S de archivos. open() termina en una llamada al sistema
    (CreateFile/WriteFile en Windows); el SO guarda los datos en su caché de
    escritura y los vuelca al disco. Al cerrar el archivo ('with') se liberan
    el descriptor/handle y los buffers asociados.
    """
    marca = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
        f.write(f"{marca} | RAM: {ram_pct:5.1f} % | CPU: {cpu_pct:5.1f} %\n")


def main():
    parser = argparse.ArgumentParser(description="Panel de control de CPU y RAM en tiempo real.")
    parser.add_argument("--umbral", type=float, default=80.0,
                        help="%% de RAM a partir del cual se genera una alerta (por defecto 80)")
    parser.add_argument("--intervalo", type=float, default=1.0,
                        help="segundos entre mediciones (por defecto 1)")
    parser.add_argument("--duracion", type=float, default=0,
                        help="segundos totales de ejecución; 0 = hasta Ctrl+C (por defecto 0)")
    parser.add_argument("--sin-limpiar", action="store_true",
                        help="no limpiar la pantalla entre mediciones (útil para guardar la salida)")
    args = parser.parse_args()

    n_cpus = psutil.cpu_count(logical=True)
    alertas = 0
    muestras = 0

    # Primera llamada "en vacío": cpu_percent() compara los contadores de tiempo
    # de CPU entre dos instantes. La primera vez no hay instante anterior y
    # devuelve 0.0, así que la descartamos.
    psutil.cpu_percent(interval=None)

    try:
        while True:
            # cpu_percent(interval=X) BLOQUEA el proceso X segundos (queda en
            # estado "en espera", sin consumir CPU) y luego calcula qué fracción
            # de ese tiempo los núcleos NO estuvieron ejecutando el proceso
            # inactivo del sistema (System Idle Process).
            cpu = psutil.cpu_percent(interval=args.intervalo)

            # virtual_memory() devuelve el estado de la memoria FÍSICA:
            # total, disponible (libre + caché reutilizable) y % en uso.
            mem = psutil.virtual_memory()
            usada_gb = (mem.total - mem.available) / GB
            total_gb = mem.total / GB
            muestras += 1

            if not args.sin_limpiar:
                print(LIMPIAR, end="")
            print(f"{NEGRITA}=== VIGILANTE DE RECURSOS ==={RESET}   "
                  f"{datetime.now():%H:%M:%S}   (Ctrl+C para salir)")
            print(f"CPU ({n_cpus} lógicos) {barra(cpu)} {cpu:5.1f} %")
            print(f"RAM               {barra(mem.percent)} {mem.percent:5.1f} %")
            print(f"RAM usada: {usada_gb:.2f} GB / {total_gb:.2f} GB   "
                  f"(disponible: {mem.available / GB:.2f} GB)")
            print(f"Umbral de alerta: {args.umbral:.0f} %   Alertas registradas: {alertas}")

            if mem.percent > args.umbral:
                alertas += 1
                registrar_alerta(mem.percent, cpu)
                print(f"\n{ROJO}{NEGRITA}!!! ALERTA: la RAM está al {mem.percent:.1f} % "
                      f"(umbral {args.umbral:.0f} %) — registrado en {os.path.basename(ARCHIVO_LOG)}{RESET}")

            if args.sin_limpiar:
                print("-" * 70)

            if args.duracion and muestras * args.intervalo >= args.duracion:
                break
    except KeyboardInterrupt:
        # Ctrl+C: Windows envía el evento CTRL_C_EVENT a la consola y Python lo
        # convierte en KeyboardInterrupt, lo que nos permite terminar con orden.
        pass

    print(f"\n{RESET}Monitor detenido. Muestras: {muestras}. Alertas: {alertas}.")
    if alertas:
        print(f"Revisa el log en: {ARCHIVO_LOG}")


if __name__ == "__main__":
    main()
