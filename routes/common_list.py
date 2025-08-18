"""Common utilities for listing routes with filtering and pagination."""

from typing import Iterable
import math

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi_csrf_protect import CsrfProtect
from sqlalchemy import or_, String

from models import SessionLocal, User
from utils import templates, get_table_columns


def list_items(
    request: Request,
    Model,
    table_name: str,
    filter_fields: Iterable[str],
    template_name: str,
    items_key: str,
) -> HTMLResponse:
    """Render a filtered and paginated list for the given model.

    Args:
        request: Incoming request object.
        Model: SQLAlchemy model to query.
        table_name: Name of the table for context.
        filter_fields: Allowed fields for exact filtering.
        template_name: Template to render.
        items_key: Context key used for the list of items.
    """
    params = request.query_params
    q = params.get("q", "")
    request_filter_fields = params.getlist("filter_field")
    request_filter_values = params.getlist("filter_value")
    filter_field = request_filter_fields[0] if request_filter_fields else None
    filter_value = request_filter_values[0] if request_filter_values else None
    page = int(params.get("page", 1))
    per_page = int(params.get("per_page", 25))

    filters = []
    db = SessionLocal()
    try:
        query = db.query(Model)
        for field, value in zip(request_filter_fields, request_filter_values):
            if field in filter_fields and value and hasattr(Model, field):
                query = query.filter(getattr(Model, field) == value)
                filters.append({"field": field, "value": value})

        if q:
            search_conditions = []
            for column in Model.__table__.columns:
                if isinstance(column.type, String):
                    search_conditions.append(column.ilike(f"%{q}%"))
            if search_conditions:
                query = query.filter(or_(*search_conditions))

        total_count = query.count()
        total_pages = max(1, math.ceil(total_count / per_page))
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()
        users = db.query(User).all()
    finally:
        db.close()

    user_list = [
        {
            "id": u.id,
            "name": (f"{u.first_name or ''} {u.last_name or ''}".strip() or u.username),
        }
        for u in users
    ]

    context = {
        "request": request,
        "columns": get_table_columns(Model.__tablename__),
        "column_widths": {},
        "lookups": {},
        "offset": offset,
        "page": page,
        "total_pages": total_pages,
        "q": q,
        "per_page": per_page,
        "table_name": table_name,
        "filters": filters,
        "count": total_count,
        "filter_field": filter_field,
        "filter_value": filter_value,
        "users": user_list,
        "current_user_id": request.session.get("user_id"),
    }
    context[items_key] = items
    csrf_protect = CsrfProtect()
    token, signed = csrf_protect.generate_csrf_tokens()
    context["csrf_token"] = token
    response = templates.TemplateResponse(request, template_name, context)
    csrf_protect.set_csrf_cookie(signed, response)
    return response
