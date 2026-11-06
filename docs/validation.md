# Validação da v1

Conferência final dos 9 critérios de sucesso da [especificação](spec.md), feita em 05/11/2026 com os dados do Supabase. Cada critério usa uma fonte que não passa pelo código: a biblioteca da Steam, a página de Histórico de compras, o perfil da Steam, a aba Actions do GitHub ou uma conta feita à mão. As consultas ao banco rodaram numa sessão só de leitura.

## 1. Horas jogadas

Sorteei 5 jogos com horas (semente 20261105, para o sorteio poder ser repetido) e comparei as horas do banco com as da biblioteca da Steam.

| Jogo | Banco | Biblioteca |
|---|---|---|
| Dying Light | 48,07 h | 48,1 h |
| Enshrouded | 15,05 h | 15 h |
| Destiny 2 | 5,32 h | 5,3 h |
| Ready or Not | 6,40 h | 6,4 h |
| Fallout 4 | 83,25 h | 83,2 h |

Resultado: passou. Os 5 batem, com a biblioteca arredondando para uma casa decimal.

## 2. Valores pagos

| Caso | Banco | Página de Histórico de compras |
|---|---|---|
| Pacote: Cities: Skylines com 3 expansões, 22/05/2021 | R$ 47,84, dividido em 4 × R$ 11,96 | R$ 47,84 na mesma linha |
| Reembolso: The Witcher 3, 17/09/2020 | compra e estorno se anulam, os dois na quarentena com o motivo | compra riscada e estorno |
| Presente enviado: NieR:Automata, 03/10/2020 | R$ 53,50 na quarentena, fora do meu gasto | compra de presente, R$ 53,50 |
| Compra simples: No Rest for the Wicked, 03/06/2026 | R$ 81,89 | R$ 81,89 |
| Compra simples: Dead by Daylight: Jason, 07/08/2026 | R$ 17,49 | R$ 17,49 |

Resultado: passou.

## 3. Contagem do histórico

O arquivo tem 191 linhas de transação, contadas com grep direto no HTML, sem o script de carga. No banco, são 105 compras aceitas e 86 linhas na quarentena, total de 191. Nenhuma linha da quarentena está sem motivo.

Resultado: passou.

## 4. Coleta diária

- A aba Actions mostra 14 execuções agendadas seguidas com sucesso, de 23/10 a 05/11/2026.
- Cada um desses 14 dias tem 79 snapshots, um por item da biblioteca, e nenhum dia ficou sem coleta.
- A biblioteca no banco tem 79 itens: 54 com licença e 25 gratuitos jogados sem licença.
- O contador "Jogos" do perfil mostra 52, o mesmo de 16/10/2026.
- Diferenças explicadas: os 25 gratuitos não entram no contador, e dos 54 itens com licença, 2 são itens de teste ou programas que o contador também não inclui (54 − 2 = 52).

Resultado: passou.

## 5. Painel

| Jogo | Gasto (Histórico de compras) | Horas (biblioteca) | Conta à mão | Painel |
|---|---|---|---|---|
| PAYDAY 2 | R$ 2,19 + R$ 8,67 de extras | 44,1 h | R$ 10,86 ÷ 44,13 h = R$ 0,25 | R$ 0,25 |
| Hunt: Showdown 1896 | R$ 31,15 + R$ 11,05 de extras | 148,4 h | R$ 42,20 ÷ 148,37 h = R$ 0,28 | R$ 0,28 |
| Dying Light: The Beast | R$ 186,75 | 35,5 h | R$ 186,75 ÷ 35,48 h = R$ 5,26 | R$ 5,26 |

O dinheiro parado é R$ 0,00. Os 3 jogos com 0 hora (Company of Heroes 2, Metro Exodus Enhanced Edition e Grand Theft Auto V Enhanced) não têm compra no histórico, então a soma manual também dá R$ 0,00 (regra 24). O painel mostra R$ 0,00.

Resultado: passou.

## 6. Testes

Os 79 testes automáticos passam no PostgreSQL local do Docker. Eles cobrem pacote, reembolso, presente, moeda estrangeira, zero hora, horas que diminuem e jogo novo.

Resultado: passou.

## 7. Qualidade de dados

Nenhuma chave duplicada (snapshots por usuário, jogo e dia, e itens por compra), nenhum valor negativo em compras, itens, valor do jogo, gasto extra ou horas por dia, e nenhum jogo sem nome no catálogo.

Resultado: passou.

## 8. Privacidade

- No banco, o SteamID real não aparece em nenhuma das 21 colunas de texto, e todo user_id é um HMAC-SHA256 em hexadecimal.
- No repositório, a varredura de todo o histórico do Git (143 commits, contando os ramos de backup locais) não encontrou o SteamID, a chave da API, a chave do hash nem as senhas do banco, e nenhum arquivo .env ou de histórico de compras real foi versionado.
- Os SteamIDs que aparecem nos testes são fictícios.

Resultado: passou.

## 9. Fatos do painel

Conferido em 03/11/2026 (ticket 11b):
- As 31 consultas de [fact_checks.sql](fact_checks.sql) batem com os números do painel.
- 5 fatos batem com a própria Steam: as horas de Warframe e de Rainbow Six Siege na biblioteca e, no Histórico de compras, a primeira compra (GRID, 30/12/2014, R$ 24,81), a compra mais cara (Battlefield 6, R$ 299,00) e o maior desconto (The Crew 2, 98%).

Resultado: passou.
