# C:\spritle-bot\backend\models.py
from pydantic import BaseModel, Field
from typing import Optional

class QuoteDetails(BaseModel):
    client_name: Optional[str] = Field(None, description="The name of the client asking for a quote.")
    client_email: Optional[str] = Field(None, description="A valid email address of the client.")
    requirements: Optional[str] = Field(None, description="Detailed summary of what services or features they need.")
    estimated_budget: Optional[str] = Field(None, description="Any budget mentioned by the client.")
    is_complete: bool = Field(False, description="Set to True only if client_name, client_email, and requirements are all present.")