"""Structured outputs shared by the real LLM and the offline mock."""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class Route(BaseModel):
    intent: Literal["travel", "chat"] = Field(
        description="'travel' if the user wants a trip planned or changed (including follow-ups and "
                    "answers to trip questions); 'chat' for greetings and general questions.")
    proceed_with_assumptions: bool = Field(
        default=False, description="True only if the user explicitly said to go ahead / assume / use defaults.")
    origin: Optional[str] = Field(default=None, description="Starting city, only if the user said it.")
    origin_country: Optional[str] = Field(default=None, description="Country of the starting city.")
    origin_iata: Optional[str] = Field(default=None, description="IATA code of the origin's main airport, if confident.")
    destination: Optional[str] = Field(default=None, description="Destination city/region/country.")
    destination_country: Optional[str] = Field(default=None, description="Country of the destination.")
    destination_iata: Optional[str] = Field(default=None, description="IATA code of the destination's main airport, if confident.")
    days: Optional[int] = Field(default=None, description="Trip length in days, only if stated.")
    travellers: Optional[int] = Field(default=None, description="Number of people, only if stated.")
    budget_inr: Optional[int] = Field(default=None, description="Budget in INR, only if stated (1 lakh = 100000).")
    budget_is_per_person: Optional[bool] = Field(default=None, description="True only if the user said per person.")
    start_date: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD), only if stated.")


class DayPlan(BaseModel):
    day: int
    base_region: str = Field(description="Region id where the traveller sleeps that night.")
    activities: list[str] = Field(description="Place ids from the provided list.")
    note: str = Field(default="", description="One short sentence on pacing/logistics. No prices, flights or new facts.")


class CostItem(BaseModel):
    item: str
    unit_inr: int
    qty: int
    per_person: bool


class Plan(BaseModel):
    days: list[DayPlan]
    estimated_costs: list[CostItem] = Field(default_factory=list,
                                            description="Only when no price data is provided.")


class PlaceCandidate(BaseModel):
    name: str = Field(description="Attraction name exactly as written in the search result.")
    source: int = Field(description="Number of the search result that mentions it.")
    type: str = Field(default="sight", description="e.g. heritage, beach, museum, market, nature, viewpoint")


class PlaceList(BaseModel):
    places: list[PlaceCandidate]
