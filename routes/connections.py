"""LDAP connection management routes."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from ldap3 import Server, Connection

from utils import templates
from utils.auth import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/connections", response_class=HTMLResponse)
def connections_form(request: Request) -> HTMLResponse:
    """Render the LDAP connection form."""
    return templates.TemplateResponse(request, "connections.html")


@router.post("/connections", response_class=HTMLResponse)
def test_connection(
    request: Request,
    server: str = Form(...),
    port: int = Form(389),
    user_dn: str = Form(...),
    password: str = Form(...),
    base_dn: str = Form(...),
) -> HTMLResponse:
    """Attempt to connect to the LDAP server and report the result."""
    try:
        srv = Server(server, port=port)
        conn = Connection(srv, user=user_dn, password=password, auto_bind=True)
        conn.search(base_dn, "(objectClass=*)", attributes=["cn"])
        conn.unbind()
        return templates.TemplateResponse(
            request,
            "connections.html",
            {"success": "Bağlantı başarılı"},
        )
    except Exception as exc:  # pragma: no cover - network failures
        return templates.TemplateResponse(
            request,
            "connections.html",
            {"error": str(exc)},
            status_code=400,
        )


__all__ = ["router"]
