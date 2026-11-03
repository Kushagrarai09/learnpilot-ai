import re
from collections import Counter
import httpx
from .config import settings

STOP = set('the a an and or but to of in on for with is are was were be this that from by as at it its into your you what how why when where which can could should would about'.split())

def split_chunks(text: str, page: int, size: int = 1100, overlap: int = 160):
    if size <= overlap or overlap < 0: raise ValueError('size must be greater than overlap and overlap cannot be negative')
    normalized = re.sub(r'\s+', ' ', text).strip()
    return [{'text': normalized[start:start + size], 'page': page} for start in range(0, len(normalized), size - overlap) if len(normalized[start:start + size]) > 80]

def tokens(value: str): return [w.lower() for w in re.findall(r'[A-Za-z0-9]{3,}', value) if w.lower() not in STOP]

def retrieve(question: str, docs: list[dict], limit: int = 5):
    terms = set(tokens(question)); ranked = []
    for document in docs:
        for chunk in document.get('chunks', []):
            words = tokens(chunk['text']); counts = Counter(words); overlap = sum(counts[w] for w in terms)
            if overlap: ranked.append((overlap / (len(words) ** 0.5 + 1), document['filename'], chunk))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [{'filename': filename, **chunk} for _, filename, chunk in ranked[:limit]]

async def llm(prompt: str, system: str = 'You are LearnPilot, a careful educational assistant.'):
    if not settings.llm_api_key or settings.llm_provider == 'none': return None
    base = 'https://generativelanguage.googleapis.com/v1beta/openai' if settings.llm_provider == 'gemini' else settings.llm_base_url
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(base.rstrip('/') + '/chat/completions', headers={'Authorization': f'Bearer {settings.llm_api_key}'}, json={'model': settings.llm_model, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}], 'temperature': 0.3})
        response.raise_for_status(); return response.json()['choices'][0]['message']['content']

def fallback_quiz(text: str, count: int):
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 55]; questions = []
    for sentence in sentences:
        if len(questions) >= count: break
        words = [w for w in re.findall(r'\b[A-Za-z][A-Za-z-]{5,}\b', sentence) if w.lower() not in STOP]
        if not words: continue
        answer = max(set(words), key=words.count); stem = re.sub(re.escape(answer), '____', sentence, count=1, flags=re.I)
        distractors = list(dict.fromkeys(w for other in sentences for w in re.findall(r'\b[A-Za-z][A-Za-z-]{5,}\b', other) if w.lower() != answer.lower()))[:3]
        options = [answer] + distractors
        while len(options) < 4: options.append(f'Option {len(options) + 1}')
        questions.append({'question': f'Complete the statement: {stem}', 'options': options, 'answer': answer, 'explanation': f'The source states: {sentence}', 'type': 'mcq'})
    return questions
