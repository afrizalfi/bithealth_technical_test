# main.py

import os
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, Filter, FieldCondition, MatchValue
import numpy as np
import time
import random
import json
import logging

global_app = FastAPI(title="Messy LangGraph + Qdrant API", version="0.1")
global_qdrant_client = None
global_workflow = None
global_embedding_dim = 384  # Using all-MiniLM-L6-v2 dimension
global_collection_name = "messy_documents"
global_state_store = {}  # Simulating persistent state poorly

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("messy_app")

class DocumentInput(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None

class QueryInput(BaseModel):
    query: str
    top_k: int = 5

class WorkflowResult(BaseModel):
    initial_query: str
    retrieved_docs: List[Dict[str, Any]]
    final_answer: str
    processing_time: float

# Embedding function 
def generate_embedding(text: str) -> List[float]:
    # In real life, you'd use a proper model like sentence-transformers
    # Here we fake it with random numbers seeded by text length for "determinism"
    random.seed(hash(text) % (10 ** 9))
    return [random.random() for _ in range(global_embedding_dim)]

# Qdrant setup function
def setup_qdrant():
    global global_qdrant_client
    if global_qdrant_client is None:
        # Try to connect to Qdrant - assume it's running locally
        try:
            global_qdrant_client = QdrantClient(host="localhost", port=6334)
            logger.info("Connected to Qdrant")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            global_qdrant_client = QdrantClient(":memory:")
            logger.info("Using in-memory Qdrant (probably won't work well)")

    # Create collection if it doesn't exist
    try:
        global_qdrant_client.get_collection(global_collection_name)
    except Exception:
        global_qdrant_client.create_collection(
            collection_name=global_collection_name,
            vectors_config=VectorParams(size=global_embedding_dim, distance=Distance.COSINE)
        )
        logger.info(f"Created collection {global_collection_name}")

# State dictionary for LangGraph
def create_initial_state(query: str) -> Dict[str, Any]:
    return {
        "query": query,
        "retrieved_docs": [],
        "final_answer": "",
        "processing_steps": [],
        "error": None
    }

# LangGraph node functions
def retrieve_documents_node(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state["query"]
    try:
        query_vector = generate_embedding(query)
        search_result = global_qdrant_client.search(
            collection_name=global_collection_name,
            query_vector=query_vector,
            limit=5
        )
        docs = []
        for hit in search_result:
            docs.append({
                "id": hit.id,
                "content": hit.payload.get("content", ""),
                "metadata": hit.payload.get("metadata", {}),
                "score": hit.score
            })
        state["retrieved_docs"] = docs
        state["processing_steps"].append("Retrieved documents from Qdrant")
    except Exception as e:
        state["error"] = f"Retrieval failed: {str(e)}"
        logger.error(state["error"])
    return state

def generate_answer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    if state["error"]:
        state["final_answer"] = f"Error occurred: {state['error']}"
        return state
    
    docs = state["retrieved_docs"]
    if not docs:
        state["final_answer"] = "No relevant documents found."
        return state
    
    # Super naive answer generation
    top_doc = docs[0]["content"]
    state["final_answer"] = f"Based on the document: {top_doc[:200]}..."  # Truncate for sanity
    state["processing_steps"].append("Generated final answer")
    return state

def should_retry_node(state: Dict[str, Any]) -> str:
    return "generate_answer"

def build_workflow():
    global global_workflow
    workflow = StateGraph(dict)  
    
    # Add nodes (procedures)
    workflow.add_node("retrieve", retrieve_documents_node)
    workflow.add_node("generate_answer", generate_answer_node)
    
    # Set entry point
    workflow.set_entry_point("retrieve")
    
    # Add edges
    workflow.add_edge("retrieve", "generate_answer")
    workflow.add_edge("generate_answer", END)
    
    # Compile - this is the runnable workflow
    global_workflow = workflow.compile()

# FastAPI startup event - set up everything here
@global_app.on_event("startup")
async def startup_event():
    setup_qdrant()
    build_workflow()
    logger.info("Messy application started!")

# FastAPI routes 
@global_app.post("/ingest")
async def ingest_document(doc: DocumentInput, background_tasks: BackgroundTasks):
    try:
        # Generate embedding
        embedding = generate_embedding(doc.content)
        
        # Create point ID
        point_id = str(uuid.uuid4())
        
        # Prepare payload
        payload = {
            "content": doc.content,
            "metadata": doc.metadata or {},
            "ingested_at": datetime.utcnow().isoformat()
        }
        
        # Upsert to Qdrant
        global_qdrant_client.upsert(
            collection_name=global_collection_name,
            points=[PointStruct(id=point_id, vector=embedding, payload=payload)]
        )
        
        global_state_store[point_id] = payload
        
        return {"id": point_id, "message": "Document ingested successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@global_app.post("/query", response_model=WorkflowResult)
async def query_documents(query_input: QueryInput):
    start_time = time.time()
    
    if global_workflow is None:
        raise HTTPException(status_code=500, detail="Workflow not initialized")
    
    try:
        # Run the LangGraph workflow
        initial_state = create_initial_state(query_input.query)
        final_state = global_workflow.invoke(initial_state)
        
        processing_time = time.time() - start_time
        
        return WorkflowResult(
            initial_query=query_input.query,
            retrieved_docs=final_state["retrieved_docs"],
            final_answer=final_state["final_answer"],
            processing_time=processing_time
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

@global_app.get("/documents")
async def list_documents(limit: int = 10):
    try:
        # Scan collection
        points = global_qdrant_client.scroll(
            collection_name=global_collection_name,
            limit=limit
        )
        documents = []
        for point in points[0]:  # scroll returns tuple (points, next_offset)
            documents.append({
                "id": point.id,
                "content": point.payload.get("content", "")[:100] + "...",
                "metadata": point.payload.get("metadata", {})
            })
        return {"documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@global_app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    try:
        global_qdrant_client.delete(
            collection_name=global_collection_name,
            points_selector=[doc_id]
        )
        global_state_store.pop(doc_id, None)
        return {"message": f"Document {doc_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

@global_app.get("/health")
async def health_check():
    qdrant_healthy = False
    try:
        global_qdrant_client.get_collection(global_collection_name)
        qdrant_healthy = True
    except:
        pass
    
    return {
        "status": "healthy" if qdrant_healthy and global_workflow else "unhealthy",
        "qdrant": "connected" if qdrant_healthy else "disconnected",
        "workflow": "ready" if global_workflow else "not ready",
        "documents_in_memory": len(global_state_store)
    }

@global_app.get("/debug/state")
async def debug_state():
    return {
        "global_state_store_keys": list(global_state_store.keys()),
        "collection_name": global_collection_name,
        "embedding_dim": global_embedding_dim
    }

@global_app.get("/chaos")
async def chaos_mode():
    await asyncio.sleep(random.uniform(0.1, 2.0))
    return {
        "message": "Chaos mode activated!",
        "random_number": random.randint(1, 100),
        "timestamp": datetime.utcnow().isoformat()
    }

@global_app.post("/batch_ingest")
async def batch_ingest(documents: List[DocumentInput]):
    results = []
    for doc in documents:
        try:
            embedding = generate_embedding(doc.content)
            point_id = str(uuid.uuid4())
            payload = {
                "content": doc.content,
                "metadata": doc.metadata or {},
                "ingested_at": datetime.utcnow().isoformat()
            }
            global_qdrant_client.upsert(
                collection_name=global_collection_name,
                points=[PointStruct(id=point_id, vector=embedding, payload=payload)]
            )
            global_state_store[point_id] = payload
            results.append({"id": point_id, "status": "success"})
        except Exception as e:
            results.append({"status": "error", "error": str(e)})
    
    return {"results": results}

messy_counter = 0

@global_app.get("/counter")
async def get_counter():
    global messy_counter
    messy_counter += 1
    return {"counter": messy_counter}