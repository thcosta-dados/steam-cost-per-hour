# steam-cost-per-hour

> **EN:** Data pipeline that combines a Steam library's playtime (collected daily from the Steam Web API) with the user's own purchase history to show the cost per hour of each game in a Power BI dashboard. Work in progress.

> 🚧 **README provisório.** O projeto está em construção. A versão final, com diagrama do fluxo, prints e GIF do painel, entra no fim da v1.

## O que é

Um pipeline de dados que junta as horas jogadas de cada jogo da Steam com o valor pago por ele e responde perguntas como:

- Qual jogo saiu mais barato por hora de diversão?
- Quanto dinheiro está parado em jogos que nunca abri?

A especificação completa está em [docs/spec.md](docs/spec.md) e o plano de trabalho em [docs/tickets.md](docs/tickets.md).

## Stack

Python (Pandas, Requests, BeautifulSoup), PostgreSQL (Supabase), GitHub Actions, Docker, pytest e Power BI.

## Ambiente local

Pré-requisito: [Docker Desktop](https://www.docker.com/products/docker-desktop/) aberto.

```bash
# 1. Crie o arquivo de variáveis a partir do modelo e preencha os valores
cp .env.example .env

# 2. Suba o banco PostgreSQL e o ambiente Python
docker compose up -d

# 3. Rode os testes dentro do ambiente
docker compose exec app pytest

# Para desligar
docker compose down
```

O banco local fica acessível pelo Windows (pgAdmin, DBeaver, Power BI) em `localhost:5433`, com o usuário e a senha definidos no `.env`.

## Pipeline

```bash
docker compose exec app python -m src.create_tables  # cria (ou atualiza) tabelas e views
docker compose exec app python -m src.collect        # coleta biblioteca e horas do dia
docker compose exec app python -m src.catalog        # busca preço, capa e gêneros dos jogos novos
```

## Banco na nuvem (Supabase)

O mesmo código roda contra o Supabase trocando só as variáveis de ambiente. Crie o `.env.cloud` com os dados do *Session pooler* do projeto e `POSTGRES_SSLMODE=require` (veja o `.env.example`), e use o serviço `app-cloud`:

```bash
docker compose run --rm app-cloud python -m src.create_tables
docker compose run --rm app-cloud python -m src.collect
```

As tabelas têm Row Level Security ligado e as views usam `security_invoker`, para que a API pública do Supabase não exponha os dados.

## Painel

O painel do Power BI está em `dashboard/`, salvo como projeto (`.pbip`). Ele lê as views do banco, e o servidor e o banco são parâmetros. Os dados importados não são versionados.

## Privacidade

Credenciais ficam só no `.env` (ignorado pelo Git) e nos segredos do GitHub. Arquivos de histórico de compras nunca vão para o repositório, e o SteamID só é gravado no banco transformado em hash.
