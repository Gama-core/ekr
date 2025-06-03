# app/features/semantic_retrieval/llama_ops/embedding_setup.py
import logging
from llama_index.core import Settings as LlamaSettings, Document as LlamaDocument
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from app.core.config import settings as core_settings
from app.features.semantic_retrieval.config import semantic_retrieval_config
from app.db_connectors.schemas import NoteForIndex as DBNoteForIndexSchema
from app.features.semantic_retrieval.llama_ops import get_llama_settings_initialized_flag, set_llama_settings_initialized_flag

logger = logging.getLogger(__name__)

def initialize_llama_index_settings():
    if get_llama_settings_initialized_flag() and LlamaSettings.llm and LlamaSettings.embed_model:
        return

    logger.info("Llama_ops: Configuring LlamaIndex global settings...")
    try:
        LlamaSettings.llm = LlamaOpenAI(
            model=core_settings.QWEN_DEFAULT_MODEL,
            api_base=core_settings.QWEN_BASE_URL,
            api_key=core_settings.QWEN_API_KEY,
            temperature=0.1,
        )
        logger.info(f"Llama_ops: LLM configured with Qwen model: {core_settings.QWEN_DEFAULT_MODEL}")

        if core_settings.EMBEDDING_MODEL_PROVIDER == "huggingface":
            LlamaSettings.embed_model = HuggingFaceEmbedding(
                model_name=core_settings.HF_EMBEDDING_MODEL_NAME
            )
            logger.info(
                f"Llama_ops: Embed Model (HuggingFace): {core_settings.HF_EMBEDDING_MODEL_NAME} "
                f"(Dim: {core_settings.ACTIVE_EMBEDDING_DIMENSION})"
            )
        else:
            err_msg = f"Unsupported EMBEDDING_MODEL_PROVIDER: '{core_settings.EMBEDDING_MODEL_PROVIDER}'"
            logger.error(err_msg)
            raise ValueError(err_msg)

        LlamaSettings.chunk_size = semantic_retrieval_config.DEFAULT_CHUNK_SIZE
        LlamaSettings.chunk_overlap = semantic_retrieval_config.DEFAULT_CHUNK_OVERLAP
        logger.info(
            f"Llama_ops: chunk_size: {LlamaSettings.chunk_size}, chunk_overlap: {LlamaSettings.chunk_overlap}")
        set_llama_settings_initialized_flag(True)
    except Exception as e:
        logger.exception(f"CRITICAL: Llama_ops: Failed to initialize LlamaIndex Core Settings: {e}")
        raise


def db_note_to_llama_document(note_data: DBNoteForIndexSchema) -> LlamaDocument:
    doc_id = f"note_{note_data.id}"
    metadata = {
        "note_id": str(note_data.id),
        "title": str(note_data.title or "Untitled"),
        "creation_date": str(note_data.creation_date.isoformat() if note_data.creation_date else ""),
        "owner_id": str(note_data.owner_id),
        "source_type": "note"
    }
    text_content = note_data.text_content if note_data.text_content and note_data.text_content.strip() else " "
    return LlamaDocument(text=text_content, doc_id=doc_id, metadata=metadata, id_=doc_id) # Ensure id_ is set for LlamaIndex