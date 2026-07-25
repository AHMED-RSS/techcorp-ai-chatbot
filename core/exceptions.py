from __future__ import annotations


class TechCorpError(Exception):
    """Base exception for the local application."""


class ConfigurationError(TechCorpError):
    """Raised when application configuration is invalid."""


class OllamaConnectionError(TechCorpError):
    """Raised when the local Ollama service cannot be reached."""


class OllamaModelError(TechCorpError):
    """Raised when a local Ollama model fails."""


class ChatStorageError(TechCorpError):
    """Raised when local conversation storage fails."""


class FileProcessingError(TechCorpError):
    """Raised when a local file cannot be processed."""


class UnsupportedFileTypeError(FileProcessingError):
    """Raised when a file type is unsupported."""


class SkillError(TechCorpError):
    """Raised when a local skill cannot be managed."""


class ToolExecutionError(TechCorpError):
    """Raised when a local tool cannot be executed."""


class PlanningError(TechCorpError):
    """Raised when an agent plan cannot be created or managed."""


class AgentExecutionError(TechCorpError):
    """Raised when an agent plan cannot be executed."""


class CriticError(TechCorpError):
    """Raised when a response cannot be reviewed or revised."""


class MemoryServiceError(TechCorpError):
    """Raised when local memory or task state cannot be managed."""


class StudyError(TechCorpError):
    """Raised when local study material cannot be generated or managed."""


class WebSearchError(TechCorpError):
    """Raised when keyless web search cannot be completed."""