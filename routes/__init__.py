from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def root() -> str:
    return "<h1>Welcome to BilgiislemTool</h1>"


@router.get("/login", response_class=HTMLResponse)
def login_page() -> str:
    return "<h1>Login Page</h1>"


@router.get("/stock", response_class=HTMLResponse)
def stock_page() -> str:
    return "<h1>Stock Page</h1>"


@router.get("/printer", response_class=HTMLResponse)
def printer_page() -> str:
    return "<h1>Printer Page</h1>"


@router.get("/ping")
def ping():
    return {"status": "ok"}
