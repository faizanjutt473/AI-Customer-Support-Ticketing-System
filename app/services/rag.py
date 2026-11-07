"""RAG pipeline: KB articles -> chunks -> embeddings -> FAISS index -> retrieval -> (optional) Gemini reply."""
import os
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.models import KBArticle

INDEX_DIR = Path(__file__).resolve().parents[2] / "knowledge_base" / "faiss_index"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# FAISS returns squared L2 distance. On normalised vectors that is 2 - 2*cosine,
# so 1.4 keeps matches with cosine similarity of about 0.3 or more. Lower it to be stricter.
MAX_DISTANCE = 1.4

_embeddings = None
_store = None


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL, encode_kwargs={"normalize_embeddings": True}
        )
    return _embeddings


def build_index():
    """(Re)builds the FAISS index from the kb_articles table. Returns the number of chunks."""
    global _store
    docs = [
        Document(
            page_content=f"{a.title}. {a.body}",
            metadata={"article_id": a.id, "title": a.title, "category": a.category},
        )
        for a in KBArticle.query.all()
    ]
    if not docs:
        _store = None
        return 0
    chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(docs)
    _store = FAISS.from_documents(chunks, _get_embeddings())
    INDEX_DIR.parent.mkdir(parents=True, exist_ok=True)
    _store.save_local(str(INDEX_DIR))
    return len(chunks)


def _get_store():
    global _store
    if _store is None:
        if (INDEX_DIR / "index.faiss").exists():
            _store = FAISS.load_local(
                str(INDEX_DIR), _get_embeddings(), allow_dangerous_deserialization=True
            )
        else:
            build_index()
    return _store


def retrieve(query, k=3):
    """Returns [(KBArticle, distance), ...] for the most relevant articles (best first)."""
    store = _get_store()
    if store is None or not query.strip():
        return []
    found, seen = [], set()
    for doc, dist in store.similarity_search_with_score(query, k=k * 2):
        aid = doc.metadata["article_id"]
        if aid in seen or float(dist) > MAX_DISTANCE:
            continue
        article = KBArticle.query.get(aid)
        if article:
            seen.add(aid)
            found.append((article, float(dist)))
        if len(found) == k:
            break
    return found


def draft_reply(ticket, articles):
    """Plain template reply from the best article (works without any API key)."""
    if not articles:
        return ""
    body = articles[0].body.strip()
    if body[-1] not in ".!?":
        body += "."
    return (
        f"Hi {ticket.customer.name}, thanks for reaching out. {body} "
        "Let us know if you need anything else."
    )


def llm_reply(ticket, articles):
    """Gemini writes the reply using ONLY the retrieved articles. Returns (text, error)."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None, "GOOGLE_API_KEY is not set in .env"
    if not articles:
        return None, "No relevant knowledge base article was found for this ticket."
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-flash-latest"),
            google_api_key=api_key,
            temperature=0.2,
        )
        context = "\n\n".join(f"[{a.title}]\n{a.body}" for a in articles)
        prompt = (
            "You are a polite customer support agent. Write a short, clear reply (max 120 words) "
            "to the customer's ticket. Use ONLY the knowledge base context below. If the context "
            "does not answer the problem, say we are looking into it. Do not invent policies or numbers.\n\n"
            f"Knowledge base context:\n{context}\n\n"
            f"Customer: {ticket.customer.name}\nSubject: {ticket.subject}\nMessage: {ticket.description}\n\n"
            "Reply (start with a greeting, no subject line):"
        )
        text = str(llm.invoke(prompt).text).strip()
        return (text or None), (None if text else "The model returned an empty reply.")
    except Exception as e:  # network, quota, wrong model name, bad key...
        return None, f"{type(e).__name__}: {str(e)[:200]}"