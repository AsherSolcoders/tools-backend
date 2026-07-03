"""Site-wide custom code (header / body / footer), à la the WordPress
"Insert Headers and Footers" plugin. Stored as key/value settings.

- Public GET is consumed by the frontend layout to inject the snippets on every page.
- Admin GET/PUT let the super-admin edit them.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_super_admin
from app.database import get_db
from app.models import User
from app.models.settings import Setting

router = APIRouter(tags=["site"])

_HEADER = "site_header_code"
_BODY = "site_body_code"
_FOOTER = "site_footer_code"
_KEYS = (_HEADER, _BODY, _FOOTER)


class SiteCode(BaseModel):
    header: str = ""
    body: str = ""
    footer: str = ""


def _read(db: Session) -> SiteCode:
    rows = {
        s.key: s.value
        for s in db.execute(select(Setting).where(Setting.key.in_(_KEYS))).scalars().all()
    }
    return SiteCode(
        header=rows.get(_HEADER) or "",
        body=rows.get(_BODY) or "",
        footer=rows.get(_FOOTER) or "",
    )


@router.get("/api/site-code", response_model=SiteCode)
def public_site_code(db: Session = Depends(get_db)):
    return _read(db)


@router.get("/api/admin/site-code", response_model=SiteCode)
def admin_get_site_code(db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    return _read(db)


@router.put("/api/admin/site-code", response_model=SiteCode)
def admin_put_site_code(
    payload: SiteCode,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    values = {_HEADER: payload.header, _BODY: payload.body, _FOOTER: payload.footer}
    existing = {
        s.key: s
        for s in db.execute(select(Setting).where(Setting.key.in_(_KEYS))).scalars().all()
    }
    for key, value in values.items():
        if key in existing:
            existing[key].value = value
        else:
            db.add(Setting(key=key, value=value))
    db.commit()
    return _read(db)
