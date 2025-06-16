import logging
from typing import List, Any, Optional
import numpy as np
import faiss
import json
from pathlib import Path
from llama_index.core.schema import BaseNode
from llama_index.core.vector_stores.types import VectorStoreQuery, VectorStoreQueryResult
from llama_index.vector_stores.faiss import FaissVectorStore
from llama_index.core.bridge.pydantic import PrivateAttr

logger = logging.getLogger(__name__)
MAPPINGS_FILENAME = "custom_faiss_store_mappings.json"

class CustomFaissVectorStore(FaissVectorStore):
    _faiss_id_to_node_id: dict[int, str] = PrivateAttr(default_factory=dict)
    _node_id_to_faiss_id: dict[str, int] = PrivateAttr(default_factory=dict)
    _next_faiss_id: int = PrivateAttr(default=0)
    _persist_path: Optional[Path] = PrivateAttr(default=None)

    def __init__(self, faiss_index: faiss.Index, persist_path: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(faiss_index=faiss_index, **kwargs)
        if persist_path:
            self._persist_path = Path(persist_path)
            self._load_mappings()

    def _get_or_create_faiss_id(self, node_id: str) -> int:
        if node_id in self._node_id_to_faiss_id:
            return self._node_id_to_faiss_id[node_id]
        faiss_int_id = self._next_faiss_id
        self._node_id_to_faiss_id[node_id] = faiss_int_id
        self._faiss_id_to_node_id[faiss_int_id] = node_id
        self._next_faiss_id += 1
        return faiss_int_id

    def add(self, nodes: List[BaseNode], **add_kwargs: Any) -> List[str]:
        if not nodes: return []
        embeddings_list, ids_list, added_node_ids = [], [], []
        for node in nodes:
            embedding = node.get_embedding()
            if embedding is None: continue
            embeddings_list.append(embedding)
            ids_list.append(self._get_or_create_faiss_id(node.node_id))
            added_node_ids.append(node.node_id)
        if not embeddings_list: return []
        self._faiss_index.add_with_ids(np.array(embeddings_list, dtype=np.float32), np.array(ids_list, dtype=np.int64))
        self._save_mappings()
        return added_node_ids

    def query(self, query: VectorStoreQuery, **kwargs: Any) -> VectorStoreQueryResult:
        if query.query_embedding is None: raise ValueError("Query embedding is required.")
        distances, faiss_ids = self._faiss_index.search(np.array([query.query_embedding], dtype=np.float32), query.similarity_top_k)
        valid_mask = faiss_ids[0] != -1
        valid_ids = faiss_ids[0][valid_mask]
        valid_distances = distances[0][valid_mask]
        result_ids, result_similarities = [], []
        for i, faiss_id in enumerate(valid_ids):
            if faiss_id in self._faiss_id_to_node_id:
                result_ids.append(self._faiss_id_to_node_id[faiss_id])
                result_similarities.append(valid_distances[i].item())
        return VectorStoreQueryResult(ids=result_ids, similarities=result_similarities)

    def delete(self, ref_doc_id: str, **delete_kwargs: Any) -> None:
        ids_to_remove = [faiss_id for node_id, faiss_id in self._node_id_to_faiss_id.items() if node_id.startswith(ref_doc_id)]
        if not ids_to_remove: return
        selector = faiss.IDSelectorBatch(len(ids_to_remove), faiss.swig_ptr(np.array(ids_to_remove, dtype=np.int64)))
        self._faiss_index.remove_ids(selector)
        for node_id, faiss_id in list(self._node_id_to_faiss_id.items()):
            if faiss_id in ids_to_remove:
                del self._node_id_to_faiss_id[node_id]
                if faiss_id in self._faiss_id_to_node_id:
                    del self._faiss_id_to_node_id[faiss_id]
        self._save_mappings()

    def _save_mappings(self):
        if not self._persist_path: return
        mappings_file = self._persist_path / MAPPINGS_FILENAME
        try:
            data = {"node_id_to_faiss_id": self._node_id_to_faiss_id, "faiss_id_to_node_id": {str(k): v for k, v in self._faiss_id_to_node_id.items()}, "next_faiss_id": self._next_faiss_id}
            with open(mappings_file, "w") as f: json.dump(data, f)
        except Exception as e: logger.error(f"Failed to save mappings: {e}")

    def _load_mappings(self):
        if not self._persist_path: return
        mappings_file = self._persist_path / MAPPINGS_FILENAME
        if mappings_file.exists():
            try:
                with open(mappings_file, "r") as f: data = json.load(f)
                self._node_id_to_faiss_id = data.get("node_id_to_faiss_id", {})
                self._faiss_id_to_node_id = {int(k): v for k, v in data.get("faiss_id_to_node_id", {}).items()}
                self._next_faiss_id = data.get("next_faiss_id", 0)
            except Exception as e:
                logger.error(f"Failed to load mappings: {e}", exc_info=True)
                self._clear_mappings()
        else: self._clear_mappings()

    def _clear_mappings(self):
        self._node_id_to_faiss_id, self._faiss_id_to_node_id, self._next_faiss_id = {}, {}, 0

    def clear(self):
        self._faiss_index.reset()
        self._clear_mappings()
        self._save_mappings()