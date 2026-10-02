"""
simulador_cache.py — Simulador de Memoria Caché
================================================

Concepto de SO: JERARQUÍA DE MEMORIA.
    registros  →  caché L1/L2/L3  →  RAM  →  SSD/HDD
    (más rápido, más caro, más pequeño)  ...  (más lento, más barato, más grande)

Una caché guarda una copia de los datos en un nivel más rápido para no tener
que volver a buscarlos en el nivel lento. Aquí la simulamos con un diccionario
de Python que vive en RAM y guarda {ruta_archivo: contenido}:

  * CACHE MISS: el dato no está en la caché → hay que ir al disco (lento),
    pasando por llamadas al sistema (CreateFile/ReadFile) y copiando los bytes
    al espacio de memoria de nuestro proceso. Después se guarda en la caché.
  * CACHE HIT:  el dato ya está en la caché → se devuelve directamente desde
    RAM, sin llamadas al sistema ni copias.

Nota: Windows también tiene su PROPIA caché de archivos (la "caché del sistema"
o memoria "En espera" del Administrador de tareas). Por eso un archivo recién
creado o leído hace poco puede leerse más rápido que desde el disco físico.
Aun así, nuestra caché es mucho más rápida porque evita llamadas al sistema
y la copia de cientos de MB.

Uso:
    python simulador_cache.py                            # 2 archivos de 150 MB, 5 lecturas
    python simulador_cache.py --tamano-mb 20 --archivos 1 --lecturas 3
    python simulador_cache.py --borrar                   # elimina archivos_prueba al final
"""

import argparse
import os
import shutil
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "archivos_prueba")
MB = 1024 ** 2

# La "memoria caché": un diccionario en RAM.  ruta -> contenido (bytes)
cache = {}


def generar_archivos(cantidad, tamano_mb):
    """
    Crea archivos de prueba con datos aleatorios si no existen (o si tienen
    otro tamaño). Se escribe en bloques de 8 MB para no tener que reservar
    todo el archivo en RAM de una vez.
    """
    os.makedirs(CARPETA, exist_ok=True)
    rutas = []
    for i in range(1, cantidad + 1):
        ruta = os.path.join(CARPETA, f"prueba_{i}_{tamano_mb}MB.bin")
        rutas.append(ruta)
        if os.path.exists(ruta) and os.path.getsize(ruta) == tamano_mb * MB:
            print(f"  [ya existe] {os.path.basename(ruta)}")
            continue
        print(f"  [generando] {os.path.basename(ruta)} ({tamano_mb} MB)...", end="", flush=True)
        bloque = 8 * MB
        restantes = tamano_mb * MB
        with open(ruta, "wb") as f:
            while restantes > 0:
                n = min(bloque, restantes)
                f.write(os.urandom(n))  # datos aleatorios: no se pueden comprimir
                restantes -= n
        print(" listo")
    return rutas


def leer_archivo(ruta):
    """
    Lee un archivo usando la caché.
    Devuelve (contenido, tipo_acceso, segundos).
    """
    inicio = time.perf_counter()  # reloj de alta resolución del SO (QueryPerformanceCounter)

    if ruta in cache:
        # CACHE HIT: el contenido ya está en RAM, en el espacio de nuestro proceso.
        contenido = cache[ruta]
        tipo = "HIT"
    else:
        # CACHE MISS: hay que pedirle al SO que lea desde el disco.
        # Esto implica: llamada al sistema → driver de disco → DMA → buffer
        # del kernel → copia al buffer de nuestro proceso.
        with open(ruta, "rb") as f:
            contenido = f.read()
        cache[ruta] = contenido  # se guarda en el nivel rápido para la próxima vez
        tipo = "MISS"

    return contenido, tipo, time.perf_counter() - inicio


def formato_tiempo(seg):
    """Muestra el tiempo en la unidad más legible."""
    if seg >= 1:
        return f"{seg:.3f} s"
    if seg >= 1e-3:
        return f"{seg * 1e3:.3f} ms"
    return f"{seg * 1e6:.3f} µs"


def main():
    parser = argparse.ArgumentParser(description="Simulador de caché: disco vs RAM.")
    parser.add_argument("--archivos", type=int, default=2, help="cantidad de archivos de prueba (por defecto 2)")
    parser.add_argument("--tamano-mb", type=int, default=150, help="tamaño de cada archivo en MB (por defecto 150)")
    parser.add_argument("--lecturas", type=int, default=5, help="lecturas por archivo (por defecto 5)")
    parser.add_argument("--borrar", action="store_true", help="borrar la carpeta archivos_prueba al terminar")
    args = parser.parse_args()

    print("=== SIMULADOR DE MEMORIA CACHÉ ===\n")
    print(f"Preparando archivos de prueba en: {CARPETA}")
    rutas = generar_archivos(args.archivos, args.tamano_mb)

    # ---- Lecturas detalladas ----
    print(f"\n{'Archivo':<26}{'Lectura':>8}{'Acceso':>8}{'Origen':>10}{'Tiempo':>16}")
    print("-" * 68)
    resultados = {}  # ruta -> {"MISS": [...], "HIT": [...]}
    for ruta in rutas:
        resultados[ruta] = {"MISS": [], "HIT": []}
        for n in range(1, args.lecturas + 1):
            contenido, tipo, seg = leer_archivo(ruta)
            resultados[ruta][tipo].append(seg)
            origen = "disco" if tipo == "MISS" else "caché"
            print(f"{os.path.basename(ruta):<26}{n:>8}{tipo:>8}{origen:>10}{formato_tiempo(seg):>16}")
        print("-" * 68)

    # ---- Tabla comparativa ----
    print("\nCOMPARATIVA (1ª lectura desde disco vs promedio de lecturas desde caché)\n")
    print(f"{'Archivo':<26}{'Disco (MISS)':>16}{'Caché (HIT)':>16}{'Veces más rápido':>20}")
    print("=" * 78)
    for ruta, r in resultados.items():
        t_disco = r["MISS"][0]
        if r["HIT"]:
            t_cache = sum(r["HIT"]) / len(r["HIT"])
            veces = t_disco / t_cache if t_cache > 0 else float("inf")
            print(f"{os.path.basename(ruta):<26}{formato_tiempo(t_disco):>16}"
                  f"{formato_tiempo(t_cache):>16}{veces:>18,.0f}x")
        else:
            print(f"{os.path.basename(ruta):<26}{formato_tiempo(t_disco):>16}{'(sin hits)':>16}")

    total_mb = sum(len(c) for c in cache.values()) / MB
    print(f"\nLa caché ocupa ahora ~{total_mb:.0f} MB de RAM en este proceso "
          f"({len(cache)} entradas).")
    print("Conclusión: un HIT solo busca la clave en un diccionario (tabla hash en RAM);")
    print("un MISS requiere llamadas al sistema, E/S de disco y copiar todos los bytes.")

    # Liberar la caché: al eliminar las referencias, Python devuelve la memoria
    # y el SO puede reasignar esos marcos de página a otros procesos.
    cache.clear()

    if args.borrar:
        shutil.rmtree(CARPETA, ignore_errors=True)
        print(f"\nCarpeta {CARPETA} eliminada.")


if __name__ == "__main__":
    main()
