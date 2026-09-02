from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .evaluator import (
    PolicyError,
    evaluate,
    finalize_opa,
    load_policy,
    opa_input,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
POLICY_PATH = Path(os.getenv("SPP_POLICY", REPO_ROOT / "examples" / "hospital.yaml"))
ENGINE = os.getenv("SPP_ENGINE", "local").lower()
OPA_URL = os.getenv("SPP_OPA_URL", "http://localhost:8181")

policy = load_policy(POLICY_PATH)
app = FastAPI(title="PlaceAuth SPP 0.1 Reference Policy Server", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "spp_version": "0.1",
        "engine": ENGINE,
        "policy_id": policy["policy_id"],
        "policy_version": policy["policy_version"],
    }


@app.post("/v1/decision")
async def decision(request: dict[str, Any]) -> dict[str, Any]:
    try:
        if ENGINE == "local":
            return evaluate(policy, request)
        if ENGINE != "opa":
            raise HTTPException(status_code=500, detail=f"Unsupported SPP_ENGINE: {ENGINE}")

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{OPA_URL.rstrip('/')}/v1/data/spp/core",
                json={"input": opa_input(policy, request)},
            )
            response.raise_for_status()
        body = response.json()
        if "result" not in body:
            raise HTTPException(status_code=502, detail="OPA returned no decision")
        return finalize_opa(policy, request, body["result"])
    except PolicyError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"OPA request failed: {error}") from error


def main() -> None:
    uvicorn.run("spp.server:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
