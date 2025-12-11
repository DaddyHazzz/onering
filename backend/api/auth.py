from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class SignupIn(BaseModel):
    email: str
    password: str

@router.post("/signup")
async def signup(data: SignupIn):
    # TODO: wire to real DB / Clerk / auth provider
    if not data.email or not data.password:
        raise HTTPException(status_code=400, detail="email+password required")
    return {"status": "ok", "email": data.email}
