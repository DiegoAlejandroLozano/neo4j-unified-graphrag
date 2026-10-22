from dotenv               import dotenv_values
from pathlib              import Path
from extraccion_tripletas import ExtractorGrafo
from EntityResolver       import ResolverEntidades
from graph_store          import GestorNeo4j

def main():
    directorio_documentos = Path("00_documentos")
    archivos              = list(directorio_documentos.glob("*.md"))

    if not archivos:
        raise ValueError(f"No se encontraron archivos en el directorio: {directorio_documentos.resolve()}")

    config         = dotenv_values(dotenv_path=".env")
    openai_api_key = config.get("OPENAI_API_KEY")
    neo4j_uri      = config.get("NEO4J_URI")
    neo4j_user     = config.get("NEO4J_USER")
    neo4j_pass     = config.get("NEO4J_PASSWORD")
    
    if not openai_api_key:
        raise ValueError("No se encontró OPENAI_API_KEY en el archivo .env")

    # PASO 1: Extracción de Tripletas y Entidades Canónicas con LLM
    print("=== PASO 1: Extracción con GPT-4o-mini ===")
    extractor = ExtractorGrafo(api_key=openai_api_key)
    entidades_crudas_totales = []
    tripletas_crudas_totales = []

    for ruta_archivo in archivos:
        print(f"\nProcesando archivo: {ruta_archivo.name}")
        resultado = extractor.extraer(ruta_archivo=ruta_archivo)

        # Inyectar nombrede del archivo origen en cada entidad
        for ent in resultado["entidades"]:
            ent["documento_origen"] = ruta_archivo.name

        # Acumulando entidades y tripletas de cada documento
        entidades_crudas_totales.extend(resultado["entidades"])
        tripletas_crudas_totales.extend(resultado["tripletas"])    

    # Convertir las listas de propiedades [{'clave': 'k', 'valor': 'v'}] a diccionarios {'k': 'v'} para Neo4j
    for ent in entidades_crudas_totales:
        if isinstance(ent.get("propiedades"), list):
            ent["propiedades"] = {p["clave"]: p["valor"] for p in ent["propiedades"]}

    for trip in tripletas_crudas_totales:
        if isinstance(trip.get("propiedades"), list):
            trip["propiedades"] = {p["clave"]: p["valor"] for p in trip["propiedades"]}

    print(f"\n[PASO 1.1] Total de entidades crudas extraídas de {len(archivos)} archivo(s): {len(entidades_crudas_totales)}")
    print(f"[PASO 1.2] Total de tripletas crudas extraídas: {len(tripletas_crudas_totales)}")

    # PASO 2: Resolución de Entidades y Formas Canónicas
    print("\n=== PASO 2: Resolución de Entidades y Normalización ===")

    resolver = ResolverEntidades(api_key=openai_api_key)
    entidades_canonicas, tripletas_canonicas = resolver.resolver(
        entidades = entidades_crudas_totales, 
        tripletas = tripletas_crudas_totales
    )

    print(f"\n[RESULTADO PASO 2]")
    print(f" - Entidades canónicas consolidadas: {len(entidades_canonicas)}")
    print(f" - Tripletas re-mapeadas: {len(tripletas_canonicas)}")

    print("\nEjemplo de Entidades Canónicas creadas con ID único:")
    for ent in entidades_canonicas[:5]:
        print(f" - ID: {ent['id']} | Nombre: '{ent['nombre']}' | Tipo: :{ent['etiqueta_especifica']}")

    print("\nEjemplo de Tripletas validadas con IDs:")
    for t in tripletas_canonicas[:5]:
        print(f" - ({t['subject']} [{t['subject_id']}]) --[{t['relation']}]--> ({t['object']} [{t['object_id']}])")

    # PASO 3: Persistencia del Grafo en Neo4j
    print("\n=== PASO 3: Persistencia del grafo en Neo4j ===")
    neo4j_mgr = GestorNeo4j(
        uri       = neo4j_uri,
        user      = neo4j_user,
        pass_word = neo4j_pass
    )
    try:
        neo4j_mgr.guardar_grafo(entidades=entidades_canonicas, tripletas=tripletas_canonicas)
    finally:
        neo4j_mgr.close()

    print("\n Pipeline ejecutable completado con éxito")

if __name__ == "__main__":
    main()