# Unified GraphRAG System with Neo4j & OpenAI

Un pipeline de **GraphRAG (Retrieval-Augmented Generation basado en Grafos)** que realiza extracción estructurada de conocimiento desde documentos Markdown, resuelve la sinonimia e inconsistencia de entidades utilizando vector embeddings, y almacena tanto la estructura del grafo (nodos y relaciones) como los embeddings y texto completo de forma **unificada** en Neo4j.

## 🌟 Características Principales

* **Extracción Estructurada con LLM**: Procesa documentos Markdown divididos en fragmentos (*chunks*) utilizando `gpt-4o-mini` y esquemas estrictos de Pydantic para garantizar la calidad de entidades y relaciones.

* **Resolución de Entidades (Entity Resolution)**: Algoritmo dinámico basado en similitud coseno mediante `text-embedding-3-small` de OpenAI para agrupar sinónimos, fusionar nodos duplicados e integrar fragmentos de texto.

* **Manejo de Nodos Fantasma**: Detección y creación automática de nodos implícitos referenciados en las tripletas pero no declarados explícitamente en el texto original.

* **Almacenamiento Unificado en Neo4j**:

  * Contención híbrida: Nodos, relaciones, metadatos y vectores integrados en la misma base de datos.

  * Restricciones de unicidad deterministas generadas mediante hashing MD5.

  * Creación automática de **Índices Vectoriales Nativos** (1536 dimensiones, similitud coseno) e **Índices Full-Text** sobre el contenido.

## 📐 Arquitectura de la Solución

```
[ Documentos Markdown (.md) ]
             │
             ▼
[ ExtractorGrafo (LangChain + OpenAI GPT-4o-mini) ]
             │  ↳ Extrae Entidades, Tripletas y Metadatos con Pydantic
             ▼
[ ResolverEntidades (OpenAI Embeddings) ]
             │  ↳ Normalización de nodos implícitos
             │  ↳ Clustering por similitud coseno (Umbral configurable)
             │  ↳ Asignación de Hash MD5 determinista
             ▼
[ GestorNeo4j (Driver Oficial Neo4j) ]
             │  ↳ Creación de Índices Vectoriales y Full-Text
             │  ↳ Inserción/MERGE de Nodos Multietiqueta y Relaciones
             ▼
  ( Base de Datos Grafos/Vectorial Neo4j )
```

## 📁 Estructura del Proyecto

```
.
├── 00_documentos/           # Directorio para archivos fuente (.md)
├── EntityResolver.py       # Módulo para resolución y clustering de entidades
├── extraccion_tripletas.py # Módulo de extracción estructurada con LangChain/Pydantic
├── graph_store.py          # Gestor de conexión y queries Cypher en Neo4j
├── main.py                 # Pipeline de ejecución principal
├── environment.yml         # Archivo de configuración del entorno Conda
├── .env.example            # Plantilla de variables de entorno
└── README.md               # Documentación del proyecto
```

## ⚙️ Requisitos Previos

* **Conda / Mamba** (Anaconda, Miniconda o Micromamba).
* Una instancia activa de **Neo4j** (Neo4j Desktop, AuraDB o Docker).
* Una API Key válida de **OpenAI**.

## 🚀 Instalación y Configuración

1. **Clonar el repositorio:**

   ```bash
   git clone https://github.com/DiegoAlejandroLozano/neo4j-unified-graphrag.git
   cd neo4j-unified-graphrag
   ```

2. **Crear y activar el entorno Conda:**

   Crea el entorno desde el archivo `environment.yml`:

   ```bash
   conda env create -f environment.yml
   ```

   Una vez creado, activa el entorno (`conda-graphrag-curso`):

   ```bash
   conda activate conda-graphrag-curso
   ```

3. **Configurar variables de entorno:**

   Crea un archivo `.env` en la raíz del proyecto basándote en la plantilla `.env.example`:

   ```env
   OPENAI_API_KEY=sk-...
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=tu_contraseña
   ```

## 💻 Uso

1. Coloca tus archivos de conocimiento en formato Markdown (`.md`) dentro del directorio `00_documentos/`.

2. Ejecuta el pipeline principal con el entorno activado:

   ```bash
   python main.py
   ```

3. Visualiza la consola para seguir el progreso del pipeline de extracción, deduplicación y persistencia.

## 🔍 Consultas en Neo4j (Cypher)

Una vez ejecutado el pipeline, puedes abrir la consola de Neo4j Browser para inspeccionar el grafo:

### Ver todas las entidades y sus relaciones:

```cypher
MATCH (n:Entidad)-[r]->(m:Entidad)
RETURN n, r, m
LIMIT 50;
```

### Búsqueda por índice vectorial (Similitud Semántica):

```cypher
WITH [/* array con vector de 1536 dimensiones */] AS queryVector
CALL db.index.vector.queryNodes('entity_embeddings', 5, queryVector)
YIELD node, score
RETURN node.nombre, node.etiqueta_especifica, score;
```

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.