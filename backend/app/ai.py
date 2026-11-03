import re, json
import httpx
from collections import Counter
from .config import settings

STOP=set('the a an and or but to of in on for with is are was were be this that from by as at it its into your you what how why when where which can could should would about'.split())
def split_chunks(text: str, page: int, size: int=1100, overlap: int=160):
    text=re.sub(r'\\s+',' ',text).strip(); out=[]
    for start in range(0,len(text),size-overlap):
        chunk=text[start:start+size]
        if len(chunk)>80: out.append({'text':chunk,'page':page})
    return out
def tokens(s): return [w.lower() for w in re.findall(r'[A-Za-z0-9]{3,}',s) if w.lower() not in STOP]
def retrieve(question: str, docs: list[dict], limit=5):
    q=set(tokens(question)); ranked=[]
    for doc in docs:
        for chunk in doc.get('chunks',[]):
            words=tokens(chunk['text']); counts=Counter(words); overlap=sum(counts[w] for w in q)
            if overlap: ranked.append((overlap/(len(words)**0.5+1),doc['filename'],chunk))
    ranked.sort(key=lambda x:x[0],reverse=True)
    return [{'filename':name,**chunk} for _,name,chunk in ranked[:limit]]
async def llm(prompt: str, system: str='You are LearnPilot, a careful educational assistant.'):
    if not settings.llm_api_key or settings.llm_provider=='none': return None
    base='https://generativelanguage.googleapis.com/v1beta/openai' if settings.llm_provider=='gemini' else settings.llm_base_url
    async with httpx.AsyncClient(timeout=60) as client:
        r=await client.post(base.rstrip('/')+'/chat/completions',headers={'Authorization':f'Bearer {settings.llm_api_key}'},json={'model':settings.llm_model,'messages':[{'role':'system','content':system},{'role':'user','content':prompt}],'temperature':0.3})
        r.raise_for_status(); return r.json()['choices'][0]['message']['content']
def fallback_quiz(text: str,count: int):
    sentences=[s.strip() for s in re.split(r'(?<=[.!?])\\s+',text) if len(s.strip())>55]; questions=[]
    for s in sentences[:count]:
        words=[w for w in re.findall(r'\\b[A-Za-z][A-Za-z-]{5,}\\b',s) if w.lower() not in STOP]
        if not words: continue
        answer=max(set(words),key=words.count); stem=re.sub(re.escape(answer),'____',s,count=1,flags=re.I)
        distractors=list(dict.fromkeys([w for x in sentences for w in re.findall(r'\\b[A-Za-z][A-Za-z-]{5,}\\b',x) if w.lower()!=answer.lower()]))[:3]
        options=[answer]+distractors[:3]
        while len(options)<4: options.append(f'Option {len(options)+1}')
        questions.append({'question':f'Complete the statement: {stem}','options':options,'answer':answer,'explanation':f'The source states: {s}','type':'mcq'})
    return questions
