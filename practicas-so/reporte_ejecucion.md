# Reporte de ejecución

## Condiciones iniciales

La memoria RAM del equipo se encontraba alrededor del 95-96 %. Por seguridad, el ejercicio de estrés se ejecutó con límites reducidos.

## Ejercicio 1: Monitor de recursos

Comando utilizado:

```powershell
python monitor_recursos.py --umbral 0 --intervalo 1 --duracion 2 --sin-limpiar
```

El monitor realizó 2 mediciones y registró 2 alertas. La RAM estuvo entre 95.6 % y 95.7 %.

Se creó el archivo `log_ram.txt` con las mediciones de fecha, porcentaje de RAM y porcentaje de CPU.

## Ejercicio 2: Simulador de caché

Comando utilizado:

```powershell
python simulador_cache.py --tamano-mb 20 --archivos 1 --lecturas 3 --borrar
```

Resultados:

- Primera lectura, tipo MISS: 20.039 ms.
- Lecturas posteriores, tipo HIT: 1.600 µs y 0.600 µs.
- Promedio de caché: 1.100 µs.
- La caché fue aproximadamente 18.217 veces más rápida.

Los archivos temporales se eliminaron al finalizar.

## Ejercicio 3: Estrés de memoria

Comando utilizado:

```powershell
python estres_memoria.py --max-gb 0.25 --max-ram 95 --bloque 300000 --pausa 0.1 --espera-inicial 0
```

El programa se detuvo en la iteración 0 porque la RAM del sistema alcanzó el 96.1 %, superando el límite configurado del 95 %. No llegó a reservar strings y liberó correctamente la memoria utilizada por el proceso.

## Ejercicio 4: Prioridades de procesos

Comando utilizado:

```powershell
python comparar_prioridades.py --n 500000
```

Resultados:

- El proceso de prioridad alta terminó primero.
- Tiempo del proceso de prioridad alta: 1.04 s.
- Tiempo del proceso de prioridad baja: 1.92 s.
- Diferencia: 0.87 s.
- Windows no concedió prioridad de tiempo real porque la terminal no estaba ejecutándose como Administrador; la aplicó como prioridad alta.

## Conclusión

Los cuatro ejercicios funcionaron correctamente. El monitor detectó y registró el uso elevado de RAM, la caché redujo notablemente el tiempo de lectura, el ejercicio de estrés respetó su límite de seguridad y el proceso con mayor prioridad terminó primero.
