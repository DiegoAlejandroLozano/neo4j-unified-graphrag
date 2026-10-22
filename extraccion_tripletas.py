from typing   import List, Dict, Any
from pydantic import BaseModel, Field
from dotenv   import dotenv_values
from pathlib  import Path

from langchain_openai         import ChatOpenAI
from langchain_core.prompts   import ChatPromptTemplate
from langchain_text_splitters import MarkdownTextSplitter

# Esquema para propiedades y etiquetas enriquecidas de la Entidad
class PropiedadClaveValor(BaseModel):
    clave: str = Field(description="Nombre del atributo o relación")
    valor: str = Field(description="Valor correspondiente al atributo")

class EntidadDetalle(BaseModel):
    nombre             : str = Field(description="Nombre único y canónico de la entidad (ej. 'Neo4j', 'RAG')")
    etiqueta_especifica: str = Field(description="Categoría o tipo de la entidad en PascalCase (ej. 'Tecnologia', 'Empresa', 'Algoritmo', 'Concepto')")
    propiedades        : List[PropiedadClaveValor] = Field(
        default_factory = list,
        description     = "Lista de pares clave-valor descriptivos"
    )

# Definimos el Esquema Pydantic para forzar salida estructurada
class TripletaEsquema(BaseModel):
    subject     : str = Field(description="Nombre exacto del sujeto (debe coincidir con alguna entidad)")
    relation    : str = Field(description="Relación en MAYÚSCULAS_CON_UNDERSCORE (ej. 'MEJORA_A', 'DESARROLLADO_POR')")
    object      : str = Field(description="Nombre exacto del objeto (debe coincidir con alguna entidad)")
    propiedades : List[PropiedadClaveValor] = Field(
        default_factory = dict,
        description     = "Atributos o contexto de la relación (ej. {'confianza': 0.9, 'contexto': 'búsqueda'})"
    )

class ExtraccionGrafoEsquema(BaseModel):
    entidades : List[EntidadDetalle]  = Field(description="Lista de todas las entidades únicas con sus tipos y propiedades")
    tripletas : List[TripletaEsquema] = Field(description="Lista de relaciones estructuradas entre las entidades")

class ExtractorGrafo():
    """Clase encargada de la extracción estructurada de Grafos de Conocimiento usando LLMs."""

    def __init__(self, api_key:str, model_name:str="gpt-4o-mini"):
        self.api_key    = api_key
        self.model_name = model_name

        # Inicializar el LLM con salida estructurada de Pydantic
        llm = ChatOpenAI(
            model       = self.model_name,
            temperature = 0,
            api_key     = self.api_key
        )
        self.structured_llm = llm.with_structured_output(schema=ExtraccionGrafoEsquema)
        self.system_prompt  = (
            "Eres un experto en extracción de grafos de conocimiento enriquecidos.\n"
            "Analiza el texto y extrae las entidades clave y sus relaciones principales.\n\n"
            "REGLAS DE RESTRICCIÓN OBLIGATORIAS:\n"
            "- Extrae UN MÁXIMO de 10 entidades y 10 tripletas por cada fragmento.\n"
            "- Enfócate únicamente en los conceptos, tecnologías o entidades MÁS IMPORTANTES.\n"
            "- En 'propiedades', añade únicamente atributos altamente relevantes (máximo 3 por entidad/relación o lista vacía).\n"
            "- Los nombres de entidades en las tripletas (sujeto y objeto) deben coincidir exactamente con los nombres de la lista de entidades."
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "Extrae las tripletas de conocimiento del siguiente texto:\n\n{texto}")
        ])

        self.chain = self.prompt | self.structured_llm

    def extraer(self, ruta_archivo:Path):
        """Lee un archivo y retorna un diccionario con entidades_canonicas y tripletas."""
        with open(str(ruta_archivo), "r", encoding="utf-8") as f:
            texto_documento = f.read()        

        print(f"Dividiendo archivo '{ruta_archivo}' en chunks...")

        # 1. División del documento en chunks manejables
        splitter = MarkdownTextSplitter(chunk_size=2000, chunk_overlap=500)
        chunks   = splitter.split_text(text=texto_documento)
        print(f"[Extractor] Documento dividido en {len(chunks)} fragmentos.")

        entidades_totales = []
        tripletas_totales = []

        # 2. Iteracción sobre cada chunk
        for idx, chunk in enumerate(chunks, 1):
            print(f" -> Procesando chunk {idx}/{len(chunks)}...")
            res : ExtraccionGrafoEsquema = self.chain.invoke({"texto" : chunk})
            datos_chunk = res.model_dump()

            # Inyectamos el texto del chunk exacto en cada entidad
            for entidad in datos_chunk["entidades"]:
                entidad["text"] = chunk
            entidades_totales.extend(datos_chunk["entidades"])
            tripletas_totales.extend(datos_chunk["tripletas"])

        return  {
            "entidades" : entidades_totales,
            "tripletas" : tripletas_totales
        }

