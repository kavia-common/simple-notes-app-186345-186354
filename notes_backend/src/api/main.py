from typing import Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator


# PUBLIC_INTERFACE
class NoteBase(BaseModel):
    """Base schema for a Note containing common fields."""

    title: str = Field(..., description="The title of the note")
    content: str = Field(..., description="The main content of the note")

    # Validate non-empty strings for title/content after trimming whitespace
    @field_validator("title", "content")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("must be a string")
        if v.strip() == "":
            raise ValueError("must not be empty")
        return v.strip()


# PUBLIC_INTERFACE
class NoteCreate(NoteBase):
    """Schema for creating a new Note."""
    pass


# PUBLIC_INTERFACE
class NoteUpdate(BaseModel):
    """Schema for updating an existing Note; both fields optional but must be non-empty if provided."""

    title: Optional[str] = Field(None, description="Updated title of the note")
    content: Optional[str] = Field(None, description="Updated content of the note")

    @field_validator("title", "content")
    @classmethod
    def not_empty_when_present(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("must be a string")
        if v.strip() == "":
            raise ValueError("must not be empty")
        return v.strip()


# PUBLIC_INTERFACE
class Note(NoteBase):
    """Note model returned by the API, including the generated ID."""
    id: UUID = Field(..., description="Unique identifier for the note")


app = FastAPI(
    title="Simple Notes Backend",
    description="FastAPI backend for a simple notes app using in-memory storage. Provides CRUD endpoints for notes.",
    version="0.1.0",
    openapi_tags=[
        {"name": "Health", "description": "Service health and status"},
        {"name": "Notes", "description": "CRUD operations for notes"},
    ],
)

# Permissive CORS for simplicity (development only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend origin(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory "database" of notes. Keyed by UUID.
NOTES_STORE: Dict[UUID, Note] = {}


@app.get("/", tags=["Health"], summary="Health Check")
def health_check():
    """
    Health check endpoint.

    Returns:
        JSON message indicating the service is healthy.
    """
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.get(
    "/notes",
    response_model=List[Note],
    tags=["Notes"],
    summary="List all notes",
    description="Retrieve the list of all notes currently stored in memory.",
)
def list_notes() -> List[Note]:
    """
    List all notes in the in-memory store.

    Returns:
        List[Note]: All notes.
    """
    return list(NOTES_STORE.values())


# PUBLIC_INTERFACE
@app.post(
    "/notes",
    response_model=Note,
    status_code=201,
    tags=["Notes"],
    summary="Create a new note",
    description="Create a new note with a non-empty title and content.",
)
def create_note(payload: NoteCreate) -> Note:
    """
    Create a new note.

    Parameters:
        payload (NoteCreate): The note data containing title and content.

    Returns:
        Note: The newly created note including its generated ID.
    """
    note_id = uuid4()
    note = Note(id=note_id, title=payload.title, content=payload.content)
    NOTES_STORE[note_id] = note
    return note


# PUBLIC_INTERFACE
@app.get(
    "/notes/{note_id}",
    response_model=Note,
    tags=["Notes"],
    summary="Get a note by ID",
    description="Retrieve a single note by its UUID.",
)
def get_note(
    note_id: UUID = Path(..., description="The UUID of the note to retrieve")
) -> Note:
    """
    Get a single note by its ID.

    Parameters:
        note_id (UUID): The ID of the note.

    Returns:
        Note: The note with the specified ID.

    Raises:
        HTTPException: 404 if not found.
    """
    note = NOTES_STORE.get(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


# PUBLIC_INTERFACE
@app.put(
    "/notes/{note_id}",
    response_model=Note,
    tags=["Notes"],
    summary="Update a note by ID",
    description="Update an existing note. The payload may include title and/or content; each must be non-empty if provided.",
)
def update_note(
    payload: NoteUpdate,
    note_id: UUID = Path(..., description="The UUID of the note to update"),
) -> Note:
    """
    Update an existing note.

    Parameters:
        note_id (UUID): The ID of the note to update.
        payload (NoteUpdate): Fields to update (title and/or content).

    Returns:
        Note: The updated note.

    Raises:
        HTTPException: 404 if the note is not found.
    """
    existing = NOTES_STORE.get(note_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")

    updated = existing.model_copy(update=payload.model_dump(exclude_unset=True))
    NOTES_STORE[note_id] = updated
    return updated


# PUBLIC_INTERFACE
@app.delete(
    "/notes/{note_id}",
    status_code=204,
    tags=["Notes"],
    summary="Delete a note by ID",
    description="Delete a note from the in-memory store by its UUID.",
)
def delete_note(
    note_id: UUID = Path(..., description="The UUID of the note to delete")
) -> None:
    """
    Delete a note by its ID.

    Parameters:
        note_id (UUID): The ID of the note to delete.

    Returns:
        None: 204 No Content on success.

    Raises:
        HTTPException: 404 if the note is not found.
    """
    if note_id not in NOTES_STORE:
        raise HTTPException(status_code=404, detail="Note not found")
    del NOTES_STORE[note_id]
    return None


# Optional: allow running directly with uvicorn for local dev
# This block is not used by the platform which likely runs uvicorn separately,
# but documents the required port (3001).
if __name__ == "__main__":
    import uvicorn

    # Run on port 3001 as required
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=3001, reload=True)
