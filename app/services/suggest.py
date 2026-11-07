import re

from app.models import KBArticle

STOP = {
    "the", "and", "for", "you", "your", "this", "that", "with", "are", "was",
    "have", "has", "not", "can", "please", "our", "from", "but", "any", "all",
    "how", "its", "i", "my", "after", "every", "when", "will",
}


def _words(text):
    return set(re.findall(r"[a-z]{3,}", text.lower())) - STOP


def suggest_articles(ticket, limit=2):
    """Simple keyword matcher. Will be replaced by the RAG (FAISS) search later."""
    ticket_words = _words(f"{ticket.subject} {ticket.description}")
    scored = []
    for article in KBArticle.query.all():
        overlap = len(ticket_words & _words(f"{article.title} {article.body}"))
        if overlap == 0:
            continue
        score = overlap + (1 if article.category == ticket.category else 0)
        scored.append((score, article))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in scored[:limit]]