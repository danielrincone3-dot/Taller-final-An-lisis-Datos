# Taller práctico proyecto integrador: calidad de datos para la retención estudiantil

Una institución de educación superior quiere entender qué factores están asociados a la deserción, para diseñar estrategias de retención tempranas. Antes de responder preguntas de análisis, el equipo de datos debe garantizar que la información sea confiable. Este taller trabaja justo ese paso: auditar, limpiar y documentar los datos, y después responder cinco preguntas con esos datos limpios.

Los datos son sintéticos. Fueron generados para el taller y no corresponden a estudiantes reales.

## Requisitos

- Python 3.10 o superior
- Git
- Lo visto en los talleres de Pandas y de limpieza de datos

## Cómo empezar

1. Clona el repositorio y entra a la carpeta del proyecto:

    ```
    git clone <URL-DEL-REPOSITORIO>
    cd <NOMBRE-DE-LA-CARPETA>
    ```

2. Crea y activa un ambiente virtual. Las instrucciones para Windows y Mac/Linux están en `LEEME_ambiente.txt`.

3. Instala las librerías:

    ```
    pip install -r requirements.txt
    ```

4. Ejecuta el script:

    ```
    python analisis_desercion.py
    ```

Ejecuta el comando desde la carpeta del proyecto.

## Estructura del proyecto

```
proyecto/
├── analisis_desercion.py   Script principal. Tiene un TODO por cada paso.
├── requirements.txt        Versiones de las librerías.
├── LEEME_ambiente.txt      Pasos para crear el ambiente virtual.
├── README.md               Este archivo.
├── .gitignore              Archivos que Git no debe subir.
└── Data/
    ├── raw/
    │   └── datos_estudiantes.csv   Dataset original. No lo modifiques.
    └── processed/
        ├── .gitkeep                Mantiene la carpeta en el repositorio.
        ├── dataset_limpio.csv      Lo genera el script. No se sube (está en .gitignore).
        ├── decisiones.csv          Lo genera el script. Sí se sube.
        └── graficos/               Lo genera el script. Sí se sube.
```

Lo que genera el script (`dataset_limpio.csv`, `decisiones.csv` y `graficos/`) aparece en `Data/processed/` al ejecutarlo. Los dos últimos se suben al repositorio, porque son parte de la entrega.

---

# Mis decisiones y respuestas

> **Alumno:** Daniel Herrera  
> **Profesor:** Diego Giraldo  

*Todas las cifras salen de ejecutar `python analisis_desercion.py` (10.150 filas originales → 9.687 limpias).*

### 0. Diccionario de datos (23 columnas originales)
| Columna | Tipo | Rol | Descripción |
| :--- | :--- | :--- | :--- |
| `id_estudiante` | Texto (ID) | Identificación | Código único del estudiante. No se promedia. |
| `programa` | Categórica | Explicativa | Programa académico que cursa (8 válidos). |
| `facultad` | Categórica | Explicativa | Facultad del programa. |
| `jornada` | Categórica | Explicativa | Diurna, Nocturna o Fin de semana. |
| `semestre` | Numérica | Explicativa | Semestre que cursa (1 a 10). |
| `promedio_acumulado` | Numérica | Explicativa | Promedio de notas, escala 0–5. |
| `creditos_aprobados` | Numérica | Explicativa | Créditos aprobados acumulados. |
| `materias_reprobadas` | Numérica | Explicativa | Número de materias perdidas. |
| `asistencia_pct` | Numérica (llega como texto) | Explicativa | % de asistencia; llega con '%' o '-'. |
| `sesiones_tutoria` | Numérica | Explicativa | Sesiones de tutoría asistidas. |
| `cambios_programa` | Numérica | Explicativa | Veces que cambió de programa (0 o 1). |
| `estrato` | Numérica (ordinal) | Explicativa | Estrato socioeconómico 1–6 (sensible). |
| `beca` | Categórica | Explicativa | Si recibe beca (sí/no). |
| `trabaja` | Categórica | Explicativa | Si trabaja (sí/no). |
| `horas_trabajo_semana` | Numérica (llega como texto) | Explicativa | Horas de trabajo por semana; llega con '-'. |
| `distancia_km` | Numérica | Explicativa | Distancia casa–sede; 999 = sin dato. |
| `edad` | Numérica | Explicativa | Edad en años. |
| `genero` | Categórica | Explicativa | Femenino/Masculino (sensible). |
| `ciudad_procedencia` | Categórica | Explicativa | Ciudad de origen (sensible). |
| `tipo_colegio` | Categórica | Explicativa | Colegio público o privado. |
| `fecha_matricula` | Fecha | Explicativa | Fecha de matrícula; llega en dos formatos. |
| `estado` | Categórica | Resultado | activo, graduado o desertor. |
| `motivo_retiro` | Categórica | Resultado | Motivo del retiro; solo existe si ya se retiró (no sirve para predecir). |

Columnas creadas en el paso 9: `desertor` (booleana, resultado) y `cuartil_asistencia` (Q1 a Q4, explicativa).

### 1. Diagnóstico de calidad
- **Nulos reales:** motivo_retiro 6.877 (normal: solo aplica a quien se retiró), promedio_acumulado 304, distancia_km 199, tipo_colegio 152, ciudad_procedencia 103.
- **Faltantes disfrazados:** '-' en asistencia_pct (202) y en horas_trabajo_semana (2.822); 999 en distancia_km (152); 300 asistencias con símbolo '%'.
- **Valores imposibles:** promedio fuera de 0–5 (17, con valores como 45, 62 y 78), edad fuera de 15–80 (12, con 12 y 150 años) y horas de trabajo > 100 (30).
- **Duplicados:** 150 filas idénticas.
- **Errores tipográficos:** programa ('Ingenieria de Sistemas', 'Psicologia'), jornada (minúsculas, espacios), género (M, F, femenino) y ciudad (BOGOTÁ, bogota, medellin…).
- **Fechas:** 3.052 en formato DD/MM/AAAA mezcladas con AAAA-MM-DD.

**Mapa de faltantes:** los huecos más visibles son motivo_retiro, promedio_acumulado y distancia_km, y coinciden con el conteo de `isnull().sum()`. Los '-' y 999 no aparecen porque todavía no son nulos reales.

### 2. Decisiones de limpieza y justificación
(Detalle completo con filas afectadas en `Data/processed/decisiones.csv`.)
- **'-' y 999 → nulo** con `to_numeric(errors="coerce")` y `replace`, para poder calcular promedios.
- **Categorías:** se comparan sin tildes ni mayúsculas contra la lista de valores válidos; así quedan 8 programas, 3 jornadas, 2 géneros y 7 ciudades.
- **Fechas:** formato ISO primero, luego DD/MM/AAAA, unidos con `fillna()` (3.052 en el segundo formato).
- **Duplicados:** 150 eliminadas; dos estudiantes distintos no pueden coincidir en las 23 columnas, incluido el id.
- **Nulos:** promedio nulo → se elimina la fila (298): una nota no se inventa. Ciudad y tipo de colegio → 'Sin dato' (96 y 145).
- **Imposibles:** promedio > 5 → se elimina (15). Edad imposible → mediana (12). Si no trabaja → 0 horas; horas > 100 → mediana de quienes trabajan (29 ajustes en total).

**Boxplots:** antes, los promedios de 45–78 y las edades de 12 y 150 aplastaban la caja; después el promedio queda entre 1,17 y 5,0 y la edad entre 17 y 29. Siguen apareciendo puntos sueltos (promedios bajos, edades 28–29): son valores posibles, por eso se conservan.

### 3. Respuestas a las cinco preguntas (con número de estudiantes)
1. **Programa con mayor deserción:** Ingeniería Industrial, **40,2 %** (n = 1.271), seguido de Ingeniería de Sistemas 38,2 % (n = 1.386) y Diseño Gráfico 35,6 % (n = 848). El más bajo es Psicología, 26,0 % (n = 1.137). Ningún programa tiene un tamaño tan pequeño como para dudar de su tasa.
2. **Becados vs no becados:** becados **21,9 %** (n = 2.683) frente a no becados **36,4 %** (n = 7.004): 14,5 puntos de diferencia.
3. **Jornada con menor promedio:** Nocturna, **3,46** (n = 2.666), frente a Fin de semana 3,70 (n = 949) y Diurna 3,72 (n = 6.072). Una hipótesis es el cansancio por el trabajo, pero el dato no la respalda: trabaja el 43,4 % de la nocturna y el 44,1 % de la diurna.
4. **Materias reprobadas (sin graduados):** desertores **3,07** (n = 3.136) frente a activos **0,62** (n = 5.692), unas 4,9 veces más.
5. **Deserción y asistencia:** sí aumenta al bajar la asistencia: Q1 **61,9 %** (n = 2.385), Q2 36,7 % (n = 2.386), Q3 20,7 % (n = 2.348), Q4 **9,4 %** (n = 2.371). Quedan fuera 197 estudiantes sin dato de asistencia.

### 4. Reflexión 1: asociación y causalidad
Los becados desertan menos (21,9 % vs 36,4 %), pero eso no prueba que la beca *cause* la permanencia. Muchas becas se dan por buen promedio o buena asistencia, y esas mismas características ya reducen la deserción (factor de confusión). También puede influir el apoyo familiar o económico de quien accede a la beca. Para separar causa de asociación habría que comparar becados y no becados con perfil académico y socioeconómico parecido, o usar una asignación aleatoria o un corte por puntaje.

### 5. Reflexión 2: variables que no deberían usarse para predecir
`motivo_retiro` solo se conoce cuando el estudiante ya desertó; usarla para predecir sería filtrar el resultado en las variables de entrada (fuga de información). Pasa lo mismo con `estado` y `desertor`, que son el resultado, y con cualquier dato registrado en o después del retiro. También hay que tener cuidado con `semestre` y `creditos_aprobados`: quien deserta pronto tiene valores bajos por haberse ido.

### 6. Reflexión 3: variables sensibles
Género, estrato y ciudad de procedencia reflejan desigualdades sociales. Aunque estén asociadas a la deserción, la institución no debería usarlas para decidir quién recibe apoyo: reproduciría la desigualdad, podría discriminar a grupos enteros y estigmatizar personas por su origen. Es más justo focalizar con señales académicas (asistencia, materias reprobadas, tutorías) y usar las variables sensibles solo para auditar brechas y comprobar que el apoyo llegue de forma equitativa.
