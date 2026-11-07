"""
Prática Avaliada 01 - Exercício 4
API REST de gerenciamento de usuários com FastAPI.

Como executar:
    pip install -r requirements.txt
    uvicorn main:app --reload

Documentação interativa (Swagger): http://127.0.0.1:8000/docs
"""

from typing import Annotated

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

app = FastAPI(
    title="API de Usuários",
    description="Prática Avaliada 01 - CRUD de usuários com armazenamento em memória.",
    version="1.0.0",
)

# ----------------
# Modelos Pydantic
# ----------------

# Removendo espaços nas pontas e exige entre 2 e 100 caracteres.
Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]


class UsuarioCreate(BaseModel):
    """Dados que o cliente envia para criar um usuário."""

    nome: Nome = Field(..., examples=["Nathan Garrett"])
    email: EmailStr = Field(..., examples=["nathangarrett@exemplo.com"])

class Usuario(UsuarioCreate):
    """Usuário completo, como armazenado e devolvido pela API (com id)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"id": 1, "nome": "Nathan Garrett", "email": "nathangarrett@exemplo.com"}
        }
    )

    id: int

# --------------------------------------------------------------------------
# Armazenamento em memória
# --------------------------------------------------------------------------

usuarios_db: list[Usuario] = []
proximo_id: int = 1

# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@app.post(
    "/usuarios",
    response_model=Usuario,
    status_code=status.HTTP_201_CREATED,
    summary="Criar usuário",
    responses={409: {"description": "E-mail já cadastrado"}},
)
def criar_usuario(dados: UsuarioCreate) -> Usuario:
    """Cria um novo usuário. O `id` é gerado pelo servidor."""
    global proximo_id

    # Regra de negócio: e-mail único.
    email_normalizado = dados.email.lower()
    if any(u.email.lower() == email_normalizado for u in usuarios_db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe um usuário cadastrado com o e-mail '{dados.email}'.",
        )

    usuario = Usuario(id=proximo_id, nome=dados.nome, email=dados.email)
    usuarios_db.append(usuario)
    proximo_id += 1
    return usuario


@app.get(
    "/usuarios",
    response_model=list[Usuario],
    summary="Listar usuários",
)
def listar_usuarios() -> list[Usuario]:
    """Retorna todos os usuários cadastrados (lista vazia se não houver nenhum)."""
    return usuarios_db