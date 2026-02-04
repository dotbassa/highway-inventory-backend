from pydantic import BaseModel, Field
from typing import List, TypeVar, Generic, Optional


T = TypeVar("T")


class PaginatedResponse(
    BaseModel,
    Generic[T],
):
    total: int = Field(
        ...,
        description="Total number of items",
    )
    items: List[T] = Field(
        ...,
        description="List of items in the current page",
    )
    page: int = Field(
        default=1,
        description="Current page number",
    )
    per_page: int = Field(
        default=100,
        description="Number of items per page",
    )
    has_more: bool = Field(
        default=False,
        description="Whether there are more items available",
    )

    @classmethod
    def create_unpaginated(
        cls,
        items: List[T],
        total: Optional[int] = None,
    ):
        """Helper method to create a response for endpoints that don't use pagination"""
        actual_total = total if total is not None else len(items)
        return cls(
            total=actual_total,
            items=items,
            page=1,
            per_page=actual_total if actual_total > 0 else 100,
            has_more=False,
        )

    @classmethod
    def create_paginated(cls, items: List[T], total: int, page: int, per_page: int):
        """Helper method to create a response for endpoints that use pagination"""
        has_more = (page * per_page) < total
        return cls(
            total=total,
            items=items,
            page=page,
            per_page=per_page,
            has_more=has_more,
        )
