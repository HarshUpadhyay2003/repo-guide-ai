from typing import List
from pydantic import BaseModel, Field

class RepositoryMap(BaseModel):
    frontend: List[str] = Field(default_factory=list)
    backend: List[str] = Field(default_factory=list)
    tests: List[str] = Field(default_factory=list)
    docs: List[str] = Field(default_factory=list)
    config: List[str] = Field(default_factory=list)
    scripts: List[str] = Field(default_factory=list)
    other: List[str] = Field(default_factory=list)