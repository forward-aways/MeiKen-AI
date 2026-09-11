"""知识库（RAG）：文档解析、切分、向量化与检索。

设计：向量库按用户隔离（metadata.user_id 过滤），
文件保存到用户工作区，检索结果携带来源文件名供引用展示。

注意：在导入 chromadb 之前关闭匿名遥测——posthog 上报在部分网络环境下
会无限阻塞初始化（已经实测：开启时卡死，关闭后 0.4s）。
"""
import os

os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")

import uuid
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import CHROMA_DIR, UPLOAD_DIR

Path(UPLOAD_DIR).mkdir(exist_ok=True)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

_text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", "。", ".", " ", ""],
)

_embedding_fn = None
_vectorstore = None


class ChromadbEmbeddingAdapter(Embeddings):
    """把 chromadb 原生 embedding 函数适配为 langchain 的 Embeddings 接口。"""

    def __init__(self, ef):
        self._ef = ef

    def embed_documents(self, texts):
        return self._ef(texts).tolist()

    def embed_query(self, text):
        return self._ef(text).tolist()


def _get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        import chromadb.utils.embedding_functions as ef
        _embedding_fn = ChromadbEmbeddingAdapter(ef.DefaultEmbeddingFunction())
    return _embedding_fn


def _get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=_get_embedding_fn(),
            collection_name="meiken_kb",
        )
    return _vectorstore


def extract_text(filepath: str, filename: str) -> str:
    """提取文件正文（统一走文档解析层，支持 pdf/docx/xlsx/pptx/csv/html 等）。"""
    from backend.documents import extract_document
    return extract_document(filepath, filename).text


def ingest_document(filepath: str, filename: str, file_id: str, scope: str = "temp", user_id: int = 0):
    """提取文本、切分为块并写入 Chroma 向量库，返回块数。"""
    text = extract_text(filepath, filename)
    if not text.strip():
        return 0

    chunks = _text_splitter.split_text(text)
    docs = [
        Document(
            page_content=chunk,
            metadata={"file_id": file_id, "filename": filename, "scope": scope, "user_id": user_id},
        )
        for chunk in chunks
    ]
    _get_vectorstore().add_documents(docs)
    return len(chunks)


def search_relevant(query: str, scope: str = None, k: int = 4, file_ids: list = None, user_id: int = None):
    """检索相关文档块：始终限定在当前用户范围内。"""
    vs = _get_vectorstore()
    filters = {}
    if user_id is not None:
        filters["user_id"] = user_id
    if file_ids:
        filters["file_id"] = {"$in": file_ids}
    elif scope:
        filters["scope"] = scope
    filter_dict = filters or None
    results = vs.similarity_search_with_relevance_scores(query, k=k, filter=filter_dict)
    return [
        {
            "content": doc.page_content,
            "filename": doc.metadata.get("filename", ""),
            "file_id": doc.metadata.get("file_id", ""),
            "score": round(score, 3),
        }
        for doc, score in results
    ]


def delete_document(file_id: str):
    """删除某个文件的全部向量块。"""
    _get_vectorstore().delete(where={"file_id": file_id})


def save_upload_file(file_content: bytes, filename: str, user_id: int = 0):
    """保存上传文件到用户工作区，返回 (文件路径, 文件 ID)。"""
    from backend.workspace import save_upload
    file_id = uuid.uuid4().hex[:12]
    ext = Path(filename).suffix
    path = save_upload(user_id, file_id, ext, file_content)
    return path, file_id


def cleanup_upload_file(filepath: str):
    """删除磁盘上的上传文件（忽略失败）。"""
    try:
        os.remove(filepath)
    except OSError:
        pass
