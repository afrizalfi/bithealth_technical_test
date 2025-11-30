# Design Smells and Refactoring Priorities

## Design Smells

### 1. Global State Everywhere

**Problem:**
6 global variables used throughout the code:
- `global_qdrant_client`
- `global_workflow`
- `global_embedding_dim`
- `global_collection_name`
- `global_state_store`
- `messy_counter`

**Impact:**
- Cannot test functions without setting up globals
- Race conditions (counter, state_store)
- Dependencies are hidden

**Example:**
```python
def generate_embedding(text: str) -> List[float]:
    return [random.random() for _ in range(global_embedding_dim)]  # Hidden dependency
```

---

### 2. Hardcoded Configuration

**Problem:**
Configuration values hardcoded in code:
- `host="localhost"`, `port=6333`
- `embedding_dim = 384`
- `collection_name = "messy_documents"`

**Impact:**
- Cannot deploy to different environments
- Must edit code to change config
- Security risk

**Example:**
```python
QdrantClient(host="localhost", port=6333)  # Hardcoded
```

---

### 3. Everything in One File

**Problem:**
All code in `main.py` (297 lines): routes, business logic, data access, workflow nodes.

**Impact:**
- Hard to navigate
- Changes affect unrelated code
- No separation of concerns

---

### 4. Tight Coupling

**Problem:**
Routes directly access `global_qdrant_client`. No abstraction layer.

**Impact:**
- Cannot swap vector database
- Cannot test routes without real Qdrant
- Changes require updates in many places

**Example:**
```python
@global_app.post("/ingest")
async def ingest_document(doc: DocumentInput):
    global_qdrant_client.upsert(...)  # Direct access, no abstraction
```

---

### 5. Code Duplication

**Problem:**
Ingestion logic duplicated in `/ingest` and `/batch_ingest` endpoints.

**Impact:**
- Bugs must be fixed in multiple places
- Inconsistent behavior risk

---

### 6. Race Conditions

**Problem:**
Shared global state accessed without synchronization:
- `messy_counter += 1` - not atomic
- `global_state_store[point_id] = payload` - not thread-safe

**Impact:**
- Data corruption in concurrent requests
- Incorrect values under load

---

## Refactoring Priorities

### Priority 1: Configuration (Do First)

**Why:**
- Required for deployment
- Quick win (1-2 days)
- Enables other improvements

**What:**
- Move hardcoded values to environment variables
- Create Settings class

**Impact:**
- Can deploy to dev/staging/prod
- No code changes for config

---

### Priority 2: Extract Services (Do Second)

**Why:**
- Separates business logic from routes
- Makes code testable
- Reduces duplication

**What:**
- Create DocumentService
- Move business logic out of routes
- Store services in app.state

**Impact:**
- Routes become thin controllers
- Business logic can be tested
- Less code duplication

---

### Priority 3: Remove Globals (Do Third)

**Why:**
- Makes dependencies explicit
- Enables proper testing
- Fixes race conditions

**What:**
- Pass dependencies as parameters
- Remove global variables
- Use dependency injection

**Impact:**
- Functions are testable
- No hidden dependencies
- No race conditions

---

### Priority 4: Add Repository (Do Fourth)

**Why:**
- Can swap vector database
- Makes testing easier
- Better separation

**What:**
- Create VectorRepository interface
- Implement QdrantRepository
- Update services to use repository

**Impact:**
- Can swap implementations
- Can mock for testing
- More flexible

---

### Priority 5: Organize Files (Do Last)

**Why:**
- Better code organization
- Easier to navigate
- Professional structure

**What:**
- Create folder structure
- Move code to appropriate files
- Update imports

**Impact:**
- Clear organization
- Easy to find code
- Better maintainability

---

## Summary

**Critical Issues:**
1. Global state - prevents testing, causes race conditions
2. Hardcoded config - blocks deployment
3. Tight coupling - hard to change or test

**Fix Order:**
1. Configuration (enables deployment)
2. Services (enables testing)
3. Remove globals (fixes race conditions)
4. Repository (enables flexibility)
5. Organize (polish)

Simple, practical, production-ready.
