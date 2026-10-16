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

## Privacidade

Credenciais ficam só no `.env` (ignorado pelo Git) e nos segredos do GitHub. Arquivos de histórico de compras nunca vão para o repositório, e o SteamID só é gravado no banco transformado em hash.
