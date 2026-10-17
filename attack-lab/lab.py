"""Kavach Attack Lab — a demo-only dashboard that runs security checks against a RUNNING Kavach.

    uvicorn lab:app --host 127.0.0.1 --port 4000
    open http://127.0.0.1:4000

Every button sends a real HTTP request to Kavach (http://127.0.0.1:8000) and shows the real
answer. This server imports NO Kavach code and changes nothing in the project — it only talks
to Kavach over HTTP, the same way a browser or a website would.

DEMO ONLY. Do not expose outside a local demo.
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import attacks
import kavach_client as K

app = FastAPI(title="Kavach Attack Lab", docs_url=None, redoc_url=None)

STATIC = Path(__file__).parent / "static"


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/cards")
def cards():
    return {"cards": attacks.card_list(), "target": K.API, "origin": K.ORIGIN}


@app.get("/api/scenario")
def scenario():
    if not K.health():
        return JSONResponse(
            {"ready": False, "error": "Kavach backend is not reachable on http://127.0.0.1:8000. "
                                      "Start Kavach (start-all.bat) first, then reload this page."},
            status_code=200)
    try:
        attacks.SCN.setup()
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ready": False, "error": str(e)}, status_code=200)
    return attacks.SCN.status()


def _run(attack_id: str, legit: bool):
    if attack_id not in attacks.REGISTRY:
        raise HTTPException(404, "Unknown attack")
    try:
        return attacks.run(attack_id, legit=legit)
    except K.KavachDown as e:
        raise HTTPException(503, str(e))
    except Exception as e:  # noqa: BLE001  — surface the error on the card instead of crashing
        return {"outcome": "error", "verdict": f"The lab hit an error running this check: {e}",
                "steps": [{"title": "Lab error", "kind": "warn", "note": str(e)}], "legit": legit}


@app.post("/api/run/{attack_id}")
def run_attack(attack_id: str):
    return _run(attack_id, legit=False)


@app.post("/api/legit/{attack_id}")
def run_legit(attack_id: str):
    return _run(attack_id, legit=True)


app.mount("/static", StaticFiles(directory=STATIC), name="static")
