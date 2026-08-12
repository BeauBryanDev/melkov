from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas.chat import ChatRequest, ChatResponse, ToolCallLog
from app.agent.orchestrator import build_melkov_agent

app = FastAPI(title="Melkov - Art Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restringe esto al dominio de tu frontend en produccion
    allow_methods=["*"],
    allow_headers=["*"],
)

# Historial de chat en memoria por session_id. Para produccion, cambia esto
# por Redis o una tabla de sesiones - se pierde al reiniciar el proceso.
_sessions: dict[str, list] = {}


@app.get("/health")
def health():
    return {"status": "ok", "agent": "melkov"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        history = _sessions.setdefault(req.session_id, [])

        executor, artifacts = build_melkov_agent(current_image_b64=req.image_base64)
        result = executor.invoke({"input": req.message, "chat_history": history})

        reply = result["output"]

        # Actualiza el historial de la sesion
        history.append(("human", req.message))
        history.append(("ai", reply))

        tools_used = [
            ToolCallLog(tool=step[0].tool, input_summary=str(step[0].tool_input)[:120])
            for step in result.get("intermediate_steps", [])
        ]

        return ChatResponse(
            reply=reply,
            session_id=req.session_id,
            tools_used=tools_used,
            generated_image_base64=artifacts.get("generated_image_b64"),
            met_results=artifacts.get("met_results"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
