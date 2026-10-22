import numpy as np
from typing           import List, Dict, Tuple
from langchain_openai import OpenAIEmbeddings

import hashlib

class ResolverEntidades:
    """
    Se encarga de resolver la sinonimia de entidades (Entity Resolution) mediante embeddings
    y de garantizar que todos los nodos referenciados en tripletas existan con un ID único.
    """

    def __init__(self, api_key:str, umbral_similitud:float = 0.88):
        self.embeddings = OpenAIEmbeddings(
            api_key = api_key,
            model   = "text-embedding-3-small"
        )
        self.umbral = umbral_similitud

    def _similitud_coseno(self, vec_a:np.ndarray, vec_b:np.ndarray) -> float:
        norma_a = np.linalg.norm(vec_a)
        norma_b = np.linalg.norm(vec_b)
        if norma_a == 0 or norma_b == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norma_a * norma_b))

    def resolver(
        self, 
        entidades: List[Dict],
        tripletas: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:

        # 1. COMPLETAR NODOS FANTASMA:
        # Extraer nombres ya declarados en la lista de entidades
        nombres_existentes = {e["nombre"] for e in entidades}

        # Iterar sobre tripletas para rescatar nodos no declarados en la lista original
        for trip in tripletas:
            for rol in ["subject", "object"]:
                nombre_nodo = trip[rol]
                if nombre_nodo not in nombres_existentes:
                    entidades.append({
                        "nombre"              : nombre_nodo,
                        "etiqueta_especifica" : "Concepto",
                        "propiedades"         : {}
                    })
                    nombres_existentes.add(nombre_nodo)

        # 2. Generación de embeddings
        nombres  = [e["nombre"] for e in entidades]
        vectores = self.embeddings.embed_documents(texts=nombres)

        mapa_canonico              : Dict[str, str]  = {}
        entidades_canonicas_unicas : Dict[str, Dict] = {}

        # 3. CLUSTERING Y NORMALIZACIÓN DE ENTIDADES
        for i, nombre_orig in enumerate(nombres):
            vec_i      = np.array(vectores[i])
            encontrado = False

            # comparar contra las entidades canónicas identificadas hasta ahora
            for nombre_can, ent_can in entidades_canonicas_unicas.items():
                vec_can   = np.array(ent_can["vector"])
                similitud = self._similitud_coseno(vec_a=vec_i, vec_b=vec_can)
                if similitud >= self.umbral:
                    mapa_canonico[nombre_orig] = nombre_can
                    encontrado                 = True

                    # si la entidad ya existe: Acumular/anexar el chunk de texto si proviene de otro fragmento
                    texto_nuevo  = entidades[i].get("text", "")
                    texto_actual = ent_can.get("text", "")
                    if texto_nuevo and texto_nuevo not in texto_actual:
                        ent_can["text"] = f"{texto_actual}\n\n{texto_nuevo}".strip()
                    break

            if not encontrado:
                # Se registra una nueva entidad canónica
                mapa_canonico[nombre_orig]              = nombre_orig
                ent_copia                               = dict(entidades[i])
                ent_copia["vector"]                     = vectores[i]
                ent_copia["text"]                       = entidades[i].get("text", "")
                entidades_canonicas_unicas[nombre_orig] = ent_copia

        # 4. Asignación de ID único y preparación de entidades
        entidades_procesadas = []
        for nombre_can, ent in entidades_canonicas_unicas.items():
            # Generar ID determinista basado en el nombre canónico
            id_hash              = int(hashlib.md5(nombre_can.encode("utf-8")).hexdigest(), 16) % 1000000
            ent["id"]            = f"node_{id_hash}"
            ent["etiqueta_base"] = "Entidad"            
            entidades_procesadas.append(ent)

        # 5. Re-mapeo de tripletas con los nodos canónicos e IDs
        mapa_ids             = {e["nombre"] : e["id"] for e in entidades_procesadas}
        tripletas_procesadas = []

        for trip in tripletas:
            subj_can = mapa_canonico.get(trip["subject"], trip["subject"])
            obj_can  = mapa_canonico.get(trip["object"], trip["object"])

            if subj_can in mapa_ids and obj_can in mapa_ids:
                trip_copia = dict(trip)
                trip_copia["subject"]    = subj_can
                trip_copia["subject_id"] = mapa_ids[subj_can]
                trip_copia["object"]     = obj_can
                trip_copia["object_id"]  = mapa_ids[obj_can]
                tripletas_procesadas.append(trip_copia)

        return entidades_procesadas, tripletas_procesadas
