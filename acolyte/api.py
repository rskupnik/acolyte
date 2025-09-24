from __future__ import annotations
from fastapi import FastAPI, Body
from pydantic import BaseModel

app = FastAPI(title="acolyte", version="0.1.0")

class EchoIn(BaseModel):
    message: str

class EchoOut(BaseModel):
    echoed: str

@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}

@app.post("/echo", response_model=EchoOut)
def echo(payload: EchoIn = Body(...)) -> EchoOut:
    # Put your business logic here
    return EchoOut(echoed=payload.message)
