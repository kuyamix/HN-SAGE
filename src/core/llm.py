# src/core/llm.py
import json
import httpx
from src.config import (
    LLM_PROVIDER, OLLAMA_URL, OLLAMA_MODEL, 
    LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
)

def build_prompt(query, hits):
    context_parts = []
    for i, h in enumerate(hits):
        block = [f"[{i+1}] Title: {h['title']}", f"By: {h['by']} · {h['score']} points"]
        if h["matched_doc"]:
            block.append(f"Matched Passage:\n{h['matched_doc'][:1500]}")
        context_parts.append("\n".join(block))
    context = "\n\n---\n\n".join(context_parts)

    return f"""You are a helpful AI assistant analyzing tech discussions.
Use the provided context to answer the question.
If the context does not contain the answer, say "I don't have enough information in the current stories to answer that."
Do NOT invent facts. 
Only cite sources [n] that are directly relevant to the user's question. Ignore irrelevant context.

Context:
{context}

Question: {query}

Answer:"""

async def stream_llm_response(query, hits):
    prompt = build_prompt(query, hits)
    yield json.dumps({"type": "sources", "data": hits}) + "\n"
    
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            if LLM_PROVIDER == "ollama":
                # --- LOCAL OLLAMA STREAM ---
                async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json={
                    "model": OLLAMA_MODEL, 
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True, 
                    "options": {"num_predict": 512, "temperature": 0.3}
                }) as r:
                    async for line in r.aiter_lines():
                        if not line.strip(): continue
                        try:
                            obj = json.loads(line)
                            chunk = obj.get("message", {}).get("content", "")
                            if chunk: yield json.dumps({"type": "token", "data": chunk}) + "\n"
                        except: pass
                        
            elif LLM_PROVIDER == "openai":
                # --- DEEPSEEK / OPENAI CLOUD STREAM ---
                headers = {
                    "Authorization": f"Bearer {LLM_API_KEY}",
                    "Content-Type": "application/json"
                }
                async with client.stream("POST", f"{LLM_BASE_URL}/chat/completions", 
                    headers=headers,
                    json={
                        "model": LLM_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": True,
                        "temperature": 0.3
                    }
                ) as r:
                    if r.status_code != 200:
                        error_text = await r.aread()
                        yield json.dumps({"type": "error", "data": f"API Error {r.status_code}: {error_text.decode()}"}) + "\n"
                        return
                        
                    async for line in r.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]": break
                            try:
                                obj = json.loads(data_str)
                                chunk = obj["choices"][0]["delta"].get("content", "")
                                if chunk: yield json.dumps({"type": "token", "data": chunk}) + "\n"
                            except: pass
                            
    except Exception as e:
        yield json.dumps({"type": "error", "data": str(e)}) + "\n"
    
    yield json.dumps({"type": "done"}) + "\n"