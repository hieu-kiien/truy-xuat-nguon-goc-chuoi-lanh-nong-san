from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def get_items():
    """Lấy danh sách items — ví dụ minh họa."""
    return [{"id": 1, "name": "Item mẫu"}]


@router.get("/{item_id}")
def get_item(item_id: int):
    """Lấy chi tiết một item theo ID."""
    return {"id": item_id, "name": f"Item số {item_id}"}
