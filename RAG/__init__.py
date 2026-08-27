"""Art-history RAG pipeline for the Melkov agent.

The build phases (``audit_pdfs``, ``extract``, ``chunk``,
``colab_embed_ingest``, ``validate_retrieval``) are run as scripts from
inside this directory and import each other by bare module name.
``retrieval`` is the exception: it is also imported as ``RAG.retrieval``
by the FastAPI backend, which is why this package marker exists.
"""
