# app/features/semantic_retrieval/llama_ops/custom_faiss_vstore.py
import logging
from typing import List, Any, cast, Optional
import numpy as np
import faiss
import json
from pathlib import Path

from llama_index.core.schema import BaseNode
from llama_index.core.vector_stores.types import (
    VectorStoreQuery,
    VectorStoreQueryResult,
)
from llama_index.vector_stores.faiss import FaissVectorStore  # type: ignore
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
        if node_id not in self._node_id_to_faiss_id:
            faiss_int_id = self._next_faiss_id
            self._node_id_to_faiss_id[node_id] = faiss_int_id
            self._faiss_id_to_node_id[faiss_int_id] = node_id
            self._next_faiss_id += 1
            logger.debug(
                f"Mapped LlamaNodeID '{node_id}' to FaissIntID {faiss_int_id} (new). Next FaissID: {self._next_faiss_id}")
            return faiss_int_id
        else:
            faiss_int_id = self._node_id_to_faiss_id[node_id]
            logger.debug(f"Found existing FaissIntID {faiss_int_id} for LlamaNodeID '{node_id}'.")
            return faiss_int_id

    def add(self, nodes: List[BaseNode], **add_kwargs: Any) -> List[str]:
        if not nodes:
            return []

        embeddings_to_add_np_list = []
        faiss_ids_to_add_list = []
        added_llama_node_ids: List[str] = []

        for node in nodes:
            current_embedding = node.embedding
            if current_embedding is None:
                if self.embed_model:  # Access embed_model from FaissVectorStore base
                    logger.debug(f"Node {node.node_id} has no embedding, attempting to generate.")
                    current_embedding = self.embed_model.get_text_embedding(
                        node.get_content(metadata_mode="all"))  # type: ignore
                else:
                    logger.warning(
                        f"Node {node.node_id} has no embedding and no embed_model in vector store. Skipping.")
                    continue

            if current_embedding is None:  # Still None after attempt
                logger.warning(f"Failed to get/generate embedding for node {node.node_id}. Skipping.")
                continue

            embeddings_to_add_np_list.append(current_embedding)
            faiss_int_id = self._get_or_create_faiss_id(node.node_id)
            faiss_ids_to_add_list.append(faiss_int_id)
            added_llama_node_ids.append(node.node_id)

        if not embeddings_to_add_np_list:
            logger.info("No valid embeddings to add for the provided nodes.")
            return []

        embeddings_np = np.array(embeddings_to_add_np_list, dtype=np.float32)

        if isinstance(self._faiss_index, (faiss.IndexIDMap, faiss.IndexIDMap2)):
            ids_np = np.array(faiss_ids_to_add_list, dtype=np.int64)
            logger.info(
                f"CustomFaissVS: Adding {embeddings_np.shape[0]} embeddings with {ids_np.shape[0]} FAISS INT IDs to IndexIDMap2.")
            self._faiss_index.add_with_ids(embeddings_np, ids_np)
        else:
            logger.warning(
                "CustomFaissVS: Adding to non-IDMap FAISS index. This is unexpected and might lead to issues with ID-based deletion.")
            self._faiss_index.add(embeddings_np)

        self._save_mappings()
        return added_llama_node_ids

    def query(self, query: VectorStoreQuery, **kwargs: Any) -> VectorStoreQueryResult:
        if query.query_embedding is None:
            if self.embed_model and query.query_str:
                logger.debug(f"Query string provided ('{query.query_str[:30]}...'), generating query embedding.")
                query.query_embedding = self.embed_model.get_text_embedding(query.query_str)  # type: ignore
            else:
                raise ValueError("Query embedding (or query_str with an embed_model) is required for FAISS query.")

        if query.query_embedding is None:  # Check again after potential generation
            raise ValueError("Failed to obtain query embedding for FAISS query.")

        query_embedding_np = np.array([query.query_embedding], dtype=np.float32)

        logger.debug(
            f"CustomFaissVS Query: Top K={query.similarity_top_k}, Query Emb Shape: {query_embedding_np.shape}")

        distances, faiss_int_ids_results = self._faiss_index.search(query_embedding_np, query.similarity_top_k)

        distances_sq = distances[0]
        faiss_int_ids_results_sq = faiss_int_ids_results[0]

        logger.info(
            f"CustomFaissVS Query: Raw FAISS search results - Distances: {distances_sq}, FAISS INT IDs: {faiss_int_ids_results_sq}")

        valid_mask = faiss_int_ids_results_sq != -1
        valid_faiss_int_ids = faiss_int_ids_results_sq[valid_mask]
        valid_distances = distances_sq[valid_mask]

        logger.info(
            f"CustomFaissVS Query: Valid FAISS results after filtering - Distances: {valid_distances}, FAISS INT IDs: {valid_faiss_int_ids}")

        result_llama_node_ids: List[str] = []
        result_similarities: List[float] = []

        for i, faiss_int_id in enumerate(valid_faiss_int_ids):
            faiss_int_id_val = int(faiss_int_id)
            if faiss_int_id_val in self._faiss_id_to_node_id:
                llama_node_id = self._faiss_id_to_node_id[faiss_int_id_val]
                result_llama_node_ids.append(llama_node_id)
                result_similarities.append(valid_distances[i].item())
                logger.debug(
                    f"CustomFaissVS Query: Mapped FaissIntID {faiss_int_id_val} to LlamaNodeID '{llama_node_id}' with score {valid_distances[i]}.")
            else:
                logger.error(
                    f"CustomFaissVS Query: FaissIntID {faiss_int_id_val} retrieved from FAISS, but NOT FOUND in _faiss_id_to_node_id mapping! This means the mapping is inconsistent with the FAISS index content.")

        logger.info(f"CustomFaissVS Query: FINAL LlamaNodeIDs being returned to retriever: {result_llama_node_ids}")
        return VectorStoreQueryResult(
            ids=result_llama_node_ids,
            similarities=result_similarities,
            nodes=None
        )

    def delete(self, ref_doc_id: str, **delete_kwargs: Any) -> None:
        if not isinstance(self._faiss_index, (faiss.IndexIDMap, faiss.IndexIDMap2)):
            logger.warning(
                f"CustomFaissVS: FAISS index is not IndexIDMap/2. Deletion by ID not directly supported for '{ref_doc_id}'.")
            return

        faiss_ids_to_remove: List[int] = []
        llama_node_ids_to_cleanup_mapping: List[str] = []

        for llama_node_id, faiss_int_id in list(self._node_id_to_faiss_id.items()):
            if llama_node_id == ref_doc_id or llama_node_id.startswith(ref_doc_id + "_chunk_"):
                faiss_ids_to_remove.append(faiss_int_id)
                llama_node_ids_to_cleanup_mapping.append(llama_node_id)

        if faiss_ids_to_remove:
            logger.info(
                f"CustomFaissVS: Attempting to remove {len(faiss_ids_to_remove)} FAISS INT IDs for Llama ref_doc_id '{ref_doc_id}'. FAISS IDs: {faiss_ids_to_remove}")
            ids_to_remove_np = np.array(faiss_ids_to_remove, dtype=np.int64)
            try:
                selector = faiss.IDSelectorBatch(ids_to_remove_np.size, faiss.swig_ptr(ids_to_remove_np))
                num_removed_count = self._faiss_index.remove_ids(selector)
                logger.info(
                    f"CustomFaissVS: FAISS remove_ids reported {num_removed_count} vectors removed for Llama ref_doc_id '{ref_doc_id}'.")

                for llama_node_id_removed in llama_node_ids_to_cleanup_mapping:
                    faiss_int_id_pop = self._node_id_to_faiss_id.pop(llama_node_id_removed, None)
                    if faiss_int_id_pop is not None:
                        self._faiss_id_to_node_id.pop(faiss_int_id_pop, None)
                self._save_mappings()
            except Exception as e:
                logger.error(f"CustomFaissVS: Error during FAISS remove_ids for Llama ref_doc_id '{ref_doc_id}': {e}",
                             exc_info=True)
        else:
            logger.info(f"CustomFaissVS: No mapped FAISS INT IDs found to remove for Llama ref_doc_id '{ref_doc_id}'.")

    def delete_nodes(self, node_ids: List[str], **delete_kwargs: Any) -> None:
        if not isinstance(self._faiss_index, (faiss.IndexIDMap, faiss.IndexIDMap2)):
            logger.warning(
                "CustomFaissVS: FAISS index not IndexIDMap/2. Deletion by node_ids not supported at FAISS level.")
            return

        faiss_ids_to_remove: List[int] = []
        for node_id in node_ids:
            if node_id in self._node_id_to_faiss_id:
                faiss_ids_to_remove.append(self._node_id_to_faiss_id[node_id])
            else:
                logger.warning(f"Node ID '{node_id}' not found in internal FAISS ID mapping for deletion.")

        if faiss_ids_to_remove:
            logger.info(
                f"CustomFaissVS: Attempting to remove {len(faiss_ids_to_remove)} FAISS IDs for node_ids: {node_ids}. FAISS IDs: {faiss_ids_to_remove}")
            ids_to_remove_np = np.array(faiss_ids_to_remove, dtype=np.int64)
            try:
                selector = faiss.IDSelectorBatch(ids_to_remove_np.size, faiss.swig_ptr(ids_to_remove_np))
                num_actually_removed = self._faiss_index.remove_ids(selector)
                logger.info(f"CustomFaissVS: FAISS remove_ids for nodes reported {num_actually_removed} removed.")

                for node_id_to_remove in node_ids:
                    if node_id_to_remove in self._node_id_to_faiss_id:
                        faiss_int_id_removed = self._node_id_to_faiss_id.pop(node_id_to_remove)
                        if faiss_int_id_removed in self._faiss_id_to_node_id:
                            self._faiss_id_to_node_id.pop(faiss_int_id_removed)
                self._save_mappings()
            except Exception as e:
                logger.error(f"CustomFaissVS: Error during FAISS remove_ids for node_ids {node_ids}: {e}",
                             exc_info=True)
        else:
            logger.info(f"CustomFaissVS: No FAISS IDs mapped for node_ids: {node_ids} for deletion.")

    def _save_mappings(self) -> None:
        if not self._persist_path:
            logger.debug("CustomFaissVS: No persist_path set, skipping saving mappings.")
            return

        mappings_file = self._persist_path / MAPPINGS_FILENAME
        try:
            data_to_save = {
                "node_id_to_faiss_id": self._node_id_to_faiss_id,
                "faiss_id_to_node_id": {str(k): v for k, v in self._faiss_id_to_node_id.items()},
                "next_faiss_id": self._next_faiss_id,
            }
            with open(mappings_file, "w") as f:
                json.dump(data_to_save, f, indent=4)
            logger.info(f"CustomFaissVS: Mappings saved to {mappings_file}")
        except Exception as e:
            logger.error(f"CustomFaissVS: Failed to save mappings to {mappings_file}: {e}")

    def _load_mappings(self) -> None:
        if not self._persist_path:
            logger.debug("CustomFaissVS: No persist_path set, skipping loading mappings.")
            return

        mappings_file = self._persist_path / MAPPINGS_FILENAME
        if mappings_file.exists():
            try:
                with open(mappings_file, "r") as f:
                    loaded_data = json.load(f)
                self._node_id_to_faiss_id = loaded_data.get("node_id_to_faiss_id", {})
                self._faiss_id_to_node_id = {
                    int(k): v for k, v in loaded_data.get("faiss_id_to_node_id", {}).items()
                }
                self._next_faiss_id = loaded_data.get("next_faiss_id", 0)
                logger.info(
                    f"CustomFaissVS: Mappings loaded from {mappings_file}. Next FAISS ID: {self._next_faiss_id}")
            except Exception as e:
                logger.error(
                    f"CustomFaissVS: Failed to load mappings from {mappings_file}: {e}. Initializing empty mappings.")
                self._clear_mappings()
        else:
            logger.info(f"CustomFaissVS: Mappings file {mappings_file} not found. Initializing empty mappings.")
            self._clear_mappings()

    def _clear_mappings(self) -> None:
        self._node_id_to_faiss_id = {}
        self._faiss_id_to_node_id = {}
        self._next_faiss_id = 0
        logger.info("CustomFaissVS: Mappings cleared.")

    def clear(self) -> None:
        # This method is called by LlamaIndex if index.vector_store.clear() is invoked.
        # It should clear the FAISS index AND our custom mappings.
        if self._faiss_index:
            self._faiss_index.reset()  # Clears all vectors from FAISS index
            logger.info("CustomFaissVS: Underlying FAISS index has been reset.")
        self._clear_mappings()
        if self._persist_path:  # Save the cleared state
            self._save_mappings()
        logger.info("CustomFaissVS: Cleared FAISS index and all custom mappings.")