"""Shared Pydantic schemas mirrored from server for client-side use."""
from typing import Literal, Optional
from pydantic import BaseModel, Field

# Re-export server schemas for client use
from server.dm.schemas import DMRuling, DMPromptPacket, DMRulingSubmission

__all__ = ["DMRuling", "DMPromptPacket", "DMRulingSubmission"]
