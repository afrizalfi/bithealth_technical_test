# Migration Strategy

## Overview

This migration strategy outlines incremental steps to improve the codebase without breaking functionality. Each step addresses the key considerations from the README:
1. Introducing interfaces for external services
2. Decoupling web logic from business logic
3. Centralizing configuration
4. Enabling unit and integration testing

## Phase 1: Centralizing Configuration (1-2 days)

### Addresses: Centralizing configuration

### What to do

1. Create `config.py`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    embedding_dim: int = 384
    collection_name: str = "messy_documents"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

2. Update `main.py` to use settings:
```python
from config import settings

# Replace hardcoded values
test_client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
global_embedding_dim = settings.embedding_dim
global_collection_name = settings.collection_name
```

3. Create `.env.example` file with all configuration options

### Why
- All configuration in one place
- Can deploy to different environments
- No code changes needed for config
- More secure

### Test
- App works with default values
- App works with .env file
- Can change config without code changes

---

## Phase 2: Decoupling Web Logic from Business Logic (2-3 days)

### Addresses: Decoupling web logic from business logic

### What to do

1. Create `services.py` with business logic:
```python
class DocumentService:
    def __init__(self, qdrant_client, collection_name, embedding_dim):
        self.client = qdrant_client
        self.collection = collection_name
        self.embedding_dim = embedding_dim
    
    def ingest(self, content: str, metadata: dict) -> str:
        # Business logic here
        embedding = self._generate_embedding(content)
        point_id = str(uuid.uuid4())
        payload = {"content": content, "metadata": metadata, "ingested_at": ...}
        self.client.upsert(
            collection_name=self.collection,
            points=[PointStruct(id=point_id, vector=embedding, payload=payload)]
        )
        return point_id
    
    def _generate_embedding(self, text: str) -> List[float]:
        random.seed(hash(text) % (10 ** 9))
        return [random.random() for _ in range(self.embedding_dim)]
```

2. In startup, create service and store in `app.state`:
```python
@global_app.on_event("startup")
async def startup_event():
    setup_qdrant()
    build_workflow()
    
    # Create service with business logic
    document_service = DocumentService(
        global_qdrant_client,
        global_collection_name,
        global_embedding_dim
    )
    global_app.state.document_service = document_service
```

3. Update routes to be thin controllers (web logic only):
```python
@global_app.post("/ingest")
async def ingest_document(doc: DocumentInput):
    # Web logic: get service, call business logic, return response
    service = global_app.state.document_service
    point_id = service.ingest(doc.content, doc.metadata)
    return {"id": point_id, "message": "Document ingested successfully"}
```

### Why
- Routes only handle HTTP (web logic)
- Business logic in services (testable)
- Clear separation of concerns
- Less duplication

### Test
- All endpoints work the same
- Service can be tested independently with mock client
- Routes are thin controllers that delegate to services

---

## Phase 3: Remove Globals and Enable Testing (2-3 days)

### Addresses: Enabling unit and integration testing

### What to do

1. Pass dependencies as function parameters:
```python
# Before - cannot test
def generate_embedding(text: str) -> List[float]:
    return [random.random() for _ in range(global_embedding_dim)]

# After - can test
def generate_embedding(text: str, dimension: int) -> List[float]:
    return [random.random() for _ in range(dimension)]
```

2. Update services to accept dependencies:
```python
class DocumentService:
    def __init__(self, qdrant_client, collection_name, embedding_dim):
        # Dependencies injected, not from globals
        self.client = qdrant_client
        self.collection = collection_name
        self.embedding_dim = embedding_dim
```

3. Use dependency injection in routes:
```python
def get_document_service():
    return global_app.state.document_service

@global_app.post("/ingest")
async def ingest_document(
    doc: DocumentInput,
    service = Depends(get_document_service)  # Injected
):
    return service.ingest(doc.content, doc.metadata)
```

4. Remove global variable declarations

### Why
- Dependencies are explicit
- Can test functions easily (pass mocks)
- Can test services without real Qdrant
- No hidden dependencies

### Test
- Unit test service with mock client:
```python
def test_document_service():
    mock_client = Mock()
    service = DocumentService(mock_client, "test_collection", 384)
    doc_id = service.ingest("test", {})
    assert doc_id is not None
    mock_client.upsert.assert_called_once()
```

- Integration test routes with test client
- All functions work with parameters

---

## Phase 4: Introducing Interfaces for External Services (2-3 days)

### Addresses: Introducing interfaces for external services

### What to do

1. Create `repository.py` with interface:
```python
class VectorRepository:
    """Interface for vector database operations"""
    def upsert(self, point_id: str, vector: List[float], payload: dict):
        raise NotImplementedError
    
    def query_points(self, query_vector: List[float], limit: int):
        raise NotImplementedError
    
    def scroll(self, limit: int):
        raise NotImplementedError
    
    def delete(self, point_id: str):
        raise NotImplementedError

class QdrantRepository(VectorRepository):
    """Qdrant implementation of VectorRepository"""
    def __init__(self, client, collection_name):
        self.client = client
        self.collection = collection_name
    
    def upsert(self, point_id: str, vector: List[float], payload: dict):
        self.client.upsert(
            collection_name=self.collection,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)]
        )
    
    def query_points(self, query_vector: List[float], limit: int):
        return self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=limit
        )
    
    # Implement other methods...
```

2. Update services to use interface:
```python
class DocumentService:
    def __init__(self, vector_repo: VectorRepository, embedding_dim: int):
        # Uses interface, not concrete QdrantClient
        self.vector_repo = vector_repo
        self.embedding_dim = embedding_dim
    
    def ingest(self, content: str, metadata: dict) -> str:
        embedding = self._generate_embedding(content)
        point_id = str(uuid.uuid4())
        payload = {"content": content, "metadata": metadata}
        self.vector_repo.upsert(point_id, embedding, payload)  # Interface method
        return point_id
```

3. Initialize repository in startup:
```python
vector_repo = QdrantRepository(global_qdrant_client, global_collection_name)
document_service = DocumentService(vector_repo, global_embedding_dim)
```

### Why
- Can swap vector database (implement interface for Pinecone, etc.)
- Can mock repository for testing
- Services don't depend on concrete QdrantClient
- Better separation of concerns

### Test
- Works with QdrantRepository
- Can create MockRepository for unit tests:
```python
class MockRepository(VectorRepository):
    def upsert(self, point_id, vector, payload):
        self.upsert_calls.append((point_id, vector, payload))
    
    def query_points(self, query_vector, limit):
        return MockSearchResult()

# Test with mock
mock_repo = MockRepository()
service = DocumentService(mock_repo, 384)
service.ingest("test", {})
assert len(mock_repo.upsert_calls) == 1
```

---

## Phase 5: Organize Files (1 day)

### What to do

1. Create folder structure:
```
app/
├── config.py          # Configuration
├── repository.py      # Interfaces and implementations
├── services.py        # Business logic
├── routes.py         # Web logic (routes)
└── main.py           # App initialization
```

2. Move code to appropriate files:
   - Configuration → `config.py`
   - Repository interface/implementation → `repository.py`
   - Business logic → `services.py`
   - Routes → `routes.py`
   - App setup → `main.py`

3. Update imports

### Why
- Clear organization
- Easy to find code
- Professional structure
- Each file has single responsibility

### Test
- App still works
- All imports correct
- Code is organized

---

## How Each Phase Addresses README Considerations

### 1. Introducing interfaces for external services
- **Phase 4:** Creates VectorRepository interface
- Services use interface, not concrete QdrantClient
- Can swap implementations easily
- Can mock for testing

### 2. Decoupling web logic from business logic
- **Phase 2:** Extracts business logic to services
- Routes become thin controllers
- Business logic separated and testable
- Clear boundaries

### 3. Centralizing configuration
- **Phase 1:** All config in Settings class
- Environment variables support
- No hardcoded values
- Single source of truth

### 4. Enabling unit and integration testing
- **Phase 3:** Removes globals, uses dependency injection
- Functions accept dependencies as parameters
- Can pass mocks for testing
- Services testable independently

---

## Timeline

**Week 1:**
- Day 1-2: Configuration (Addresses: Centralizing configuration)
- Day 3-5: Extract Services (Addresses: Decoupling web from business logic)

**Week 2:**
- Day 1-3: Remove Globals (Addresses: Enabling testing)
- Day 4-5: Add Repository Interface (Addresses: Interfaces for external services)

**Week 3:**
- Day 1: Organize Files
- Day 2-5: Testing and cleanup

## Success Criteria

After migration:

1. **Interfaces for external services:** VectorRepository interface, can swap implementations
2. **Web logic decoupled:** Routes are thin, business logic in services
3. **Configuration centralized:** All config in Settings, environment-based
4. **Testing enabled:** Can unit test services, can integration test routes
5. **No globals:** All dependencies explicit
6. **Organized:** Code in logical files

This approach balances practical improvements with production readiness, ensuring each phase delivers value while maintaining system stability.
