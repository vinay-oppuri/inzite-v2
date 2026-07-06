from typing import List
from pydantic import BaseModel, Field

class Competitor(BaseModel):
    name: str
    domain: str
    summary: str
    website: str


class CompetitorList(BaseModel):
    competitors: List[Competitor]