from typing import Optional, Literal
from pydantic import BaseModel

InventoryType = Literal['pc', 'license', 'accessory', 'stock']


class InventoryLogCreate(BaseModel):
    inventory_type: InventoryType
    inventory_id: int
    action: Literal['assign', 'return', 'move', 'relabel']
    changed_by: int
    old_user_id: Optional[int] = None
    new_user_id: Optional[int] = None
    old_location: Optional[str] = None
    new_location: Optional[str] = None
    old_inventory_no: Optional[str] = None
    new_inventory_no: Optional[str] = None
    note: Optional[str] = None
