from typing import List, Dict
from neo4j  import GraphDatabase

class GestorNeo4j:
    """
    Maneja la inserción de nodos, relaciones y persistencia del índice 
    vectorial unificado dentro de Neo4j.
    """
    def __init__(self, uri: str, user: str, pass_word: str):
        self.driver = GraphDatabase.driver(uri=uri, auth=(user, pass_word))
        self._crear_restriccion_unicidad()
        self._crear_indice_vectorial() 
        self._crear_indice_fulltext()

    def _crear_restriccion_unicidad(self):
        """Asegura la restricción sobre (n:Entidad) usando el campo id."""
        query_contraint = """
        CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
        FOR (n:Entidad) REQUIRE n.id IS UNIQUE
        """
        with self.driver.session() as session:
            session.run(query=query_contraint)

    def _crear_indice_fulltext(self):
        """Crea el índice de texto completo nativo de Neo4j sobre el nombre y el texto de las entidades."""
        query_index = """
        CREATE FULLTEXT INDEX entity_text_index IF NOT EXISTS
        FOR (n:Entidad)
        ON EACH [n.nombre, n.text]
        """
        with self.driver.session() as session:
            session.run(query=query_index)

    def _crear_indice_vectorial(self):
        """Crea el índice vectorial nativo sobre la propiedad 'vector' de las entidades."""
        query_index = """
        CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS
        FOR (n:Entidad) ON (n.vector)
        OPTIONS {
            indexConfig : {
                `vector.dimensions`         : 1536,
                `vector.similarity_function`: 'cosine' 
            }
        }
        """
        with self.driver.session() as session:
            session.run(query=query_index)

    def close(self):
        self.driver.close()

    def guardar_grafo(self, entidades: List[Dict], tripletas: List[Dict]):
        """Crea los nodos multietiqueta y las relaciones asociadas"""
        with self.driver.session() as session:
            # 1. Inserción de nodos con multietiqueta
            for ent in entidades:

                propiedades_limpias = {
                    k: v for k, v in ent.get("propiedades", {}).items()
                    if k not in ["id", "nombre", "vector", "text"] and v is not None
                }

                etiqueta_esp = ent.get("etiqueta_especifica", "Concepto").replace(" ", "")
                query_nodo   = f"""
                MERGE (n:Entidad {{id: $id}})
                SET n:`{etiqueta_esp}`,
                    n += $propiedades,
                    n.nombre = $nombre,
                    n.vector = $vector,
                    n.text   = $text
                """
                session.run(
                    query       = query_nodo,
                    id          = ent["id"],
                    nombre      = ent["nombre"],
                    vector      = ent.get("vector"),
                    text        = ent.get("text", ""),
                    propiedades = propiedades_limpias
                )

            # 2. Inserción de relaciones
            for trip in tripletas:
                rel_type                = trip["relation"].replace(" ", "_").upper()
                propiedades_rel_limpias = {
                    k:v for k, v in trip.get("propiedades", {}).items()
                    if v is not None
                }
                query_rel = f"""
                MATCH (s:Entidad {{id: $sub_id}})
                MATCH (o:Entidad {{id: $obj_id}})
                MERGE (s)-[r:`{rel_type}`]->(o)
                SET r += $props
                """
                session.run(
                    query  = query_rel,
                    sub_id = trip["subject_id"],
                    obj_id = trip["object_id"],
                    props  = propiedades_rel_limpias
                )

        print(f"[Neo4j] {len(entidades)} nodos y {len(tripletas)} relaciones guardadas/actualizadas")
