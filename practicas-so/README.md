# practicas-so

Prácticas de **Sistemas Operativos** en Python 3 con [psutil](https://pypi.org/project/psutil/).
Son 4 scripts independientes (más un lanzador), y cada uno demuestra un concepto del SO.
Los scripts están probados en Windows 11 y tienen comentarios en español.

| Script | Concepto de SO |
|---|---|
| `monitor_recursos.py` | Gestión de recursos (CPU/RAM) y E/S a archivo |
| `simulador_cache.py` | Jerarquía de memoria y caché (HIT / MISS) |
| `estres_memoria.py` | Memoria virtual, paginación y swap |
| `prioridad_procesos.py` + `comparar_prioridades.py` | Planificación por prioridades y afinidad de CPU |

## Instalación

```powershell
cd practicas-so
python -m pip install -r requirements.txt
```

Todos los scripts aceptan `--help` para ver sus opciones.

---

## 1) monitor_recursos.py: Vigilante de Recursos

Muestra un panel en consola con el % de CPU y de RAM y la RAM usada/total en GB. Se actualiza cada segundo.
Si la RAM supera el umbral, muestra una **ALERTA** y agrega una línea a `log_ram.txt` con fecha/hora, % de RAM y % de CPU.

```powershell
python monitor_recursos.py                      # umbral 80 %, intervalo 1 s, hasta Ctrl+C
python monitor_recursos.py --umbral 30          # umbral bajo para forzar la alerta
python monitor_recursos.py --intervalo 2 --duracion 10   # cada 2 s, se detiene a los 10 s
python monitor_recursos.py --sin-limpiar        # no borra la pantalla (historial visible)
```

Se detiene con **Ctrl+C**.

## 2) simulador_cache.py: Simulador de Memoria Caché

Si no existen, genera archivos de prueba en `archivos_prueba/` (por defecto 2 de 150 MB).
Después lee cada archivo varias veces. La primera lectura va al disco (**MISS**) y las siguientes salen del diccionario en RAM (**HIT**).
Al final muestra una tabla comparativa con cuántas veces más rápido es la caché.

```powershell
python simulador_cache.py                                    # 2 archivos x 150 MB, 5 lecturas
python simulador_cache.py --archivos 3 --tamano-mb 200 --lecturas 5
python simulador_cache.py --tamano-mb 20 --archivos 1        # prueba rápida
python simulador_cache.py --borrar                           # borra archivos_prueba al terminar
```

> La caché guarda los archivos completos en RAM: con 2 x 150 MB necesitas unos 300 MB libres.
> Nota: Windows también tiene su propia caché de archivos. Si el archivo se acaba de crear, la lectura de "disco" probablemente salga de esa caché del SO.
> Para medir el disco real, reinicia la PC antes de ejecutar el script (los archivos ya existirán).

## 3) estres_memoria.py: Estrés de Memoria y Paginación

Agrega millones de strings a una lista en un bucle sin fin. En cada iteración muestra:
- el RSS del proceso
- la memoria privada (*commit*)
- el % de RAM del sistema
- el uso del archivo de paginación

**Límites de seguridad**: el script se detiene y libera la memoria si la RAM del sistema supera `--max-ram` (90 % por defecto) o si el proceso supera `--max-gb` (4 GB por defecto).
También puedes detenerlo con **Ctrl+C**, y la memoria se libera igual.

```powershell
python estres_memoria.py                          # límites: 90 % RAM o 4 GB
python estres_memoria.py --max-ram 85 --max-gb 2
python estres_memoria.py --max-gb 0.3 --bloque 300000 --espera-inicial 0   # prueba rápida
```

Mientras corre, abre el Administrador de tareas (**Ctrl+Shift+Esc → Rendimiento → Memoria**) y observa cómo suben "En uso" y **"Confirmada"**.
Cuando el script libera la memoria, verás que bajan de golpe.

> Si tu RAM ya está por encima del límite (p. ej. 92 % con `--max-ram 90`), el script se detiene en la iteración 0. Es el comportamiento esperado.
> Para ver actividad del archivo de paginación, cierra programas o sube `--max-ram` con cuidado (por ejemplo a 95).

## 4) prioridad_procesos.py: Prioridad de Procesos

Hace un cálculo pesado de CPU: cuenta los primos hasta N. Con N = 4.000.000 tarda unos 10–30 s.
Antes de empezar, cambia su propia prioridad:

| `--prioridad` | Clase en Windows |
|---|---|
| `baja` | `IDLE_PRIORITY_CLASS` |
| `normal` | `NORMAL_PRIORITY_CLASS` |
| `alta` | `HIGH_PRIORITY_CLASS` |
| `tiempo_real` | `REALTIME_PRIORITY_CLASS` |

Al terminar muestra:
- el PID
- la prioridad que aplicó el SO
- el tiempo total
- el tiempo de CPU
- el tiempo que pasó **esperando la CPU**

```powershell
python prioridad_procesos.py --prioridad baja
python prioridad_procesos.py --prioridad tiempo_real --nucleo 0
python prioridad_procesos.py --prioridad alta --n 500000      # prueba rápida
```

### comparar_prioridades.py: la carrera

Lanza a la vez dos procesos con `subprocess`, uno con prioridad `baja` y otro con `tiempo_real`.
Por defecto los fija a ambos al **mismo núcleo** (`cpu_affinity`) para que compitan por la misma CPU.
Al final indica cuál terminó primero y con cuántos segundos de diferencia.

```powershell
python comparar_prioridades.py                  # ambos en el núcleo 0
python comparar_prioridades.py --n 1000000      # prueba rápida (~4 s)
python comparar_prioridades.py --sin-afinidad   # sin fijar núcleo: la diferencia casi desaparece
```

**Permisos:** la prioridad de tiempo real necesita una terminal **ejecutada como Administrador**.
Sin esos permisos, Windows aplica *Alta* sin dar error. El script lo detecta y muestra un **AVISO**, pero sigue funcionando.

> Cuidado: con permisos de administrador, un proceso en tiempo real fijado a un núcleo lo acapara por completo hasta terminar.
> Es normal que el sistema se sienta algo más lento durante esos segundos.
