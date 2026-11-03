import os, json
from pathlib import Path
import fitz
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .config import settings
from .database import Base, engine, SessionLocal
from .models import Document, StudyEvent
from .schemas import ChatRequest, GenerateRequest
from .ai import split_chunks, retrieve, llm, fallback_quiz
from . import vector_store

Base.metadata.create_all(bind=engine)
Path(settings.upload_dir).mkdir(parents=True,exist_ok=True)
app=FastAPI(title=settings.app_name,version='1.0.0',description='AI-powered personal learning and teaching assistant')
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(',')],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
def db():
    s=SessionLocal()
    try: yield s
    finally: s.close()
def as_doc(d):
    chunks=[]
    try:
        with fitz.open(d.stored_path) as pdf:
            for idx,page in enumerate(pdf): chunks+=split_chunks(page.get_text(),idx+1)
    except Exception: pass
    return {'id':d.id,'filename':d.filename,'page_count':d.page_count,'chunks':chunks}
@app.get('/api/health')
def health(): return {'status':'ok','service':'LearnPilot AI','llm_configured':bool(settings.llm_api_key)}
@app.get('/api/documents')
def list_documents(s:Session=Depends(db)):
    return [{'id':d.id,'filename':d.filename,'page_count':d.page_count,'created_at':str(d.created_at)} for d in s.query(Document).order_by(Document.id.desc()).all()]
@app.post('/api/documents/upload')
async def upload_document(file:UploadFile=File(...),s:Session=Depends(db)):
    if not file.filename or not file.filename.lower().endswith('.pdf'): raise HTTPException(400,'Only PDF files are supported.')
    data=await file.read()
    if len(data)>settings.max_upload_mb*1024*1024: raise HTTPException(413,f'Maximum upload size is {settings.max_upload_mb} MB.')
    safe=Path(file.filename).name.replace(' ','_'); path=Path(settings.upload_dir)/f'{os.urandom(6).hex()}_{safe}'; path.write_bytes(data)
    try:
        with fitz.open(path) as pdf: pages=[p.get_text() for p in pdf]; count=len(pdf)
    except Exception:
        path.unlink(missing_ok=True); raise HTTPException(400,'Could not read this PDF. It may be encrypted or damaged.')
    extracted='\\n'.join(f'\\n[Page {i+1}]\\n{t}' for i,t in enumerate(pages))
    if not extracted.strip(): path.unlink(missing_ok=True); raise HTTPException(422,'No selectable text found. OCR is not enabled.')
    d=Document(filename=file.filename,stored_path=str(path),page_count=count,extracted_text=extracted); s.add(d); s.commit(); s.refresh(d)
    try: vector_store.index_document(d.id,d.filename,[c for i,p in enumerate(pages) for c in split_chunks(p,i+1)])
    except Exception: pass
    return {'id':d.id,'filename':d.filename,'page_count':count,'message':'Document processed successfully.'}
@app.delete('/api/documents/{doc_id}')
def delete_document(doc_id:int,s:Session=Depends(db)):
    d=s.get(Document,doc_id)
    if not d: raise HTTPException(404,'Document not found')
    Path(d.stored_path).unlink(missing_ok=True)
    try: vector_store.delete_document(doc_id)
    except Exception: pass
    s.delete(d); s.commit(); return {'deleted':doc_id}
@app.post('/api/chat')
async def chat(req:ChatRequest,s:Session=Depends(db)):
    q=s.query(Document)
    if req.document_ids: q=q.filter(Document.id.in_(req.document_ids))
    docs=[as_doc(d) for d in q.all()]
    if not docs: raise HTTPException(400,'Upload or select at least one study document first.')
    try: hits=vector_store.search(req.question,[d['id'] for d in docs],limit=5)
    except Exception: hits=retrieve(req.question,docs)
    if not hits: return {'answer':'I could not find relevant information in the selected material. Try rephrasing your question.','citations':[],'mode':'grounded-retrieval'}
    context='\\n\\n'.join(f"[{h['filename']}, page {h['page']}] {h['text']}" for h in hits)
    prompt=f'Answer using ONLY these excerpts. If unsupported, say so. Cite claims as [filename, p. N].\\n\\n{context}\\n\\nQUESTION: {req.question}'
    answer=await llm(prompt,'You are a precise tutor. Explain clearly and never invent facts or citations.')
    if not answer: answer='Relevant passages from your material:\\n\\n'+'\\n\\n'.join(f"**{h['filename']} — page {h['page']}**\\n{h['text'][:700]}" for h in hits[:3])+'\\n\\nDemo retrieval mode: configure an LLM API key for synthesized answers.'
    return {'answer':answer,'citations':[{'filename':h['filename'],'page':h['page']} for h in hits],'mode':'llm-rag' if settings.llm_api_key else 'retrieval-demo'}
@app.post('/api/quiz')
async def quiz(req:GenerateRequest,s:Session=Depends(db)):
    q=s.query(Document)
    if req.document_ids: q=q.filter(Document.id.in_(req.document_ids))
    docs=q.all()
    if not docs: raise HTTPException(400,'Upload a document first.')
    text='\\n'.join(d.extracted_text for d in docs); prompt=f'Create {req.count} {req.difficulty} multiple-choice questions from this material. Return ONLY JSON array of objects with question, options (4 strings), answer, explanation.\\n{text[:14000]}'
    raw=await llm(prompt,'You are an assessment designer. Questions must be answerable from the provided content.'); questions=[]
    if raw:
        try: questions=json.loads(raw[raw.find('['):raw.rfind(']')+1])
        except Exception: pass
    if not questions: questions=fallback_quiz(text,req.count)
    return {'questions':questions[:req.count],'source_documents':[d.filename for d in docs]}
@app.post('/api/flashcards')
async def flashcards(req:GenerateRequest,s:Session=Depends(db)):
    q=s.query(Document)
    if req.document_ids: q=q.filter(Document.id.in_(req.document_ids))
    docs=q.all()
    if not docs: raise HTTPException(400,'Upload a document first.')
    text='\\n'.join(d.extracted_text for d in docs); raw=await llm(f'Create {req.count} concise study flashcards. Return ONLY JSON array with front and back.\\n{text[:14000]}','You create accurate active-recall flashcards.'); cards=[]
    if raw:
        try: cards=json.loads(raw[raw.find('['):raw.rfind(']')+1])
        except Exception: pass
    if not cards: cards=[{'front':q['question'],'back':q['answer']+'. '+q['explanation']} for q in fallback_quiz(text,req.count)]
    return {'flashcards':cards[:req.count]}
@app.post('/api/roadmap')
async def roadmap(req:GenerateRequest,s:Session=Depends(db)):
    q=s.query(Document)
    if req.document_ids: q=q.filter(Document.id.in_(req.document_ids))
    docs=q.all()
    if not docs: raise HTTPException(400,'Upload a document first.')
    text=' '.join(d.extracted_text for d in docs); raw=await llm(f'Create a practical 7-day learning roadmap. Return JSON array with day, focus, activities, outcome.\\n{text[:10000]}','You are a learning coach.'); plan=None
    if raw:
        try: plan=json.loads(raw[raw.find('['):raw.rfind(']')+1])
        except Exception: pass
    if not plan:
        heads=[x.strip() for x in text.split('.') if len(x.strip())>35][:7]
        plan=[{'day':f'Day {i+1}','focus':heads[i][:75] if i<len(heads) else 'Review and consolidate','activities':['Read the relevant section','Write a short summary','Test yourself with 5 questions'],'outcome':'Explain the concept without notes'} for i in range(7)]
    return {'roadmap':plan}
@app.post('/api/teacher/lesson-plan')
async def lesson_plan(req:GenerateRequest,s:Session=Depends(db)):
    q=s.query(Document)
    if req.document_ids: q=q.filter(Document.id.in_(req.document_ids))
    docs=q.all()
    if not docs: raise HTTPException(400,'Upload a document first.')
    material='\\n'.join(d.extracted_text for d in docs)[:12000]
    result=await llm(f'Create a teacher-ready 45-minute lesson plan and worksheet. Include objectives, timing, activities, assessment, and five questions.\\n{material}','You are an experienced teacher creating classroom-ready materials.')
    if not result: result='# 45-minute lesson plan\\n\\n- 0–5 min: Starter and prior-knowledge check\\n- 5–15 min: Explain key concepts\\n- 15–25 min: Guided example\\n- 25–35 min: Pair activity\\n- 35–42 min: Independent practice\\n- 42–45 min: Exit ticket\\n\\n## Worksheet\\n1. Define the central concept.\\n2. List two supporting ideas.\\n3. Explain how they connect.\\n4. Apply one idea to an example.\\n5. Write one question you still have.'
    return {'content':result}
@app.post('/api/events/quiz-result')
def quiz_result(payload:dict,s:Session=Depends(db)):
    event=StudyEvent(event_type='quiz',score=int(payload.get('score',0)),total=int(payload.get('total',0)),details=json.dumps(payload.get('details',{}))); s.add(event); s.commit(); return {'saved':True}
@app.get('/api/analytics')
def analytics(s:Session=Depends(db)):
    docs=s.query(Document).count(); events=s.query(StudyEvent).all(); attempts=len(events); correct=sum(e.score or 0 for e in events); total=sum(e.total or 0 for e in events)
    return {'documents':docs,'quiz_attempts':attempts,'questions_answered':total,'accuracy':round(correct/total*100) if total else 0}
