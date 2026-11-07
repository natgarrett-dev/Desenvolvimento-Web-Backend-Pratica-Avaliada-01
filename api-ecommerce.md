# API REST — E-commerce Simples (Produtos e Pedidos)

**Versão:** v1 · **Base URL:** `https://api.exemplo.com/api/v1` · **Formato:** JSON (`application/json`)

## 1. Modelo de dados

**Produto**

| Campo | Tipo | Observação |
|---|---|---|
| `id` | inteiro | gerado pelo servidor |
| `nome` | string | obrigatório |
| `preco` | decimal | maior que 0 |
| `categoria` | string | obrigatório |
| `estoque` | inteiro | maior ou igual a 0 |

**Pedido**

| Campo | Tipo | Observação |
|---|---|---|
| `id` | inteiro | gerado pelo servidor |
| `produto_id` | inteiro | deve referenciar um produto existente |
| `quantidade` | inteiro | maior que 0 |
| `total` | decimal | calculado pelo servidor (`preco × quantidade`) |
| `status` | string | `pendente`, `pago`, `enviado`, `entregue`, `cancelado` |

---

## 2. Design dos endpoints REST

Princípios aplicados: recursos como **substantivos no plural**, verbos HTTP para as ações, URLs hierárquicas, versionamento na URL, códigos de status semânticos e filtros/paginação via *query string*.

### Produtos

| Método | Endpoint | Descrição | Sucesso | Erros |
|---|---|---|---|---|
| `GET` | `/produtos` | Lista produtos (filtros: `?categoria=`, paginação: `?pagina=1&limite=20`) | 200 | 400 |
| `POST` | `/produtos` | Cria um produto | 201 | 400, 409, 422 |
| `GET` | `/produtos/{id}` | Detalha um produto | 200 | 404 |
| `PUT` | `/produtos/{id}` | Substitui um produto por completo | 200 | 404, 422 |
| `PATCH` | `/produtos/{id}` | Atualiza campos parcialmente | 200 | 404, 422 |
| `DELETE` | `/produtos/{id}` | Remove um produto | 204 | 404, 409 |
| `GET` | `/produtos/{id}/pedidos` | Lista os pedidos de um produto | 200 | 404 |

### Pedidos

| Método | Endpoint | Descrição | Sucesso | Erros |
|---|---|---|---|---|
| `GET` | `/pedidos` | Lista pedidos (filtro: `?status=`) | 200 | 400 |
| `POST` | `/pedidos` | Cria um pedido (calcula `total` e baixa o estoque) | 201 | 404, 409, 422 |
| `GET` | `/pedidos/{id}` | Detalha um pedido | 200 | 404 |
| `PATCH` | `/pedidos/{id}` | Atualiza o status (ex.: `pendente` → `pago`) | 200 | 404, 409, 422 |
| `POST` | `/pedidos/{id}/cancelar` | Cancela o pedido e devolve o estoque | 200 | 404, 409 |

> **Nota de design:** o cancelamento é modelado como uma *ação* (`POST .../cancelar`) e não como `DELETE`, pois o pedido continua existindo no histórico com status `cancelado`.

### Regras de negócio

- O `total` nunca é enviado pelo cliente; é calculado como `preco × quantidade`.
- Criar um pedido com `quantidade` maior que o `estoque` retorna **409 Conflict**.
- Transições de status válidas: `pendente → pago → enviado → entregue`; `pendente`/`pago → cancelado`.
- Um produto com pedidos associados não pode ser removido (409).

---

## 3. Exemplos completos de requisição/resposta

### Exemplo 1 — Criar um pedido (`POST /pedidos`)

**Requisição**

```http
POST /api/v1/pedidos HTTP/1.1
Host: api.exemplo.com
Content-Type: application/json
Accept: application/json
Authorization: Bearer eyJhbGciOi...

{
  "produto_id": 7,
  "quantidade": 2
}
```

**Resposta — `201 Created`**

```http
HTTP/1.1 201 Created
Content-Type: application/json
Location: /api/v1/pedidos/101

{
  "id": 101,
  "produto_id": 7,
  "quantidade": 2,
  "total": 299.80,
  "status": "pendente",
  "_links": {
    "self":     { "href": "/api/v1/pedidos/101", "method": "GET" },
    "produto":  { "href": "/api/v1/produtos/7", "method": "GET" },
    "pagar":    { "href": "/api/v1/pedidos/101", "method": "PATCH", "body": { "status": "pago" } },
    "cancelar": { "href": "/api/v1/pedidos/101/cancelar", "method": "POST" },
    "colecao":  { "href": "/api/v1/pedidos", "method": "GET" }
  }
}
```

### Exemplo 2 — Consultar um produto (`GET /produtos/{id}`)

**Requisição**

```http
GET /api/v1/produtos/7 HTTP/1.1
Host: api.exemplo.com
Accept: application/json
```

**Resposta — `200 OK`**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 7,
  "nome": "Fone de Ouvido Bluetooth",
  "preco": 149.90,
  "categoria": "eletronicos",
  "estoque": 38,
  "_links": {
    "self":      { "href": "/api/v1/produtos/7", "method": "GET" },
    "atualizar": { "href": "/api/v1/produtos/7", "method": "PUT" },
    "remover":   { "href": "/api/v1/produtos/7", "method": "DELETE" },
    "pedidos":   { "href": "/api/v1/produtos/7/pedidos", "method": "GET" },
    "comprar":   { "href": "/api/v1/pedidos", "method": "POST", "body": { "produto_id": 7, "quantidade": 1 } },
    "categoria": { "href": "/api/v1/produtos?categoria=eletronicos", "method": "GET" },
    "colecao":   { "href": "/api/v1/produtos", "method": "GET" }
  }
}
```

---

## 4. Implementação básica de HATEOAS

**HATEOAS** (*Hypermedia As The Engine Of Application State*) é a restrição REST em que cada resposta traz **links** que indicam ao cliente quais ações ele pode realizar a seguir. O cliente não precisa "conhecer" as URLs de antemão: ele as descobre pela resposta.

### Convenção adotada

Toda representação de recurso inclui um objeto `_links`, no qual cada chave é uma **relação** (`rel`) e o valor contém:

| Campo | Descrição |
|---|---|
| `href` | URL do recurso ou da ação |
| `method` | método HTTP a utilizar |

### Links condicionais ao estado

Os links refletem o **estado atual** do recurso. Por exemplo, num pedido:

| Status do pedido | Links disponíveis (além de `self`, `produto`, `colecao`) |
|---|---|
| `pendente` | `pagar`, `cancelar` |
| `pago` | `enviar`, `cancelar` |
| `enviado` | `entregar` |
| `entregue` / `cancelado` | nenhum (estado final) |

Exemplo — pedido já cancelado:

```json
{
  "id": 101,
  "produto_id": 7,
  "quantidade": 2,
  "total": 299.80,
  "status": "cancelado",
  "_links": {
    "self":    { "href": "/api/v1/pedidos/101", "method": "GET" },
    "produto": { "href": "/api/v1/produtos/7", "method": "GET" },
    "colecao": { "href": "/api/v1/pedidos", "method": "GET" }
  }
}
```

### Coleções com paginação

```json
{
  "itens": [ { "id": 7, "nome": "Fone de Ouvido Bluetooth", "...": "..." } ],
  "pagina": 2,
  "limite": 20,
  "total_itens": 85,
  "_links": {
    "self":     { "href": "/api/v1/produtos?pagina=2&limite=20", "method": "GET" },
    "anterior": { "href": "/api/v1/produtos?pagina=1&limite=20", "method": "GET" },
    "proxima":  { "href": "/api/v1/produtos?pagina=3&limite=20", "method": "GET" },
    "criar":    { "href": "/api/v1/produtos", "method": "POST" }
  }
}
```

---

## 5. Estrutura de tratamento de erros

### Formato padrão de erro

Todos os erros seguem a mesma estrutura, o que facilita o tratamento no cliente:

```json
{
  "erro": {
    "status": 404,
    "codigo": "RECURSO_NAO_ENCONTRADO",
    "mensagem": "Produto com id 999 não foi encontrado.",
    "detalhes": [],
    "caminho": "/api/v1/produtos/999",
    "timestamp": "2026-11-07T14:32:10Z"
  }
}
```

| Campo | Descrição |
|---|---|
| `status` | código HTTP (repetido no corpo para facilitar *logs*) |
| `codigo` | identificador estável, legível por máquina |
| `mensagem` | descrição legível por humanos |
| `detalhes` | lista com erros por campo (usada em validações) |
| `caminho` | URL da requisição que gerou o erro |
| `timestamp` | data/hora UTC da ocorrência |

### Catálogo de erros

| HTTP | `codigo` | Quando ocorre |
|---|---|---|
| 400 | `REQUISICAO_INVALIDA` | JSON malformado, parâmetro de consulta inválido |
| 401 | `NAO_AUTENTICADO` | token ausente, inválido ou expirado |
| 403 | `ACESSO_NEGADO` | usuário autenticado sem permissão |
| 404 | `RECURSO_NAO_ENCONTRADO` | produto ou pedido inexistente |
| 405 | `METODO_NAO_PERMITIDO` | método HTTP não suportado no endpoint |
| 409 | `ESTOQUE_INSUFICIENTE` / `TRANSICAO_INVALIDA` | conflito com o estado atual do recurso |
| 422 | `VALIDACAO_FALHOU` | campos com tipo ou valor inválido |
| 429 | `LIMITE_EXCEDIDO` | excesso de requisições |
| 500 | `ERRO_INTERNO` | falha inesperada (detalhes internos não precisa deixar claro pro cliente o que ocorreu) |

### Exemplo — erro de validação (`422`)

```http
POST /api/v1/pedidos HTTP/1.1
Content-Type: application/json

{ "produto_id": 7, "quantidade": -3 }
```

```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

{
  "erro": {
    "status": 422,
    "codigo": "VALIDACAO_FALHOU",
    "mensagem": "Os dados enviados são inválidos.",
    "detalhes": [
      { "campo": "quantidade", "mensagem": "Deve ser maior que 0." }
    ],
    "caminho": "/api/v1/pedidos",
    "timestamp": "2026-11-07T14:35:02Z"
  }
}
```

### Exemplo — conflito de regra de negócio (`409`)

```http
HTTP/1.1 409 Conflict
Content-Type: application/json

{
  "erro": {
    "status": 409,
    "codigo": "ESTOQUE_INSUFICIENTE",
    "mensagem": "Estoque insuficiente: solicitado 50, disponível 38.",
    "detalhes": [
      { "campo": "quantidade", "mensagem": "Máximo disponível: 38." }
    ],
    "caminho": "/api/v1/pedidos",
    "timestamp": "2026-11-07T14:36:41Z"
  }
}
```

### Boas práticas adotadas

- Nunca expor *stack traces*, nomes de tabelas ou mensagens do banco nas respostas `500`; registrar apenas em *logs* internos.
- Usar o mesmo formato de erro em toda a API.
- Diferenciar **401** (quem é você?) de **403** (você não pode fazer isso).
- Diferenciar **422** (dados mal formados) de **409** (dados corretos, mas em conflito com o estado do sistema).