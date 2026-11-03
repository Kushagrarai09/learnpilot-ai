"""Persistent Chroma vector index with Sentence Transformers embeddings."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent/'chroma_data'
_collection=None
_model=None
def _resources():
    global _collection,_model
    if _collection is None or _model is None:
        import chromadb
        from sentence_transformers import SentenceTransformer
        client=chromadb.PersistentClient(path=str(ROOT))
        _collection=client.get_or_create_collection('learnpilot_chunks',metadata={'hnsw:space':'cosine'})
        _model=SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    return _collection,_model
def index_document(document_id:int,filename:str,chunks:list[dict]):
    collection,model=_resources()
    if not chunks:return
    ids=[f'doc-{document_id}-page-{c["page"]}-chunk-{i}' for i,c in enumerate(chunks)]
    embeddings=model.encode([c['text'] for c in chunks],normalize_embeddings=True).tolist()
    collection.upsert(ids=ids,documents=[c['text'] for c in chunks],embeddings=embeddings,metadatas=[{'document_id':document_id,'filename':filename,'page':c['page']} for c in chunks])
def search(question:str,document_ids:list[int],limit:int=5):
    collection,model=_resources()
    result=collection.query(query_embeddings=[model.encode(question,normalize_embeddings=True).tolist()],n_results=limit,where={'document_id':{'$in':document_ids}} if document_ids else None,include=['documents','metadatas','distances'])
    return [{'text':t,'filename':m['filename'],'page':m['page'],'score':1-d} for t,m,d in zip(result['documents'][0],result['metadatas'][0],result['distances'][0])]
def delete_document(document_id:int):
    collection,_=_resources()
    collection.delete(where={'document_id':document_id})
