# NutriTrack API

Segunda componente do MVP **NutriTrack** (diário alimentar). É uma API REST em
Flask que funciona como **intermediária em cadeia** entre o front e a
[Open Food Facts](https://openfoodfacts.org): consome, **normaliza e cacheia** os
dados externos, e faz o CRUD dos registros de consumo. O front **nunca** fala com
a Open Food Facts diretamente.

- Repositório do front (componente principal): https://github.com/almeidamx/nutritrack-front
- Repositório desta API: https://github.com/almeidamx/nutritrack-api

## Stack

- **Flask** + **flask-openapi3** (Swagger interativo gerado dos schemas Pydantic)
- **SQLAlchemy 2.0** + **SQLite**
- **requests** para o consumo da Open Food Facts
- **gunicorn** como servidor de produção no container

## Arquitetura em cadeia

```
front (React/nginx)  ──►  esta API (Flask)  ──►  Open Food Facts
                                              ├─ /api/v2/product/{barcode}  (detalhe)
                                              └─ search.openfoodfacts.org   (busca)
```

Por que a cadeia (e não o front chamando a OFF direto):

1. O enunciado exige que os dados sejam **consumidos e tratados dentro da aplicação**.
2. O **rate limit** da OFF é por IP (15 req/min leitura, 10 req/min busca). Com a API
   no meio, o cache de produto no SQLite protege a cota compartilhada.
3. Busca por texto e detalhe por barcode vivem em **hosts diferentes**, com formatos
   diferentes — a reconciliação acontece aqui.
4. A normalização é pesada (fallback de nome PT, `energy-kcal` vs `energy` em kJ,
   arredondamento, macros ausentes) e não deve ser duplicada no front.

## Rotas

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/products/search?q=&page=&page_size=` | Busca produtos por texto (proxy Search-a-licious) |
| GET | `/api/products/{barcode}` | Detalhe de um produto por código de barras (e cacheia) |
| GET | `/api/entries?date=&meal=&page=&page_size=` | Lista registros (paginado, com filtros) |
| POST | `/api/entries` | Cria um registro de consumo |
| PUT | `/api/entries/{id}` | Edita quantidade/refeição de um registro |
| DELETE | `/api/entries/{id}` | Remove um registro |
| GET | `/api/goal` | Lê a meta diária |
| PUT | `/api/goal` | Atualiza a meta diária (upsert) |
| GET | `/api/summary?date=` | Totais consumidos no dia × meta (alimenta o dashboard) |
| GET | `/api/health` | Healthcheck |

Cobre os quatro métodos exigidos (**GET, POST, PUT, DELETE**) e bem mais que 4 rotas.

**Documentação interativa (Swagger):** com a API no ar, acesse
`http://localhost:5000/openapi/swagger`.

## A API externa: Open Food Facts

- **Licença:** dados sob [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1.0/),
  conteúdo sob [DbCL 1.0](https://opendatacommons.org/licenses/dbcl/1.0/), imagens sob
  [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/deed.en).
- **Cadastro:** **não é necessário** para leitura (público e gratuito). Só operações
  de escrita exigem autenticação — e o NutriTrack só faz leitura.
- **Rotas da OFF utilizadas:**
  - `GET https://world.openfoodfacts.org/api/v2/product/{barcode}.json` (detalhe)
  - `GET https://search.openfoodfacts.org/search` (busca por texto)
- Enviamos o header `User-Agent: NutriTrack/1.0 (almeida.mx@gmail.com)`, conforme a doc.

## Como rodar

### Via Docker (recomendado — junto do front)

O `docker-compose.yml` fica no repositório do **front** e sobe as duas componentes.
Veja o README de lá. Para subir só a API isoladamente:

```bash
docker build -t nutritrack-api .
docker run -p 5000:5000 -v nutritrack_data:/data nutritrack-api
```

### Localmente (desenvolvimento)

Pré-requisitos: **Python 3.11+**.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt

# (opcional) popular dados de demonstração
python seed.py

# subir a API
python wsgi.py
```

A API sobe em `http://localhost:5000`. O banco SQLite é criado automaticamente
(`nutritrack.db` local, ou `/data/nutritrack.db` no container).

## Dados de demonstração

`python seed.py` limpa e recria produtos de exemplo, registros do dia de hoje
distribuídos entre as refeições, e uma meta — para o dashboard aparecer populado
sem depender da OFF ao vivo (evita 503 e rate limit durante a gravação).

## Modelo de dados

- **Product** — cache local do produto da OFF (chave: `barcode`). No MVP nunca expira.
- **Entry** — o registro de consumo. Entidade central. Os macros são **congelados**
  na gravação (regra de três `valor_100 × quantidade ÷ 100`); macro ausente vira
  `null` e é excluído das somas.
- **Goal** — meta diária (singleton).

## Convenções

Arquivos e identificadores Python em `snake_case`; documentação e comentários em
PT-BR; rotas, colunas e nomes de campo em inglês.
