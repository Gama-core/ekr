import logging
from llama_index.core import Settings as LlamaSettings, Document as LlamaDocument
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Use relative imports
from ..config import settings
from ..schemas import NoteForIndex
from . import get_llama_settings_initialized_flag, set_llama_settings_initialized_flag

logger = logging.getLogger(__name__)

def initialize_llama_index_settings():
    """Configures the global LlamaIndex settings for the service."""
    if get_llama_settings_initialized_flag() and LlamaSettings.llm and LlamaSettings.embed_model:
        return

    logger.info("Llama_ops: Configuring LlamaIndex global settings...")
    try:
        # Setup LLM for LlamaIndex (e.g., for summarization during retrieval)
        if settings.QWEN_API_KEY:
            LlamaSettings.llm = LlamaOpenAI(
                model=settings.QWEN_DEFAULT_MODEL,
                api_base=settings.QWEN_BASE_URL,
                api_key=settings.QWEN_API_KEY.get_secret_value(),
                temperature=0.1,
            )
            logger.info(f"Llama_ops: LLM configured with Qwen model: {settings.QWEN_DEFAULT_MODEL}")
        else:
            LlamaSettings.llm = None
            logger.warning("Llama_ops: QWEN_API_KEY not found, LlamaSettings.llm is not configured.")

        # Setup Embedding Model
        if settings.EMBEDDING_MODEL_PROVIDER == "huggingface":
            LlamaSettings.embed_model = HuggingFaceEmbedding(
                model_name=settings.HF_EMBEDDING_MODEL_NAME
            )
            logger.info(
                f"Llama_ops: Embed Model (HuggingFace): {settings.HF_EMBEDDING_MODEL_NAME} "
                f"(Dim: {settings.ACTIVE_EMBEDDING_DIMENSION})"
            )
        else:
            # You can add other providers like 'dashscope' here later
            err_msg = f"Unsupported EMBEDDING_MODEL_PROVIDER: '{settings.EMBEDDING_MODEL_PROVIDER}'"
            logger.error(err_msg)
            raise ValueError(err_msg)

        LlamaSettings.chunk_size = settings.DEFAULT_CHUNK_SIZE
        LlamaSettings.chunk_overlap = settings.DEFAULT_CHUNK_OVERLAP
        logger.info(f"Llama_ops: chunk_size: {LlamaSettings.chunk_size}, chunk_overlap: {LlamaSettings.chunk_overlap}")
        set_llama_settings_initialized_flag(True)
    except Exception as e:
        logger.exception(f"CRITICAL: Llama_ops: Failed to initialize LlamaIndex Core Settings: {e}")
        raise

def db_note_to_llama_document(note_data: NoteForIndex) -> LlamaDocument:
    """Converts the Pydantic Note DTO into a LlamaIndex Document."""
    document_internal_id = f"note_{note_data.id}"
    metadata = {
        "note_id": str(note_data.id),
        "title": str(note_data.title or "Untitled"),
        "creation_date": str(note_data.creation_date.isoformat() if note_data.creation_date else ""),
        "owner_id": str(note_data.owner_id),
        "source_type": "note"
    }
    # Provide a placeholder space if content is empty to avoid errors in LlamaIndex
    text_content = note_data.text_content if note_data.text_content and note_data.text_content.strip() else " "

    return LlamaDocument(text=text_content, id_=document_internal_id, metadata=metadata)