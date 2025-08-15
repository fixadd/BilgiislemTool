from fastapi import APIRouter
from typing import Optional
from pydantic import BaseModel

from logs import InventoryLogCreate
from services.log_service import add_inventory_log, get_inventory_logs

router = APIRouter(prefix="/logs", tags=["Inventory Logs"])

@router.get("")
def list_logs(type: Optional[str] = None, id: Optional[int] = None, limit: int = 200, offset: int = 0):
    return get_inventory_logs(inventory_type=type, inventory_id=id, limit=limit, offset=offset)

@router.post("")
def create_log(payload: InventoryLogCreate):
    log_id = add_inventory_log(payload)
    return {"ok": True, "id": log_id}

class AssignRequest(BaseModel):
    inventory_type: str
    inventory_id: int
    to_user_id: int
    changed_by: int
    note: Optional[str] = None

@router.post("/assign")
def assign_item(req: AssignRequest):
    old_user_id = None
    add_inventory_log(
        InventoryLogCreate(
            inventory_type=req.inventory_type,
            inventory_id=req.inventory_id,
            action="assign",
            changed_by=req.changed_by,
            old_user_id=old_user_id,
            new_user_id=req.to_user_id,
            note=req.note,
        )
    )
    return {"ok": True}

class ReturnRequest(BaseModel):
    inventory_type: str
    inventory_id: int
    from_user_id: int
    changed_by: int
    note: Optional[str] = None

@router.post("/return")
def return_item(req: ReturnRequest):
    add_inventory_log(
        InventoryLogCreate(
            inventory_type=req.inventory_type,
            inventory_id=req.inventory_id,
            action="return",
            changed_by=req.changed_by,
            old_user_id=req.from_user_id,
            new_user_id=None,
            note=req.note,
        )
    )
    return {"ok": True}

class MoveRequest(BaseModel):
    inventory_type: str
    inventory_id: int
    old_location: Optional[str]
    new_location: str
    changed_by: int
    note: Optional[str] = None

@router.post("/move")
def move_item(req: MoveRequest):
    add_inventory_log(
        InventoryLogCreate(
            inventory_type=req.inventory_type,
            inventory_id=req.inventory_id,
            action="move",
            changed_by=req.changed_by,
            old_location=req.old_location,
            new_location=req.new_location,
            note=req.note,
        )
    )
    return {"ok": True}

class RelabelRequest(BaseModel):
    inventory_type: str
    inventory_id: int
    old_label: str
    new_label: str
    changed_by: int
    note: Optional[str] = None

@router.post("/relabel")
def relabel_item(req: RelabelRequest):
    add_inventory_log(
        InventoryLogCreate(
            inventory_type=req.inventory_type,
            inventory_id=req.inventory_id,
            action="relabel",
            changed_by=req.changed_by,
            note=f"Label: {req.old_label} -> {req.new_label}",
        )
    )
    return {"ok": True}
