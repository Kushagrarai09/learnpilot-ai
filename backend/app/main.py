import json
import os
from pathlib import Path
import fitz
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import vector_store
from .ai import fallback_quiz, llm, retrieve, split_chunks
from .auth import get_current_user
from .config import settings
from .database import Base, engine, SessionLocal
from .models import Document, StudyEvent, User
from .schemas import ChatRequest, GenerateRequest, QuizResultRequest, RegisterRequest, LoginRequest, TokenResponse
from .security import create_access_token, hash_password, verify_password

Base.metadata.create_all(bind=engine)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
app = FastAPI(title=settings.app_name, version='1.1.0', description='AI-powered personal learning and teaching assistant')
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(',') if x.strip()], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

def db():
    session = SessionLocal()
    try: yield session
    finally: session.close()

def owned_documents(session: Session, user_id: int, document_ids: list[int] | None = None):
    query = session.query(Document).filter(Document.user_id == user_id)
    if document_ids: query = query.filter(Document.id.in_(document_ids))
    return query

def as_doc(document: Document):
    chunks = []
    try:
        with fitz.open(document.stored_path) as pdf:
            for page_number, page in enumerate(pdf, start=1): chunks.extend(split_chunks(page.get_text(), page_number))
    except Exception as exc: raise HTTPException(500, 'The stored PDF could not be read.') from exc
    return {'id': document.id, 'filename': document.filename, 'page_count': document.page_count, 'chunks': chunks}

@app.on_event('startup')
def bootstrap_legacy_user():
    with SessionLocal() as session:
        legacy = session.query(User).filter(User.email == settings.legacy_owner_email).first()
        if legacy is None:
            legacy = User(email=settings.legacy_owner_email, password_hash=hash_password(os.urandom(32).hex()), is_active=True)
            session.add(legacy); session.flush()
        session.query(Document).filter(Document.user_id.is_(None)).update({Document.user_id: legacy.id}, synchronize_session=False)
        session.query(StudyEvent).filter(StudyEvent.user_id.is_(None)).update({StudyEvent.user_id: legacy.id}, synchronize_session=False)
        session.commit()

@app.get('/api/health')
def health(): return {'status':'ok','service':'LearnPilot AI','llm_configured':bool(settings.llm_api_key)}

@app.post('/api/auth/register', response_model=TokenResponse)
def register(payload: RegisterRequest, session: Session = Depends(db)):
    email = str(payload.email).lower().strip()
    if session.query(User).filter(User.email == email).first(): raise HTTPException(409, 'An account with this email already exists.')
    user = User(email=email, password_hash=hash_password(payload.password), is_active=True)
    session.add(user); session.commit(); session.refresh(user)
    return {'access_token':create_access_token(user.id),'token_type':'bearer','user':{'id':user.id,'email':user.email}}

@app.post('/api/auth/login', response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(db)):
    user = session.query(User).filter(User.email == str(payload.email).lower().strip()).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash): raise HTTPException(401, 'Invalid email or password.')
    return {'access_token':create_access_token(user.id),'token_type':'bearer','user':{'id':user.id,'email':user.email}}

@app.get('/api/auth/me')
def me(user: User = Depends(get_current_user)): return {'id':user.id,'email':user.email}

@app.get('/api/documents')
def list_documents(session: Session = Depends(db), user: User = Depends(get_current_user)):
    return [{'id':d.id,'filename':d.filename,'page_count':d.page_count,'status':d.status,'created_at':str(d.created_at)} for d in owned_documents(session,user.id).order_by(Document.id.desc()).all()]

@app.post('/api/documents/upload')
async def upload_document(file: UploadFile = File(...), session: Session = Depends(db), user: User = Depends(get_current_user)):
    if not file.filename or not file.filename.lower().endswith('.pdf'): raise HTTPException(400,'Only PDF files are supported.')
    data = await file.read()
    if not data or len(data) > settings.max_upload_mb * 1024 * 1024: raise HTTPException(413,f'PDF must be non-empty and no larger than {settings.max_upload_mb} MB.')
    if not data.startswith(b'%PDF-'): raise HTTPException(400,'The uploaded file does not have a valid PDF signature.')
    path = Path(settings.upload_dir) / f"{os.urandom(8).hex()}_{Path(file.filename).name.replace(' ','_')}"; path.write_bytes(data)
    try:
        with fitz.open(path) as pdf:
            page_count = len(pdf)
            if page_count < 1 or page_count > settings.max_pdf_pages: raise HTTPException(413,f'PDF must contain between 1 and {settings.max_pdf_pages} pages.')
            pages = [page.get_text() for page in pdf]
    except HTTPException: path.unlink(missing_ok=True); raise
    except Exception as exc: path.unlink(missing_ok=True); raise HTTPException(400,'Could not read this PDF. It may be encrypted or damaged.') from exc
    extracted = '\n'.join(f'\n[Page {i+1}]\n{text}' for i,text in enumerate(pages))
    chunks = [chunk for number,page in enumerate(pages,start=1) for chunk in split_chunks(page,number)]
    if not extracted.strip() or not chunks: path.unlink(missing_ok=True); raise HTTPException(422,'No selectable text found. OCR is not enabled.')
    document = Document(filename=file.filename,stored_path=str(path),page_count=page_count,extracted_text=extracted,user_id=user.id,status='pending')
    session.add(document); session.commit(); session.refresh(document)
    try: vector_store.index_document(document.id,document.filename,chunks); document.status='ready'; document.index_error=None
    except Exception as exc: document.status='index_failed'; document.index_error=str(exc)[:1000]
    session.commit()
    return {'id':document.id,'filename':document.filename,'page_count':page_count,'status':document.status,'message':'Document saved. Retry indexing if status is index_failed.'}

@app.post('/api/documents/{doc_id}/retry-index')
def retry_document_index(doc_id:int,session:Session=Depends(db),user:User=Depends(get_current_user)):
    document = owned_documents(session,user.id).filter(Document.id==doc_id).first()
    if not document: raise HTTPException(404,'Document not found.')
    try:
        with fitz.open(document.stored_path) as pdf: chunks=[chunk for number,page in enumerate(pdf,start=1) for chunk in split_chunks(page.get_text(),number)]
        if not chunks: raise ValueError('No selectable text found.')
        vector_store.index_document(document.id,document.filename,chunks); document.status='ready'; document.index_error=None; session.commit()
        return {'id':doc_id,'status':'ready'}
    except Exception as exc:
        document.status='index_failed'; document.index_error=str(exc)[:1000]; session.commit()
        raise HTTPException(503,'Indexing failed. The document is retained; retry later.') from exc

@app.delete('/api/documents/{doc_id}')
def delete_document(doc_id:int,session:Session=Depends(db),user:User=Depends(get_current_user)):
    document=owned_documents(session,user.id).filter(Document.id==doc_id).first()
    if not document: raise HTTPException(404,'Document not found.')
    try: vector_store.delete_document(doc_id)
    except Exception: pass
    Path(document.stored_path).unlink(missing_ok=True); session.delete(document); session.commit(); return {'deleted':doc_id}

@app.post('/api/chat')
async def chat(req:ChatRequest,session:Session=Depends(db),user:User=Depends(get_current_user)):
    docs=[as_doc(d) for d in owned_documents(session,user.id,req.document_ids).all()]
    if not docs: raise HTTPException(400,'Upload or select at least one study document first.')
    try: hits=vector_store.search(req.question,[d['id'] for d in docs],limit=5)
    except Exception: hits=retrieve(req.question,docs)
    if not hits: return {'answer':'I could not find relevant information in the selected material.','citations':[],'mode':'grounded-retrieval'}
    context='\n\n'.join(f"[{h['filename']}, page {h['page']}] {h['text']}" for h in hits)
    prompt=f'Answer using ONLY these excerpts. If unsupported, say so. Cite claims as [filename, p. N].\n\n{context}\n\nQUESTION: {req.question}'
    try: answer=await llm(prompt,'You are a precise tutor. Explain clearly and never invent facts or citations.')
    except Exception: answer=None
    if not answer: answer='Relevant passages from your material:\n\n'+'\n\n'.join(f"**{h['filename']} — page {h['page']}**\n{h['text'][:700]}" for h in hits[:3])+'\n\nDemo retrieval mode: configure an LLM API key for synthesized answers.'
    return {'answer':answer,'citations':[{'filename':h['filename'],'page':h['page']} for h in hits],'mode':'llm-rag' if settings.llm_api_key else 'retrieval-demo'}

def document_text(req,session,user):
    docs=owned_documents(session,user.id,req.document_ids).all()
    if not docs: raise HTTPException(400,'Upload a document first.')
    return '\n'.join(d.extracted_text for d in docs),docs

@app.post('/api/quiz')
async def quiz(req:GenerateRequest,session:Session=Depends(db),user:User=Depends(get_current_user)):
    text,docs=document_text(req,session,user)
    prompt=f'Create {req.count} {req.difficulty} multiple-choice questions from this material. Return ONLY JSON array with question, options (4 strings), answer, explanation.\n{text[:14000]}'
    try: raw=await llm(prompt,'You are an assessment designer. Questions must be answerable from the provided content.')
    except Exception: raw=None
    try: questions=json.loads(raw[raw.find('['):raw.rfind(']')+1]) if raw else []
    except (ValueError,TypeError): questions=[]
    if not isinstance(questions,list): questions=[]
    questions=[q for q in questions if isinstance(q,dict) and isinstance(q.get('question'),str) and isinstance(q.get('options'),list) and len(q['options'])==4 and q.get('answer') in q['options']]
    if not questions: questions=fallback_quiz(text,req.count)
    return {'questions':questions[:req.count],'source_documents':[d.filename for d in docs]}

@app.post('/api/flashcards')
async def flashcards(req:GenerateRequest,session:Session=Depends(db),user:User=Depends(get_current_user)):
    text,_=document_text(req,session,user)
    try: raw=await llm(f'Create {req.count} concise study flashcards. Return ONLY JSON array with front and back.\n{text[:14000]}','You create accurate active-recall flashcards.')
    except Exception: raw=None
    try: cards=json.loads(raw[raw.find('['):raw.rfind(']')+1]) if raw else []
    except (ValueError,TypeError): cards=[]
    if not isinstance(cards,list): cards=[]
    cards=[c for c in cards if isinstance(c,dict) and isinstance(c.get('front'),str) and isinstance(c.get('back'),str)]
    if not cards: cards=[{'front':q['question'],'back':q['answer']+'. '+q['explanation']} for q in fallback_quiz(text,req.count)]
    return {'flashcards':cards[:req.count]}

@app.post('/api/roadmap')
async def roadmap(req:GenerateRequest,session:Session=Depends(db),user:User=Depends(get_current_user)):
    text,_=document_text(req,session,user)
    try: raw=await llm(f'Create a practical 7-day learning roadmap. Return JSON array with day, focus, activities, outcome.\n{text[:10000]}','You are a learning coach.')
    except Exception: raw=None
    try: plan=json.loads(raw[raw.find('['):raw.rfind(']')+1]) if raw else None
    except (ValueError,TypeError): plan=None
    if not isinstance(plan,list):
        heads=[x.strip() for x in text.split('.') if len(x.strip())>35][:7]
        plan=[{'day':f'Day {i+1}','focus':heads[i][:75] if i<len(heads) else 'Review and consolidate','activities':['Read the relevant section','Write a short summary','Test yourself with 5 questions'],'outcome':'Explain the concept without notes'} for i in range(7)]
    return {'roadmap':plan}

@app.post('/api/teacher/lesson-plan')
async def lesson_plan(req:GenerateRequest,session:Session=Depends(db),user:User=Depends(get_current_user)):
    material,_=document_text(req,session,user)
    try: result=await llm('Create a teacher-ready 45-minute lesson plan and worksheet. Include objectives, timing, activities, assessment, and five questions.\n'+material[:12000],'You are an experienced teacher creating classroom-ready materials.')
    except Exception: result=None
    if not result: result='# 45-minute lesson plan\n\n- 0–5 min: Starter and prior-knowledge check\n- 5–15 min: Explain key concepts\n- 15–25 min: Guided example\n- 25–35 min: Pair activity\n- 35–42 min: Independent practice\n- 42–45 min: Exit ticket\n\n## Worksheet\n1. Define the central concept.\n2. List two supporting ideas.\n3. Explain how they connect.\n4. Apply one idea to an example.\n5. Write one question you still have.'
    return {'content':result}

@app.post('/api/events/quiz-result')
def quiz_result(payload:QuizResultRequest,session:Session=Depends(db),user:User=Depends(get_current_user)):
    if payload.score>payload.total: raise HTTPException(422,'Score cannot exceed total questions.')
    event=StudyEvent(user_id=user.id,event_type='quiz',score=payload.score,total=payload.total,details=json.dumps(payload.details))
    session.add(event);session.commit();return {'saved':True}

@app.get('/api/analytics')
def analytics(session:Session=Depends(db),user:User=Depends(get_current_user)):
    doc_count=owned_documents(session,user.id).count();events=session.query(StudyEvent).filter(StudyEvent.user_id==user.id).all()
    attempts=len(events);correct=sum(e.score or 0 for e in events);total=sum(e.total or 0 for e in events)
    return {'documents':doc_count,'quiz_attempts':attempts,'questions_answered':total,'accuracy':round(correct/total*100) if total else 0}
