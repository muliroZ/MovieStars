"""Respostas de erro da API em português (constituição, seção 5.1)."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Validadores próprios já escrevem a mensagem em português; o Pydantic só a prefixa.
_VALUE_ERROR_PREFIX = "Value error, "


def translate_validation_error(error: dict[str, Any]) -> str:
    """Mensagem em português para um erro de validação do Pydantic."""

    error_type = error["type"]
    ctx = error.get("ctx", {})

    if error_type == "missing":
        return "Campo obrigatório."
    if error_type == "string_too_short":
        min_length = ctx.get("min_length", 1)
        return (
            "Campo obrigatório."
            if min_length == 1
            else f"Deve ter pelo menos {min_length} caracteres."
        )
    if error_type == "string_too_long":
        return f"Deve ter no máximo {ctx.get('max_length')} caracteres."
    if error_type in ("greater_than_equal", "greater_than"):
        return f"Deve ser no mínimo {ctx.get('ge', ctx.get('gt'))}."
    if error_type in ("less_than_equal", "less_than"):
        return f"Deve ser no máximo {ctx.get('le', ctx.get('lt'))}."
    if error_type in ("int_parsing", "int_type", "int_from_float"):
        return "Deve ser um número inteiro."
    if error_type.startswith("date_"):
        return "Data inválida."
    if error_type == "literal_error":
        return "Valor inválido."
    if error_type == "string_pattern_mismatch":
        return "Formato inválido."
    if error_type == "string_type":
        return "Deve ser um texto."
    if error_type == "list_type":
        return "Deve ser uma lista."
    if error_type == "json_invalid":
        return "JSON inválido."
    if error_type == "value_error":
        return str(error["msg"]).removeprefix(_VALUE_ERROR_PREFIX)
    return "Valor inválido."


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """422 no formato do FastAPI (`detail[].loc/msg/type`), com mensagens em português."""

    del request
    detail = [
        {"loc": list(error["loc"]), "msg": translate_validation_error(error), "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": detail})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_error_handler)
