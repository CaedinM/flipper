from pydantic import BaseModel, Field

class ReleaseCandidate(BaseModel):
    product_name: str = Field(..., description="Name of the product")
    brand: Optional[str] = Field(None, description="Brand if known")
    release_date: date = Field(..., description="Date product releases")
    retail_price: Optional[int] = Field(..., description="Expected retail price of product")
    retailers: Optional[List[str]] = Field(..., description="Retailers confirmed to be selling the item")
    seed_sources: List[str] = Field(..., description="URLs confirming the release")

class ScoutOutput(BaseModel):
    candidates: List[ReleaseCandidate]

class ReleaseItems(ReleaseCandidate):
    resale_estimate: int = Field(..., description="Estimated resale value")
    confidence_score: float = Field(..., ge=0, le=100, description="Level of confidence from 0-100 that resale_estimate is correct")

class AnalystOutput(BaseModel):
    items: List[ReleaseItems]