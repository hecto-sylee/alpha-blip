"""Shop (포인트로 옷 구매). 장착은 pet.appearance_json.equipped (pets PATCH)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import User, UserItem
from ..schemas import ShopBuyReq, ShopItemRes, ShopRes
from ..shop_catalog import SHOP_ITEMS
from ..utils.events import log_event

router = APIRouter(tags=["shop"])


def _owned_keys(db: Session, user_id: str) -> set[str]:
    return {ui.item_key for ui in db.query(UserItem).filter(UserItem.user_id == user_id).all()}


@router.get("/shop", response_model=ShopRes)
def get_shop(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ShopRes:
    owned = _owned_keys(db, user.id)
    items = [
        ShopItemRes(key=k, name=v["name"], slot=v["slot"], cost=v["cost"], owned=k in owned)
        for k, v in SHOP_ITEMS.items()
    ]
    return ShopRes(points=user.points or 0, items=items)


@router.post("/shop/buy", response_model=ShopRes)
def buy(body: ShopBuyReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ShopRes:
    item = SHOP_ITEMS.get(body.item_key)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    owned = _owned_keys(db, user.id)
    if body.item_key not in owned:
        if (user.points or 0) < item["cost"]:
            raise HTTPException(status_code=400, detail="포인트가 부족해요")
        user.points = (user.points or 0) - item["cost"]
        db.add(UserItem(user_id=user.id, item_key=body.item_key))
        log_event(db, "shop_buy", user_id=user.id, payload={"item": body.item_key})
        db.commit()
        owned = _owned_keys(db, user.id)
    items = [
        ShopItemRes(key=k, name=v["name"], slot=v["slot"], cost=v["cost"], owned=k in owned)
        for k, v in SHOP_ITEMS.items()
    ]
    return ShopRes(points=user.points or 0, items=items)
