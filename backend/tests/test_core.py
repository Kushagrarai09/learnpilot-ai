import re
import pytest
from fastapi.testclient import TestClient
from app.ai import fallback_quiz, retrieve, split_chunks
from app.main import app

def test_split_chunks_normalizes_whitespace_and_preserves_page():
    chunks = split_chunks('Photosynthesis converts sunlight into energy. ' * 12, 3, size=120, overlap=20)
    assert chunks and all(chunk['page'] == 3 for chunk in chunks)
    assert all(not re.search(r'\s{2,}', chunk['text']) for chunk in chunks)

def test_split_chunks_rejects_invalid_overlap():
    with pytest.raises(ValueError): split_chunks('some text', 1, size=10, overlap=10)

def test_retrieval_ranks_relevant_chunk():
    docs = [{'filename':'notes.pdf','chunks':[{'text':'Photosynthesis converts light energy into chemical energy.','page':2},{'text':'The water cycle includes evaporation and precipitation.','page':3}]}]
    results = retrieve('photosynthesis light energy', docs)
    assert results and results[0]['page'] == 2

def test_fallback_quiz_has_four_options_and_answer():
    questions = fallback_quiz('Photosynthesis converts sunlight into chemical energy in green plants. ' * 3, 2)
    assert questions and all(len(q['options']) == 4 and q['answer'] in q['options'] for q in questions)

def test_health_endpoint():
    with TestClient(app) as client: response = client.get('/api/health')
    assert response.status_code == 200 and response.json()['status'] == 'ok'

def test_documents_endpoint_requires_authentication():
    with TestClient(app) as client: response = client.get('/api/documents')
    assert response.status_code == 401
