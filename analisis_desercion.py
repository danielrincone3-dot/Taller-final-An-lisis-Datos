from pathlib import Path

import unicodedata
import matplotlib
matplotlib.use("Agg")  # CORREGIDO: guarda los PNG sin abrir ventanas que bloquean el script
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)

RAW = Path(__file__).parent / "Data" / "raw" / "datos_estudiantes.csv"
PROCESSED = Path(__file__).parent / "Data" / "processed"
GRAFICOS = PROCESSED / "graficos"  # CORREGIDO: el enunciado pide Data/processed/graficos/

# Valores válidos de cada columna categórica (la forma correcta de escribirlos).
VALIDOS = {
    "programa": ["Administración de Empresas", "Contaduría Pública", "Derecho", "Psicología",
                 "Ingeniería de Sistemas", "Ingeniería Industrial", "Enfermería", "Diseño Gráfico"],
    "jornada": ["Diurna", "Nocturna", "Fin de semana"],
    "genero": ["Femenino", "Masculino"],
    "ciudad_procedencia": ["Bogotá", "Medellín", "Cali", "Bucaramanga", "Rionegro",
                           "Barranquilla", "Otra ciudad"],
}

DECISIONES = []


def _clave(texto):
    """Minúsculas, sin tildes y sin espacios sobrantes: sirve para comparar variantes."""
    if pd.isna(texto):
        return texto
    t = unicodedata.normalize("NFD", str(texto).strip().lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _unificar(serie, validos, extra=None):
    """Lleva cada variante a su forma válida (VALIDOS). Respeta los nulos reales."""
    mapa = {_clave(v): v for v in validos}
    mapa.update(extra or {})
    return serie.map(lambda x: x if pd.isna(x) else mapa.get(_clave(x), x))


def registrar(paso, columna, accion, filas, justificacion):
    """Guarda una decisión para la tabla de decisiones. Ya está escrita: solo úsala."""
    DECISIONES.append({
        "paso": paso, "columna": columna, "accion": accion,
        "filas_afectadas": int(filas), "justificacion": justificacion,
    })


def explorar(df):
    """Paso 1 del Word: primera mirada al dataset."""
    print("Dimensiones (filas, columnas):", df.shape)
    print("\nTipos y nulos por columna:")
    df.info()
    print("\nEstadísticas numéricas:")
    print(df.describe())
    # CORREGIDO: el original solo describía promedio_acumulado y no mostraba value_counts
    for col in ["programa", "jornada", "genero", "estado"]:
        print(f"\nvalue_counts de {col}:")
        print(df[col].value_counts(dropna=False))


def auditar(df):
    """Paso 2 del Word: buscar problemas sin corregirlos todavía."""
    print("\n--- NULOS REALES ---")
    print(df.isnull().sum()[lambda x: x > 0])

    print("\n--- FALTANTES DISFRAZADOS ---")
    for col in ["asistencia_pct", "horas_trabajo_semana"]:
        print(f"'-' en {col}: {(df[col].astype(str).str.strip() == '-').sum()}")
    print(f"999 en distancia_km: {(df['distancia_km'] == 999).sum()}")
    print(f"'%' en asistencia_pct: {df['asistencia_pct'].astype(str).str.contains('%').sum()}")

    print("\n--- VALORES IMPOSIBLES ---")
    prom = pd.to_numeric(df["promedio_acumulado"], errors="coerce")
    print(f"promedio fuera de 0-5: {((prom < 0) | (prom > 5)).sum()}")
    print(f"edad fuera de 15-80: {((df['edad'] < 15) | (df['edad'] > 80)).sum()}")
    horas = pd.to_numeric(df["horas_trabajo_semana"], errors="coerce")
    print(f"horas de trabajo > 100: {(horas > 100).sum()}")
    print(f"no trabaja pero con horas > 0: {((df['trabaja'] == 'no') & (horas > 0)).sum()}")

    print("\n--- DUPLICADOS ---")
    print(f"filas duplicadas: {df.duplicated().sum()}")

    print("\n--- FECHAS ---")
    print(f"fechas con formato DD/MM/AAAA: {df['fecha_matricula'].astype(str).str.contains('/').sum()}")


def convertir_numericos(df):
    """Paso 3 del Word: columnas que deberían ser numéricas, pero llegan como texto.

    Pistas: quitar el símbolo % con str.replace; reemplazar '-' por nulo;
    convertir con pd.to_numeric(..., errors="coerce"); reemplazar 999 por nulo en distancia_km.
    Registra cada conversión con registrar().
    """
    # TODO 3: convertir asistencia_pct, horas_trabajo_semana y distancia_km a número.

    if "asistencia_pct" in df.columns:
        df["asistencia_pct"] = df["asistencia_pct"].astype(str).str.replace("%", "", regex=False)
        filas_afectadas_asis = (df["asistencia_pct"] == "-").sum()
        df["asistencia_pct"] = pd.to_numeric(df["asistencia_pct"].replace("-", np.nan), errors="coerce")
        registrar("paso_3", "asistencia_pct", "convertir a numérico", int(filas_afectadas_asis), "Se removió el símbolo de porcentaje y se transformaron los guiones en nulos reales.")

    
    if "horas_trabajo_semana" in df.columns:
        df["horas_trabajo_semana"] = df["horas_trabajo_semana"].astype(str)
        filas_afectadas_horas = (df["horas_trabajo_semana"] == "-").sum()
        df["horas_trabajo_semana"] = pd.to_numeric(df["horas_trabajo_semana"].replace("-", np.nan), errors="coerce")
        registrar("paso_3", "horas_trabajo_semana", "convertir a numérico", int(filas_afectadas_horas), "Se cambiaron los faltantes disfrazados (-) por nulos reales de tipo numérico.")

    
    if "distancia_km" in df.columns:
        filas_afectadas_dist = (df["distancia_km"] == 999).sum()
        df["distancia_km"] = df["distancia_km"].replace(999, np.nan)
        registrar("paso_3", "distancia_km", "reemplazar 999 por nulo", int(filas_afectadas_dist), "Se identificó el valor disfrazado 999 y se reemplazó por un nulo real.")
    return df


def unificar_categorias(df):
    """Paso 4 del Word: errores tipográficos en columnas categóricas.

    Pistas: primero df[col].str.strip().str.lower(); después .replace(diccionario)
    con las variantes que encontraste con value_counts(). Los valores correctos están en VALIDOS.
    Pregunta: ¿qué variantes son el mismo valor? ¿Hay alguna que no debas unificar?
    """
    # TODO 4: unificar las escrituras de programa, jornada, genero y ciudad_procedencia.

    
    # CORREGIDO: el original solo mapeaba 6 de los 8 programas y dejaba 'ingeniería de sistemas',
    # 'psicología', 'cali', 'barranquilla' y 'otra ciudad' en minúscula (10 programas en vez de 8).
    # Ahora se compara sin tildes ni mayúsculas contra VALIDOS, y se cuenta cuántas filas cambian de verdad.
    for col in ["programa", "jornada", "genero", "ciudad_procedencia"]:
        if col not in df.columns:
            continue
        extra = {"m": "Masculino", "f": "Femenino"} if col == "genero" else None
        nuevo = _unificar(df[col], VALIDOS[col], extra)
        cambiadas = int(((nuevo != df[col]) & df[col].notna()).sum())
        df[col] = nuevo
        accion = "normalizar abreviaturas y variantes" if col == "genero" else "normalizar y unificar variantes"
        registrar("paso_4", col, accion, cambiadas,
                  f"Se unificaron mayúsculas, espacios y tildes de {col} contra la lista de valores válidos.")
    return df


def convertir_fechas(df):
    """Paso 5 del Word: fechas escritas en dos formatos.

    Pista: intenta el formato AAAA-MM-DD y luego DD/MM/AAAA, cada uno con errors="coerce",
    y junta los resultados con fillna(). Registra cuántas fechas tenían el segundo formato.
    """
    # TODO 5: convertir fecha_matricula a fecha con los dos formatos.

    if "fecha_matricula" in df.columns:
        fechas_iso = pd.to_datetime(df["fecha_matricula"], format="%Y-%m-%d", errors="coerce")
      
        fechas_dmy = pd.to_datetime(df["fecha_matricula"], format="%d/%m/%Y", errors="coerce")
      
        # CORREGIDO: la resta anterior daba 0. Se cuentan las fechas que NO son ISO pero sí DD/MM/AAAA.
        conteo_segundo_formato = (fechas_iso.isna() & fechas_dmy.notna()).sum()
            
        df["fecha_matricula"] = fechas_iso.fillna(fechas_dmy)
        
        registrar(
            "paso_5", "fecha_matricula", "unificar formatos de fecha", int(conteo_segundo_formato), "Se unificaron los formatos mixtos (AAAA-MM-DD y DD/MM/AAAA) convirtiéndolos a un tipo datetime homogéneo.")

    return df


def eliminar_duplicados(df):
    """Paso 6 del Word: filas repetidas.

    Pregunta: ¿podrían existir dos estudiantes distintos con todos los datos iguales?
    Pista: duplicated() y drop_duplicates(), con reset_index(drop=True).
    """
    # TODO 6: eliminar duplicados, registrar la decisión y devolver el dataframe.
    
    filas_antes = len(df)
    
    df = df.drop_duplicates().reset_index(drop=True)
    
    filas_eliminadas = filas_antes - len(df)
    
    registrar("paso_6", "todas", "eliminar filas duplicadas", int(filas_eliminadas), "Se eliminaron las filas completamente idénticas para evitar sesgos y duplicidad en el análisis, reiniciando el índice.")

    return df


def tratar_faltantes(df):
    """Paso 7 del Word: decidir qué hacer con los nulos reales.

    Preguntas:
    - ¿Puedes inventar una nota? ¿Qué pasa si imputas el promedio?
    - Para ciudad o tipo de colegio, ¿conviene eliminar la fila o marcar el dato como 'Sin dato'?
    - motivo_retiro tiene muchos nulos. ¿Son errores? (Pista: ¿para quiénes aplica esa columna?)
    """
    # TODO 7: tratar los nulos de promedio_acumulado, ciudad_procedencia y tipo_colegio.

#NO INVENTAR NOTAS
    if "promedio_acumulado" in df.columns:
        nulos_antes = df["promedio_acumulado"].isnull().sum()
        df = df.dropna(subset=["promedio_acumulado"]).reset_index(drop=True)
        registrar("paso_7", "promedio_acumulado", "eliminar filas con nulos", int(nulos_antes), "Una nota académica no se puede inventar ni imputar arbitrariamente, por lo que se eliminaron las filas con promedio nulo.")

    if "ciudad_procedencia" in df.columns:
        nulos_ciudad = df["ciudad_procedencia"].isnull().sum()
        df["ciudad_procedencia"] = df["ciudad_procedencia"].fillna("Sin dato")
        registrar("paso_7", "ciudad_procedencia", "reemplazar nulos por etiqueta", int(nulos_ciudad), "Se rellenaron los nulos con 'Sin dato' para conservar la información demográfica sin descartar registros completos.")

    if "tipo_colegio" in df.columns:
        nulos_colegio = df["tipo_colegio"].isnull().sum()
        df["tipo_colegio"] = df["tipo_colegio"].fillna("Sin dato")
        registrar("paso_7", "tipo_colegio", "reemplazar nulos por etiqueta", int(nulos_colegio), "Se rellenaron los nulos con 'Sin dato' para mantener el tamaño de la muestra y evitar la pérdida de filas innecesarias." )

    return df


def tratar_imposibles(df):
    """Paso 8 del Word: valores que no pueden existir.

    Preguntas:
    - La escala del promedio es de 0 a 5. ¿Qué harías con un 45?
    - Una edad de 150 años es un error. ¿Qué valor pondrías en su lugar?
    - Si el estudiante no trabaja, ¿cuántas horas de trabajo tiene? ¿Cómo lo aplicas en código?
    """
    # TODO 8: tratar edad, promedio_acumulado y horas_trabajo_semana, con sus justificaciones.

    if "promedio_acumulado" in df.columns:
        imposibles_prom = (df["promedio_acumulado"] > 5).sum()
        df.loc[df["promedio_acumulado"] > 5, "promedio_acumulado"] = np.nan
        df = df.dropna(subset=["promedio_acumulado"]).reset_index(drop=True)
        registrar("paso_8", "promedio_acumulado", "convertir valores imposibles a nulo y eliminar", int(imposibles_prom), "Se detectaron promedios mayores a 5 debido a errores de escala; se anularon y eliminaron por tratarse de notas académicas que no se pueden inventar." )

    if "edad" in df.columns:
        imposibles_edad = ((df["edad"] < 15) | (df["edad"] > 80)).sum()
        mediana_edad = df.loc[(df["edad"] >= 15) & (df["edad"] <= 80), "edad"].median()
        df.loc[(df["edad"] < 15) | (df["edad"] > 80), "edad"] = mediana_edad
        registrar("paso_8", "edad", "imputar valores imposibles de edad por la mediana", int(imposibles_edad), "Se identificaron edades ilógicas (como 150 años) y se reemplazaron por la mediana poblacional para conservar el registro del estudiante.")

    if "trabaja" in df.columns and "horas_trabajo_semana" in df.columns:
        # CORREGIDO: NaN != 0 es True, así que se inflaba el conteo (2732). Solo cuentan horas con dato.
        afectados_cero = ((df["trabaja"] == "no") & df["horas_trabajo_semana"].notna() & (df["horas_trabajo_semana"] != 0)).sum()
        df.loc[df["trabaja"] == "no", "horas_trabajo_semana"] = 0
        
        imposibles_horas = (df["horas_trabajo_semana"] > 100).sum()
        mediana_horas = df.loc[(df["trabaja"] == "sí") & (df["horas_trabajo_semana"] <= 100) & (df["horas_trabajo_semana"] > 0), "horas_trabajo_semana"].median()
        df.loc[df["horas_trabajo_semana"] > 100, "horas_trabajo_semana"] = mediana_horas
        
        registrar("paso_8", "horas_trabajo_semana", "ajustar horas de trabajo por reglas lógicas", int(afectados_cero + imposibles_horas), "Se establecieron en 0 las horas de los estudiantes que no trabajan y se corrigieron valores superiores a 100 horas usando la mediana del grupo trabajador.")

    return df


def crear_variables(df):
    """Paso 9 del Word: variables nuevas para el análisis.

    Crea:
    - desertor: True si estado es 'desertor', False si no.
    - cuartil_asistencia: divide asistencia_pct en cuatro grupos iguales con pd.qcut.
    Pregunta: ¿por qué conviene usar cuartiles y no valores exactos de asistencia?
    """
    # TODO 9: crear las columnas desertor y cuartil_asistencia.

    if "estado" in df.columns:
        df["desertor"] = df["estado"].eq("desertor")
        registrar("paso_9", "desertor", "crear variable booleana", len(df), "Se creó la columna booleana 'desertor' (True/False) para calcular fácilmente proporciones y tasas de abandono mediante el promedio.")

    if "asistencia_pct" in df.columns:
        df["cuartil_asistencia"] = pd.qcut(
            df["asistencia_pct"], 4, labels=["Q1", "Q2", "Q3", "Q4"])
        registrar("paso_9", "cuartil_asistencia", "crear cuartiles con pd.qcut", len(df), "Se segmentó la asistencia_pct en cuatro grupos de tamaño equivalente (Q1 a Q4) para evaluar la tendencia de deserción por niveles.")

    return df


def grafico_faltantes(df):
    """Gráfico 1: mapa de faltantes del dataset original.

    Pista: sns.heatmap(df.isnull(), cbar=False)
    """
    # TODO 10: dibujar, guardar en GRAFICOS / "mapa_faltantes.png" y mostrar.

# 1. Asegurar que la carpeta GRAFICOS exista
    GRAFICOS.mkdir(parents=True, exist_ok=True)
    
    # 2. Configurar el tamaño de la figura
    plt.figure(figsize=(10, 6))
    
    # 3. Crear el mapa de calor con seaborn usando .isnull()
    sns.heatmap(df.isnull(), cbar=False, cmap="viridis")
    
    # 4. Personalizar títulos y etiquetas
    plt.title("Mapa de Datos Faltantes (Null Heatmap)", fontsize=14)
    plt.xlabel("Columnas del Dataset", fontsize=12)
    plt.ylabel("Registros / Filas", fontsize=12)
    plt.xticks(rotation=45, ha="right")
    
    # 5. Ajustar diseño, guardar la imagen y mostrarla
    plt.tight_layout()
    plt.savefig(GRAFICOS / "mapa_faltantes.png", dpi=150)
 
    plt.close()

    pass


def grafico_distribuciones(antes, despues):
    """Gráfico 2: boxplots de promedio_acumulado y edad, antes y después de limpiar.

    Pregunta: ¿qué cambió en cada distribución? ¿Por qué?
    """
    # TODO 11: dibujar los cuatro boxplots, guardar en GRAFICOS / "distribuciones_antes_despues.png" y mostrar.

    GRAFICOS.mkdir(parents=True, exist_ok=True)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Asegurar que las columnas sean numéricas para evitar errores en seaborn
    prom_antes = pd.to_numeric(antes["promedio_acumulado"], errors="coerce")
    prom_despues = pd.to_numeric(despues["promedio_acumulado"], errors="coerce")
    edad_antes = pd.to_numeric(antes["edad"], errors="coerce")
    edad_despues = pd.to_numeric(despues["edad"], errors="coerce")
    
    # 3. Gráfico 1: Promedio acumulado (Antes)
    sns.boxplot(y=prom_antes, ax=axes[0, 0], color="salmon")
    axes[0, 0].set_title("Promedio Acumulado - ANTES", fontsize=12)
    axes[0, 0].set_ylabel("Valor")
    
    # 4. Gráfico 2: Promedio acumulado (Después)
    sns.boxplot(y=prom_despues, ax=axes[0, 1], color="skyblue")
    axes[0, 1].set_title("Promedio Acumulado - DESPUÉS", fontsize=12)
    axes[0, 1].set_ylabel("Valor")
    
    # 5. Gráfico 3: Edad (Antes)
    sns.boxplot(y=edad_antes, ax=axes[1, 0], color="salmon")
    axes[1, 0].set_title("Edad - ANTES", fontsize=12)
    axes[1, 0].set_ylabel("Años")
    
    # 6. Gráfico 4: Edad (Después)
    sns.boxplot(y=edad_despues, ax=axes[1, 1], color="skyblue")
    axes[1, 1].set_title("Edad - DESPUÉS", fontsize=12)
    axes[1, 1].set_ylabel("Años")
    
    plt.tight_layout()
    plt.savefig(GRAFICOS / "distribuciones_antes_despues.png", dpi=150)
    
    plt.close()

    pass


def _barras_tasa(tasa, n, titulo, xlabel, archivo, rotar=0):
    """Dibuja barras de tasa (%) con el n de cada grupo."""
    GRAFICOS.mkdir(parents=True, exist_ok=True)
    datos = pd.DataFrame({"grupo": tasa.index.astype(str), "tasa": tasa.values * 100, "n": n.values})
    plt.figure(figsize=(12, 6))
    ax = sns.barplot(data=datos, x="grupo", y="tasa", hue="grupo", palette="crest", legend=False)
    plt.title(titulo, fontsize=14, fontweight="bold")
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel("Tasa de deserción (%)", fontsize=12)
    plt.xticks(rotation=rotar, ha="right" if rotar else "center")
    for p, (_, fila) in zip(ax.patches, datos.iterrows()):
        ax.annotate(f"{fila['tasa']:.1f}%\n(n={int(fila['n'])})",
                    (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha="center", va="bottom", fontsize=9, xytext=(0, 3), textcoords="offset points")
    plt.ylim(0, datos["tasa"].max() * 1.18)
    plt.tight_layout()
    plt.savefig(GRAFICOS / archivo, dpi=150)
    plt.close()


def grafico_tasa_programa(df):
    """Gráfico 3: tasa de deserción por programa."""
    # CORREGIDO: esta función estaba vacía (solo 'pass'); el gráfico de programa lo dibujaba la de asistencia.
    g = df.groupby("programa")["desertor"].agg(["mean", "count"]).sort_values("mean", ascending=False)
    _barras_tasa(g["mean"], g["count"], "Tasa de deserción por programa académico (%)",
                 "Programa académico", "tasa_desercion_por_programa.png", rotar=30)


def grafico_tasa_asistencia(df):
    """Gráfico 4: tasa de deserción por cuartil de asistencia."""
    # CORREGIDO: el original dibujaba el gráfico de PROGRAMA aquí; el de asistencia nunca se generaba.
    g = df.groupby("cuartil_asistencia", observed=True)["desertor"].agg(["mean", "count"])
    _barras_tasa(g["mean"], g["count"], "Tasa de deserción por cuartil de asistencia (%)",
                 "Cuartil de asistencia (Q1 = menor asistencia)", "tasa_desercion_por_asistencia.png")


def responder_preguntas(df):
    """Paso 10 del Word: las cinco preguntas de la institución.

    Cada pregunta debe imprimir el resultado con el número de estudiantes por grupo.
    Pregunta 1: ¿Qué programa presenta la tasa de deserción más alta?
    Pregunta 2: ¿Hay diferencia en la deserción entre becados y no becados?
    Pregunta 3: ¿Qué jornada tiene el menor promedio acumulado?
    Pregunta 4: ¿Cuántas materias reprobadas tienen en promedio los desertores frente a los activos?
                (Excluye a los graduados.)
    Pregunta 5: ¿La deserción aumenta conforme baja la asistencia?
                (Usa cuartil_asistencia.)
    """
    # TODO 14: responder las cinco preguntas con groupby() y agg().


    print("\n--- PREGUNTA 1: Tasa de deserción por Programa ---")
    p1 = df.groupby("programa").agg(
        tasa_desercion=("desertor", "mean"),
        total_estudiantes=("desertor", "count")
    ).reset_index()
    p1["tasa_desercion"] = p1["tasa_desercion"] * 100
    p1 = p1.sort_values(by="tasa_desercion", ascending=False)
    print(p1.to_string(index=False))

    print("\n--- PREGUNTA 2: Deserción según Beca ---")
    p2 = df.groupby("beca").agg(
        tasa_desercion=("desertor", "mean"),
        total_estudiantes=("desertor", "count")
    ).reset_index()
    p2["tasa_desercion"] = p2["tasa_desercion"] * 100
    print(p2.to_string(index=False))

   
    print("\n--- PREGUNTA 3: Promedio acumulado por Jornada ---")
    p3 = df.groupby("jornada").agg(
        promedio_acumulado=("promedio_acumulado", "mean"),
        total_estudiantes=("promedio_acumulado", "count")
    ).reset_index()
    p3 = p3.sort_values(by="promedio_acumulado", ascending=True)
    print(p3.to_string(index=False))


    print("\n--- PREGUNTA 4: Materias reprobadas (Desertores vs Activos) ---")
    df_filtrado = df[df["estado"].isin(["desertor", "activo"])]
    p4 = df_filtrado.groupby("estado").agg(
        promedio_materias_reprobadas=("materias_reprobadas", "mean"),
        total_estudiantes=("materias_reprobadas", "count")
    ).reset_index()
    print(p4.to_string(index=False))


    print("\n--- PREGUNTA 5: Deserción según Cuartil de Asistencia ---")
    if "cuartil_asistencia" in df.columns:
        p5 = df.groupby("cuartil_asistencia", observed=True).agg(
            tasa_desercion=("desertor", "mean"),
            total_estudiantes=("desertor", "count")
        ).reset_index()
        p5["tasa_desercion"] = p5["tasa_desercion"] * 100
        print(p5.to_string(index=False))
    else:
        print("La columna 'cuartil_asistencia' no está creada en el DataFrame.")
    

    pass


def guardar(df):
    """Paso 11 del Word: guardar el dataset limpio y la tabla de decisiones. Ya está escrito."""
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED / "dataset_limpio.csv", index=False)
    pd.DataFrame(DECISIONES).to_csv(PROCESSED / "decisiones.csv", index=False)
    print(f"\nDataset limpio guardado: {df.shape[0]} filas, {df.shape[1]} columnas.")


def main():
    original = pd.read_csv(RAW)
    df = original.copy()

    explorar(df)
    auditar(df)
    grafico_faltantes(df)

    df = convertir_numericos(df)
    df = unificar_categorias(df)
    df = convertir_fechas(df)
    df = eliminar_duplicados(df)
    df = tratar_faltantes(df)
    df = tratar_imposibles(df)
    df = crear_variables(df)

    grafico_distribuciones(original, df)
    grafico_tasa_programa(df)
    grafico_tasa_asistencia(df)

    responder_preguntas(df)
    print("\nTabla de decisiones:")
    print(pd.DataFrame(DECISIONES))
    guardar(df)


if __name__ == "__main__":
    main()
