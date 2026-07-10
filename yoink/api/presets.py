import sqlite3

from fastapi import APIRouter, HTTPException

from .. import db
from ..models import PresetIn, PresetOut

router = APIRouter()


@router.get("/presets")
async def list_presets() -> list[PresetOut]:
    return [PresetOut.from_row(row) for row in db.list_presets()]


@router.post("/presets", status_code=201)
async def create_preset(preset: PresetIn) -> PresetOut:
    try:
        preset_id = db.create_preset(preset.name, preset.options.model_dump_json())
    except sqlite3.IntegrityError:
        raise HTTPException(409, f"a preset named {preset.name!r} already exists")
    return PresetOut.from_row(db.get_preset(preset_id))


@router.put("/presets/{preset_id}")
async def update_preset(preset_id: int, preset: PresetIn) -> PresetOut:
    try:
        if not db.update_preset(preset_id, preset.name, preset.options.model_dump_json()):
            raise HTTPException(404, "no such preset")
    except sqlite3.IntegrityError:
        raise HTTPException(409, f"a preset named {preset.name!r} already exists")
    return PresetOut.from_row(db.get_preset(preset_id))


@router.delete("/presets/{preset_id}")
async def delete_preset(preset_id: int) -> dict:
    if not db.delete_preset(preset_id):
        raise HTTPException(404, "no such preset")
    return {"ok": True}
