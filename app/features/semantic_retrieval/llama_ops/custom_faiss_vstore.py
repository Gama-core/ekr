# app/features/semantic_retrieval/llama_ops/custom_faiss_vstore.py
import logging
from typing import List, Any, cast
import numpy as np
import faiss  # Ensure faiss is imported

from llama_index.core.schema import BaseNode
from llama_index.vector_stores.faiss import FaissVectorStore
from llama_index.core.bridge.pydantic import PrivateAttr

logger = logging.getLogger(__name__)


class CustomFaissVectorStore(FaissVectorStore):
    """
    Custom FaissVectorStore that ensures add_with_ids is used for IndexIDMap
    and IndexIDMap2, and handles LlamaIndex node ID to FAISS integer ID mapping.
    """
    _faiss_id_to_node_id: dict[int, str] = PrivateAttr(default_factory=dict)
    _node_id_to_faiss_id: dict[str, int] = PrivateAttr(default_factory=dict)
    _next_faiss_id: int = PrivateAttr(default=0)  # For generating sequential int IDs for FAISS

    def __init__(self, faiss_index: faiss.Index, **kwargs: Any) -> None:
        super().__init__(faiss_index=faiss_index, **kwargs)
        # Initialize mappings if loading a persisted index that had them
        # This part would need more sophisticated loading if you persist these mappings separately.
        # For now, we assume new index or LlamaIndex handles docstore/node_id mapping persistence.

    def _get_faiss_id(self, node_id: str) -> int:
        """Gets or creates a FAISS integer ID for a LlamaIndex node_id."""
        if node_id not in self._node_id_to_faiss_id:
            current_id = self._next_faiss_id
            self._node_id_to_faiss_id[node_id] = current_id
            self._faiss_id_to_node_id[current_id] = node_id
            self._next_faiss_id += 1
            return current_id
        return self._node_id_to_faiss_id[node_id]

    def add(self, nodes: List[BaseNode], **add_kwargs: Any) -> List[str]:
        """
        Add nodes to the Faiss index.

        Args:
            nodes: List of BaseNode objects.

        Returns:
            List of node IDs that were added.
        """
        if not nodes:
            return []

        embeddings = []
        faiss_ids_to_add = []
        added_node_ids = []

        for node in nodes:
            if node.embedding is None:
                logger.debug(
                    f"Node {node.node_id} has no embedding, skipping.")  # LlamaIndex might generate it later if not present
                # Or generate it here if self._embed_model is available and configured
                if self._embed_model:
                    node.embedding = self._embed_model.get_text_embedding(node.get_content(metadata_mode="all"))
                else:
                    logger.warning(
                        f"Node {node.node_id} has no embedding and no embed_model in vector store. Skipping.")
                    continue

            embeddings.append(node.embedding)

            # Use LlamaIndex node_id. We need to map it to an integer for FAISS IndexIDMap.
            # The node.id_ or node.node_id is usually a string like "note_123_chunk_0"
            # FAISS IndexIDMap requires 64-bit integers.
            # We'll use a simple hashing or a dedicated mapping.
            # For simplicity and direct use of what LlamaIndex provides:
            # LlamaIndex's node_id is a string. FaissVectorStore expects to store
            # integer IDs if using IndexIDMap.

            # Using a simple internal counter for FAISS IDs for this example.
            # A more robust solution might involve persisting this mapping.
            faiss_int_id = self._get_faiss_id(node.node_id)  # node.node_id or node.id_
            faiss_ids_to_add.append(faiss_int_id)
            added_node_ids.append(node.node_id)

        if not embeddings:
            logger.info("No embeddings generated or found for the provided nodes.")
            return []

        embeddings_np = np.array(embeddings, dtype=np.float32)

        if isinstance(self._faiss_index, (faiss.IndexIDMap, faiss.IndexIDMap2)):
            ids_np = np.array(faiss_ids_to_add, dtype=np.int64)
            logger.debug(
                f"CustomFaissVectorStore: Adding {len(embeddings_np)} embeddings with {len(ids_np)} custom IDs to IndexIDMap/2.")
            self._faiss_index.add_with_ids(embeddings_np, ids_np)
        else:
            # This case should ideally not be hit if we ensure IndexIDMap2 is always used
            logger.debug(f"CustomFaissVectorStore: Adding {len(embeddings_np)} embeddings to plain FAISS index.")
            self._faiss_index.add(embeddings_np)
            # If it's a plain index, FAISS assigns its own sequential IDs.
            # LlamaIndex DocStore still maps its node_id to these.

        return added_node_ids

    def delete(self, ref_doc_id: str, **delete_kwargs: Any) -> None:
        """
        Delete a document and its nodes from the Faiss index.
        LlamaIndex typically calls this, and it expects us to find all node_ids (chunks)
        related to this ref_doc_id and delete their corresponding FAISS vectors.

        Args:
            ref_doc_id (str): The document ID (e.g., "note_123")
        """
        if not isinstance(self._faiss_index, (faiss.IndexIDMap, faiss.IndexIDMap2)):
            logger.warning(
                f"FAISS index is not IndexIDMap or IndexIDMap2. Deletion of doc '{ref_doc_id}' by ID not supported at FAISS level. Relying on DocStore removal.")
            return

        # This is tricky: FaissVectorStore's delete is usually called by LlamaIndex's
        # VectorStoreIndex.delete_ref_doc(), which itself would have figured out
        # which *nodes* to delete. If LlamaIndex passes specific node_ids (vector_ids)
        # to a lower-level delete_vectors method, that would be ideal.
        # The default FaissVectorStore.delete(ref_doc_id) might not work as expected
        # without direct access to the DocStore or a mapping of ref_doc_id to FAISS int IDs.

        # For now, let's assume LlamaIndex's `index.delete_ref_doc(doc_id_to_delete)`
        # will iterate through nodes and for each node, it might call a more granular
        # delete method if available, or this `delete` method with a specific `vector_id`
        # (which would be our FAISS int ID).

        # A more robust deletion at this level requires knowing all FAISS int IDs
        # that correspond to the chunks of ref_doc_id.
        # This mapping (ref_doc_id -> list of its chunk node_ids -> list of FAISS int_ids)
        # needs to be maintained. LlamaIndex's DocStore holds part of this.

        # Let's assume for now that LlamaIndex's higher-level delete logic
        # will call a method that passes specific FAISS int IDs to be removed.
        # If it calls this `delete` method with `ref_doc_id`, and expects this store
        # to figure out all related FAISS IDs, we need a more complex mapping here.

        # The most common way LlamaIndex handles this is by deleting nodes one by one
        # from the vector store using their specific node IDs if the store supports it.
        # The `delete_ref_doc` in `VectorStoreIndex` finds nodes belonging to the doc
        # and then calls `self.vector_store.delete_nodes([node_ids_to_delete])` or similar.

        # So, we might not need to implement this `delete(ref_doc_id)` so complexly if
        # LlamaIndex calls a more granular `delete_nodes` or `delete_vector_by_id`.
        # The `FaissVectorStore` has a `delete_nodes` which expects a list of `node_ids`.

        # Let's ensure `remove_ids` is callable.
        faiss_ids_to_remove: List[int] = []
        # This is a placeholder - we need to get the FAISS int IDs for this ref_doc_id
        # For example, if we stored a mapping:
        for faiss_id, node_id_val in list(self._faiss_id_to_node_id.items()):  # Iterate over a copy
            # Assuming node_id_val is like "note_123_chunk_0" and ref_doc_id is "note_123"
            if node_id_val.startswith(ref_doc_id + "_") or node_id_val == ref_doc_id:  # Crude check
                faiss_ids_to_remove.append(faiss_id)
                # Clean up internal mappings
                del self._faiss_id_to_node_id[faiss_id]
                if node_id_val in self._node_id_to_faiss_id:
                    del self._node_id_to_faiss_id[node_id_val]

        if faiss_ids_to_remove:
            logger.info(
                f"CustomFaissVectorStore: Attempting to remove {len(faiss_ids_to_remove)} FAISS IDs for ref_doc_id '{ref_doc_id}'. IDs: {faiss_ids_to_remove}")
            ids_to_remove_np = np.array(faiss_ids_to_remove, dtype=np.int64)
            try:
                num_removed = self._faiss_index.remove_ids(ids_to_remove_np)
                logger.info(
                    f"CustomFaissVectorStore: Removed {num_removed.sum() if hasattr(num_removed, 'sum') else num_removed} vectors from FAISS for ref_doc_id '{ref_doc_id}'.")
            except Exception as e:
                logger.error(
                    f"CustomFaissVectorStore: Error during FAISS remove_ids for ref_doc_id '{ref_doc_id}': {e}")
        else:
            logger.info(f"CustomFaissVectorStore: No FAISS IDs found to remove for ref_doc_id '{ref_doc_id}'.")

    # You might need to implement or ensure delete_nodes exists and works similarly
    # def delete_nodes(self, node_ids: List[str], **delete_kwargs: Any) -> None:
    #     faiss_ids_to_remove = []
    #     for node_id in node_ids:
    #         if node_id in self._node_id_to_faiss_id:
    #             faiss_int_id = self._node_id_to_faiss_id[node_id]
    #             faiss_ids_to_remove.append(faiss_int_id)
    #             # Clean up internal mappings
    #             del self._node_id_to_faiss_id[node_id]
    #             if faiss_int_id in self._faiss_id_to_node_id:
    #                 del self._faiss_id_to_node_id[faiss_int_id]
    #         else:
    #             logger.warning(f"Node ID {node_id} not found in internal FAISS ID mapping for deletion.")

    #     if faiss_ids_to_remove:
    #         ids_to_remove_np = np.array(faiss_ids_to_remove, dtype=np.int64)
    #         num_removed = self._faiss_index.remove_ids(ids_to_remove_np) # type: ignore
    #         logger.info(f"CustomFaissVectorStore: Removed {num_removed.sum()} vectors for node_ids: {node_ids}")
    #     else:
    #         logger.info(f"CustomFaissVectorStore: No FAISS IDs found for node_ids: {node_ids}")

    # Persistence of the _faiss_id_to_node_id and _node_id_to_faiss_id mappings
    # would be important for a production system. This example doesn't fully implement it.
    # LlamaIndex usually handles this via its StorageContext and GraphStore/DocStore.
    # The key is that the FAISS IDs must be consistent across sessions if you load the index.