# OneRing LangGraph Skeleton

Drop-in LangGraph (agent orchestration) skeleton.

Purpose
- Provide a clear, testable structure for agent definitions, prompts, and workflows.
- Keep a single place for orchestration logic that the backend worker calls.

What you get
- `workflows.py` — example workflow pipeline connecting agents.
- `agents/` — individual agent modules (strategy, research, writer, posting, analytics).
- `prompts/` — human-editable prompt templates.
- `orchestrator.py` — small helper to run workflows from an RQ worker.
- `config.yaml` — central config for agent timeouts, model choices, and retry rules.

How to use
1. Implement small `run()` functions in each agent module (they are stubbed).
2. Call `orchestrator.run_workflow(prompt)` from your RQ job or FastAPI endpoint.
3. Replace placeholder model calls with your actual LLM client (Grok/Groq/Gemini).
