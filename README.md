# TechCorp AI

TechCorp AI is a local-first agentic AI workspace built with Streamlit, Ollama and ChromaDB.

All model inference and embedding generation run through locally installed Ollama models. The optional Web mode uses keyless DDGS retrieval, while answer generation remains local.

## Features

- Local Ollama chat
- Persistent conversations
- PDF, DOCX, PPTX, XLSX, CSV, text, code, image-metadata and ZIP parsing
- Persistent ChromaDB document retrieval
- Local skills
- Local tools
- Automatic routing
- Multi-step planning
- Sequential plan execution
- Independent critic and answer revision
- Persistent global and chat memory
- Persistent task snapshots
- Study summaries
- Revision notes
- Flashcards
- Quizzes
- Advanced chat attachments
- Normal, Focused and Deep Think modes
- Optional keyless web search
- Local diagnostic and readiness reports

## Requirements

- Windows, macOS or Linux
- Python 3.11 or newer
- `uv`
- Ollama
- A local chat model
- A local embedding model

The default model configuration used during development is:

```text
llama3.2:latest
nomic-embed-text:latest