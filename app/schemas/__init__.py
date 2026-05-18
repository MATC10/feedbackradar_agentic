"""
Schemas Pydantic para validación y serialización.

Este módulo exporta todos los schemas de dominio del proyecto.
"""

# Feedback schemas
from app.schemas.feedback_schema import (
    FeedbackBase,
    FeedbackCreate,
    FeedbackInDB,
    FeedbackResponse,
    FeedbackUploadResponse,
)

# Insight schemas
from app.schemas.insight_schema import (
    PriorityLevel,
    InsightBase,
    InsightCreate,
    InsightInDB,
    InsightResponse,
    InsightsListResponse,
)

# Action schemas
from app.schemas.action_schema import (
    ActionPriority,
    ActionStatus,
    ActionItemBase,
    ActionItemCreate,
    ActionItemInDB,
    ActionItemUpdate,
    ActionItemResponse,
    ActionsListResponse,
)

# Analysis schemas
from app.schemas.analysis_schema import (
    AnalysisStatus,
    ThemeSummary,
    AnalysisRunBase,
    AnalysisRunCreate,
    AnalysisRunInDB,
    AnalysisRunResponse,
    AnalysisRunDetailResponse,
    AnalysisRunStartResponse,
    AnalysisListResponse,
)

# Agent analysis schemas
from app.schemas.analysis import (
    DetectedTheme,
    ThemeDiscoveryResponse,
    Evidence,
    PrioritizedTheme,
    Recommendation,
)

__all__ = [
    # Feedback
    "FeedbackBase",
    "FeedbackCreate",
    "FeedbackInDB",
    "FeedbackResponse",
    "FeedbackUploadResponse",
    # Insight
    "PriorityLevel",
    "InsightBase",
    "InsightCreate",
    "InsightInDB",
    "InsightResponse",
    "InsightsListResponse",
    # Action
    "ActionPriority",
    "ActionStatus",
    "ActionItemBase",
    "ActionItemCreate",
    "ActionItemInDB",
    "ActionItemUpdate",
    "ActionItemResponse",
    "ActionsListResponse",
    # Analysis
    "AnalysisStatus",
    "ThemeSummary",
    "AnalysisRunBase",
    "AnalysisRunCreate",
    "AnalysisRunInDB",
    "AnalysisRunResponse",
    "AnalysisRunDetailResponse",
    "AnalysisRunStartResponse",
    "AnalysisListResponse",
    # Agent analysis
    "DetectedTheme",
    "ThemeDiscoveryResponse",
    "Evidence",
    "PrioritizedTheme",
    "Recommendation",
]
