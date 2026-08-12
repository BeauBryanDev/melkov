from typing import Optional
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic

from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from app.agent.prompts import MELKOV_SYSTEM_PROMPT
from app.tools.vlm_describe import describe_artwork
from app.tools.flux_generate import generate_artwork
from app.tools.met_search import search_met_artworks
from app.tools.rag_retriever import query_art_history
from app.utils.image_utils import base64_to_pil, pil_to_base64


def build_melkov_agent(current_image_b64: Optional[str] = None):
    """Construye un AgentExecutor de Melkov para un turno de conversacion.

    current_image_b64 (si existe) es la imagen subida por el usuario en este
    turno; se pasa por closure en vez de por el texto del LLM para no
    desperdiciar tokens ni arriesgar corrupcion de un base64 gigante.

    Devuelve (executor, artifacts): artifacts es un dict que las tools
    binarias (imagen generada, resultados MET) rellenan como side-channel,
    ya que el LLM solo devuelve texto.
    """
    artifacts = {"generated_image_b64": None, "met_results": None}

    @tool
    def describe_artwork_tool() -> str:
        """Describe artisticamente, estilo curador de museo, la imagen que el
        usuario acaba de subir en este turno. Usar SOLO si hay una imagen
        adjunta en el mensaje actual."""
        if not current_image_b64:
            return "No hay ninguna imagen adjunta en este turno para describir."
        image = base64_to_pil(current_image_b64)
        return describe_artwork(image)

    @tool
    def generate_artwork_tool(prompt: str) -> str:
        """Genera una imagen artistica nueva a partir de una descripcion en
        texto. La imagen resultante queda disponible como artefacto adjunto
        de la respuesta, no hace falta describirla en el texto de vuelta."""
        image = generate_artwork(prompt)
        artifacts["generated_image_b64"] = pil_to_base64(image)
        return f"Imagen generada para el prompt: '{prompt}'."

    @tool
    def search_met_artworks_tool(query: str) -> str:
        """Busca obras reales en la coleccion del Metropolitan Museum of Art
        (MET) por estilo, artista, movimiento o periodo."""
        results = search_met_artworks(query)
        artifacts["met_results"] = results
        if not results:
            return f"No se encontraron obras en el MET para '{query}'."
        titles = "; ".join(
            f"{r['title']} ({r['artist'] or 'autor desconocido'})" for r in results
        )
        return f"Se encontraron {len(results)} obras: {titles}"

    @tool
    def query_art_history_tool(question: str) -> str:
        """Consulta la base de conocimiento de historia del arte (RAG) para
        fundamentar respuestas conceptuales o historicas con precision."""
        return query_art_history(question)

    tools = [
        describe_artwork_tool,
        generate_artwork_tool,
        search_met_artworks_tool,
        query_art_history_tool,
    ]

    # Cambia el modelo/proveedor aqui si tu orquestador no es Claude.
    llm = ChatAnthropic(
        model=ANTHROPIC_MODEL, api_key=ANTHROPIC_API_KEY, temperature=0.6
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", MELKOV_SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

    return executor, artifacts
