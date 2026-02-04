from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel


class Submolt(BaseModel):
    id: UUID
    name: str


class Author(BaseModel):
    id: UUID
    name: str


class PostContent(BaseModel):
    id: UUID
    title: str
    content: str
    url: str | None
    upvotes: int
    downvotes: int
    comment_count: int
    created_at: datetime
    submolt: Submolt
    author: Author


class Post(BaseModel):
    success: bool
    post: PostContent


class Comment(BaseModel):
    id: UUID
    content: str
    upvotes: int
    downvotes: int
    created_at: datetime
    author: Author
    replies: list[Self]


class PostComment(BaseModel):
    success: bool
    post_id: UUID
    post_title: str
    count: int
    comments: list[Comment]


class Feed(BaseModel):
    success: bool
    posts: list[PostContent]
