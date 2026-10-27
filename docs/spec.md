# Especificação: steam-cost-per-hour

Versão 1, definida em 15/10/2026 a partir da sessão de grill-me. O nome criativo do projeto fica para depois. O repositório se chama steam-cost-per-hour.

## Problem Statement

Quem joga no PC compra muitos jogos ao longo dos anos, em promoções, pacotes e presentes, e perde a noção de quanto cada um realmente valeu. A Steam mostra quanto tempo a pessoa jogou e, em outra página, quanto ela pagou, mas nunca junta as duas coisas. Não existe um jeito simples de responder perguntas como "qual jogo saiu mais barato por hora de diversão?" ou "quanto dinheiro eu tenho parado em jogos que nunca abri?".

## Solution

Um pipeline de dados que junta a biblioteca e as horas jogadas (coletadas todos os dias, automaticamente, pela API da Steam) com o histórico de compras da própria pessoa, trata os casos difíceis do histórico (pacotes, reembolsos, presentes, créditos de carteira) e entrega um painel que mostra o custo por hora de cada jogo. Como destaque secundário, o painel mostra o dinheiro parado em jogos nunca abertos e em jogos mal começados. Qualquer pessoa com perfil público pode usar com os próprios dados, e só com os próprios dados.

## User Stories

1. Como jogador, quero ver o custo por hora de cada jogo da minha biblioteca, para saber quais compras valeram a pena.
2. Como jogador, quero ver quanto dinheiro está parado em jogos que nunca abri, para repensar minhas próximas compras.
3. Como jogador, quero ver os jogos que comprei e joguei menos de 1 hora em um grupo separado, para identificar compras que quase não usei.
4. Como jogador, quero que minhas horas sejam coletadas todos os dias sem eu fazer nada, para ter um histórico de quanto joguei em cada dia.
5. Como jogador, quero carregar meu histórico de compras rodando um comando no meu computador, para que o arquivo com meus dados pessoais nunca vá para o GitHub.
6. Como jogador sem histórico de compras carregado, quero ver um custo por hora estimado pelo preço cheio da loja, claramente marcado como estimado, para ainda ter uma noção do valor de cada jogo.
7. Como jogador, quero que uma compra de pacote seja dividida entre os jogos de forma proporcional ao preço de cada um, para que o custo de cada jogo seja justo.
8. Como jogador, quero que compras reembolsadas não contem como gasto, para que o painel reflita só o que eu realmente paguei.
9. Como jogador, quero que jogos recebidos de presente e jogos gratuitos apareçam com custo zero e marcados como tal, para ver minha biblioteca completa.
10. Como jogador, quero que linhas do histórico que não são compra de jogo (créditos de carteira, itens do Mercado da Comunidade, linhas não reconhecidas) e compras em moeda estrangeira fiquem registradas com o motivo da rejeição, para saber que nada sumiu sem explicação.
11. Como jogador, quero ser identificado no banco por um código anônimo e no painel por um apelido que eu escolher, para que meu SteamID não fique exposto.
12. Como dono do projeto, quero ser avisado por e-mail quando a coleta diária falhar, para corrigir o problema antes de perder muitos dias de histórico.
13. Como dono do projeto, quero que toda execução do pipeline fique registrada (sucesso ou falha, horário, quantidade de jogos coletados), para acompanhar a saúde da coleta.
14. Como dono do projeto, quero rodar o projeto inteiro no meu computador com um comando, em um ambiente igual ao de qualquer outra pessoa, para desenvolver e testar sem mexer no banco real.
15. Como dono do projeto, quero testes automáticos para cada regra de negócio, para ter certeza de que uma mudança no código não quebra o cálculo.
16. Como recrutador, quero abrir o repositório e entender em poucos segundos o que o projeto faz, ver as execuções automáticas e prints do painel, para avaliar a capacidade técnica do candidato.
17. Como amigo do dono do projeto (fase 2), quero informar meu perfil e meu histórico e ver o meu próprio painel, sem acesso aos dados de outras pessoas.
18. Como jogador, quero ver quanto gastei dentro de cada jogo (compras no jogo feitas pela Steam), inclusive nos gratuitos, para comparar o custo real de jogos gratuitos e pagos.
19. Como jogador, quero ver o desconto que consegui em cada compra e quanto economizei no total, calculados automaticamente, sem informar nada além do histórico de compras.

## Data and Sources

**API da Steam (Steam Web API).** Fornece a lista de jogos da biblioteca de um usuário e o total acumulado de minutos jogados em cada um. Exige uma chave de API gratuita e só funciona para perfis com os detalhes de jogos públicos. A API não informa preço pago nem horas por dia, só o total acumulado. Por isso o pipeline tira uma foto diária (snapshot) e calcula as horas de cada dia pela diferença entre duas fotos seguidas. A API devolve os jogos da conta e, com o parâmetro de gratuitos jogados, os jogos gratuitos que a pessoa já abriu. Jogos emprestados pela Biblioteca Familiar não aparecem (conferido em 16/10/2026). A coleta guarda tudo o que a API devolve, inclusive programas e servidores de teste. A separação do que é jogo acontece no catálogo e na camada de análise.

**Loja da Steam.** Fornece o preço cheio de tabela de cada jogo em reais, o link da imagem de capa, o tipo e os gêneros do item. Usado para a estimativa de preço quando não há histórico de compras, para a divisão proporcional de pacotes e para as capas no painel.

**Histórico de compras da Steam.** Página que cada pessoa logada pode ver na própria conta, com data, itens, tipo de transação e valor. Não há exportação oficial, então a pessoa salva a página como arquivo HTML pelo navegador. É a única fonte do preço realmente pago. A página só mostra todas as transações depois de clicar em "Carregar mais" até o botão sumir, e precisa ser salva como "Página da Web, completa", porque a opção "somente HTML" perde as linhas carregadas depois. Ela mostra, em cada compra, o preço original da época e o percentual de desconto. As compras no jogo trazem o número do jogo no link de ajuda, mas as outras compras trazem só o nome do produto vendido (edições, DLCs e nomes antigos). Presentes recebidos não aparecem. Problemas de qualidade conhecidos: pacotes com vários jogos em uma única linha, reembolsos que aparecem como transação separada, presentes recebidos, créditos de carteira e itens de jogo misturados com compras de jogos, possíveis compras em outras moedas, e o layout da página pode mudar no futuro.

**Licenças e ativações de produtos da Steam.** Página da conta, também salva manualmente, que lista cada licença com a data e a forma de aquisição (compra na loja, presente, chave de outra loja, cortesia). É a fonte dos presentes recebidos e das licenças de cortesia, como as edições Enhanced entregues a quem tinha a versão original.

**Frequência.** API coletada 1 vez por dia. Histórico de compras carregado manualmente sempre que a pessoa quiser atualizar.

## Implementation Decisions

**Etapas do pipeline**

1. Coleta diária: chama a API da Steam para cada usuário cadastrado, grava um snapshot de minutos jogados por jogo e registra a execução.
2. Catálogo de jogos: para cada jogo novo encontrado, busca o nome, o preço cheio de tabela e a imagem de capa na loja e registra isso uma única vez.
3. Carga do histórico: script rodado na máquina da pessoa que lê o HTML do histórico, aplica as regras de qualidade e envia ao banco só as compras tratadas e as linhas rejeitadas com motivo. O arquivo HTML nunca sai do computador da pessoa nem vai para o repositório.
4. Camada de análise: views no banco que entregam o custo por hora, as horas por dia, o dinheiro parado e os jogos mal começados, prontas para o Power BI.
5. Painel: Power BI conectado ao banco, em modo de importação, lendo as views.

**Ferramentas e motivo de cada uma**

1. Python com Pandas para transformação, por ser o padrão de mercado para manipulação de dados em Python.
2. Requests para chamar a API e a loja, por ser simples e padrão de mercado.
3. BeautifulSoup para ler o HTML do histórico de compras.
4. PostgreSQL hospedado no Supabase (plano gratuito), porque a coleta roda na nuvem e precisa de um banco acessível pela internet.
5. GitHub Actions como agendador da coleta diária, porque roda com o computador desligado, é gratuito e deixa as execuções visíveis no repositório.
6. pytest para os testes das regras de negócio.
7. Docker para o ambiente local (Python e um PostgreSQL local), para desenvolver e testar sem tocar no banco real. A coleta na nuvem não usa Docker na v1.
8. Power BI para o painel, por ser uma das ferramentas de BI mais usadas no mercado.

A chave da API da Steam e as credenciais do banco ficam guardadas como segredos do GitHub e em variáveis de ambiente locais, nunca escritas no código.

**Modelo de dados (formato das tabelas)**

O banco já nasce preparado para vários usuários: toda tabela de dados pessoais tem a coluna de usuário.

- users: código anônimo (hash do SteamID), apelido, data de cadastro.
- games: identificador do jogo na Steam, nome, tipo e gêneros do item na loja (dados brutos usados na classificação), preço cheio de tabela em reais, data em que o preço foi registrado, link da imagem de capa, indicação de jogo gratuito.
- library: usuário, jogo, data em que apareceu na biblioteca, indicação de removido, indicação de licença (a pessoa tem o jogo na conta ou só joga sem licença).
- playtime_snapshots: usuário, jogo, data, minutos acumulados. Uma linha por usuário, jogo e dia.
- purchases: usuário, data, tipo (compra, presente recebido, reembolso, compra no jogo), valor total, moeda.
- purchase_items: compra, jogo, valor atribuído ao jogo depois da divisão do pacote.
- quarantine: usuário, origem (histórico ou coleta), conteúdo original da linha, motivo da rejeição, data.
- pipeline_runs: horário de início e fim, status, quantidade de usuários e jogos coletados, mensagem de erro.

**Regras de negócio e definições de métricas**

1. Custo por hora = gasto total com o jogo dividido pelas horas totais jogadas. Gasto total = valor pago pelo jogo + compras no jogo. O painel mostra as duas partes separadas. É calculado para todos os jogos com horas maiores que zero.
2. Origem do valor, em ordem de prioridade: "pago" (está no histórico de compras), "presente" ou "gratuito" (R$ 0 mais compras no jogo), "estimado" (tem licença, não está no histórico, e a loja tem preço cheio de tabela) e "sem valor conhecido" (tem licença, não está no histórico, e a loja não tem preço). Toda métrica de custo carrega essa marcação.
3. Preço estimado é o preço cheio de tabela, sem desconto, registrado na primeira vez que o jogo aparece e nunca atualizado depois.
4. Pacote: o valor pago é dividido entre os jogos do pacote proporcionalmente ao preço cheio de tabela de cada um. Se algum jogo do pacote não tiver preço de tabela, o valor é dividido em partes iguais, e a divisão fica marcada como igual.
5. Reembolso: a compra e o estorno se anulam. Se o jogo continuar na biblioteca por outro motivo, segue a regra desse outro motivo.
6. Presentes recebidos e jogos gratuitos: valor pago zero, marcados como "presente" ou "gratuito". Ficam fora do ranking principal, que compara só jogos pagos, e formam um ranking próprio ordenado por horas jogadas. Quando houver compras no jogo (ticket 10), esse ranking também mostra o gasto e o custo por hora de cada um. "Gratuito" é definido por pessoa, pela API: é o jogo que a pessoa joga sem ter licença, ou seja, que só aparece na consulta com o parâmetro de gratuitos jogados. A indicação de gratuito da loja não serve para isso, porque mostra o status atual do jogo para qualquer pessoa: um jogo comprado que depois virou gratuito continua pago para quem o comprou, e um gratuito que foi encerrado continua gratuito. Ela fica guardada só como dado bruto. Ter licença também não prova que houve pagamento: alguns jogos que viraram gratuitos dão licença a quem começou a jogar depois da mudança. Por isso, um jogo com licença só tem valor "pago" se estiver no histórico de compras. Se não estiver, segue a regra 2 (estimado ou sem valor conhecido) e nunca vira R$ 0 por suposição.
7. Moeda: na v1 só compras em reais são aceitas. Compras em outra moeda vão para a quarentena.
8. Linhas do histórico que não são compra de jogo nem compra no jogo vão para a quarentena com o motivo: créditos de carteira (inclusive compras de crédito e vales-presente), transações do Mercado da Comunidade, presentes enviados a outras pessoas, tipos não reconhecidos, outra moeda e produtos que não foram ligados a nenhum jogo da biblioteca.
9. Jogos com 0 horas não entram no ranking de custo por hora e compõem o indicador de dinheiro parado.
10. Jogos com mais de 0 e menos de 1 hora têm o custo por hora calculado e guardado, mas não aparecem no ranking principal do painel. Os jogos pagos desse grupo formam o grupo "comprados e mal começados".
11. Horas por dia = minutos acumulados no snapshot do dia menos os do dia anterior. Minutos acumulados = tempo online + tempo jogado desconectado, como a biblioteca da Steam mostra.
12. Jogo novo na biblioteca começa a contar a partir do primeiro snapshot em que aparece.
13. Se o total de minutos de um jogo diminuir de um dia para o outro, aquele dia vai para a quarentena em vez de gerar horas negativas.
14. Jogo que some da biblioteca mantém todo o histórico e é marcado como removido.
15. Falha na coleta: a execução é registrada como falha, o GitHub envia e-mail ao dono do repositório e a coleta tenta de novo no dia seguinte. Um perfil que virou privado é registrado como falha daquele usuário, sem derrubar a coleta dos demais.
16. Compras no jogo (microtransações pagas pela Steam) somam ao gasto total do jogo, gratuito ou pago. Créditos de carteira continuam na quarentena: o dinheiro só conta quando é gasto, para não ser contado duas vezes. Compras feitas fora da Steam (no site da empresa do jogo) não aparecem no histórico e ficam fora do projeto. O painel informa esse limite.
17. Só itens classificados como "jogo" entram na camada de análise e no painel. Programas (como o Wallpaper Engine), servidores de teste e playtests continuam guardados na coleta, mas ficam fora das métricas. O campo de tipo da loja não basta, porque a loja marca o Wallpaper Engine e os servidores de teste como "game". A classificação é uma regra em SQL sobre os dados brutos da loja: "programa" se o item tem algum gênero de software (Utilities, Design & Illustration, Photo Editing etc.), "outro" se não tem gênero nem página na loja, e "jogo" no resto.
18. Jogos "sem valor conhecido" aparecem nas horas jogadas, mas ficam fora do ranking de custo por hora e da soma do dinheiro parado, porque não dá para somar um valor desconhecido. O painel mostra quantos jogos estão nessa situação.
19. Itens fora das métricas (programas e outros) aparecem numa lista no painel, com o motivo. Assim, um jogo de verdade classificado errado, por exemplo um jogo removido da loja sem gêneros, pode ser percebido e corrigido.
20. Jogos encerrados ou retirados da loja não têm regra própria: as regras de licença (6), de origem do valor (2) e de classificação (17) já resolvem esses casos.
21. Desconto obtido = 1 − (valor pago ÷ preço original da época da compra, mostrado no histórico; sem essa informação, o preço cheio de tabela atual). Economia total = soma dos preços cheios − soma dos valores pagos. Só entram jogos com origem "pago" e com preço de tabela. Em pacotes, vale o valor atribuído a cada jogo depois da divisão. Quando a comparação for com o preço cheio atual, o painel avisa: se o preço mudou desde a compra (por exemplo, num reajuste regional), o desconto calculado fica distorcido.
22. Cada item do histórico é ligado a um jogo da biblioteca nesta ordem: (a) número do jogo no link da linha; (b) nome exato do jogo ou de um apelido público versionado no repositório (nomes antigos de produtos, como PLAYERUNKNOWN'S BATTLEGROUNDS para PUBG); (c) o nome do produto começa com o nome do jogo ou do apelido, valendo o mais longo; (d) sem correspondência, a linha vai para a quarentena com o nome do produto.
23. A primeira compra ligada a um jogo é o valor pago pelo jogo. As compras seguintes do mesmo jogo (DLCs, passes, capítulos) somam ao gasto extra, como as compras no jogo.

**Painel (Power BI)**

Visão principal: ranking de custo por hora dos jogos pagos (origem "pago" ou "estimado") com 1 hora ou mais, mostrando sempre as horas e a origem do valor ao lado. Ao lado, o ranking dos gratuitos e presentes, ordenado por horas. Destaques secundários: total de dinheiro parado em jogos com 0 horas e total em jogos mal começados. Visões de apoio: horas jogadas por dia e por jogo. O design interativo (tema, capas, navegação, detalhe por jogo) está descrito no ticket 11.

**Idioma.** Código, tabelas e colunas em inglês. README em português com um resumo curto em inglês no topo.

## Success Criteria

Cada conferência usa uma fonte independente do código, nunca o próprio resultado calculado de novo.

1. Horas jogadas: para 5 jogos escolhidos ao acaso, as horas no banco batem com as horas exibidas na biblioteca da Steam.
2. Valores pagos: para 5 compras, incluindo pelo menos um pacote, um reembolso e um presente, o valor no banco bate com o que aparece na página de Histórico de compras da Steam.
3. Contagem do histórico: linhas aceitas mais linhas na quarentena somam exatamente o total de linhas do arquivo de histórico, e toda linha da quarentena tem um motivo preenchido.
4. Coleta diária: 7 execuções seguidas com sucesso visíveis no GitHub Actions, e cada dia tem um snapshot por jogo da biblioteca, com o número de jogos batendo com a referência do perfil da Steam. Nenhum número do perfil bate sozinho com a API: o contador "Jogos" não inclui os gratuitos, e a lista "Todos os jogos" inclui jogos emprestados pela família. Por isso a conferência parte do contador "Jogos" e lista cada diferença explicada (gratuitos jogados, itens de teste).
5. Painel: o custo por hora de 3 jogos no Power BI bate com uma conta feita à mão (valor pago dividido pelas horas exibidas na biblioteca da Steam), e o total de dinheiro parado bate com a soma manual dos jogos com 0 horas.
6. Testes: os testes das regras de negócio (pacote, reembolso, presente, moeda estrangeira, zero horas, horas que diminuem, jogo novo) passam.
7. Qualidade de dados: nenhuma chave duplicada (um snapshot por usuário, jogo e dia, um item por compra e jogo), nenhum valor pago negativo, nenhum jogo sem nome no catálogo.
8. Privacidade: nenhum SteamID em texto aberto no banco, nenhum arquivo de histórico ou credencial no repositório.

**A v1 está pronta quando** a coleta rodar sozinha por 7 dias, o histórico do autor estiver carregado, o painel mostrar custo por hora e dinheiro parado, todos os critérios acima passarem e o README tiver os prints do painel.

## Out of Scope

1. Outros usuários além do autor usando o projeto (fase 2, embora o banco já esteja preparado).
2. Conversão de moedas estrangeiras (fase 2).
3. Alertas por Telegram ou qualquer outro canal de mensagem.
4. Login automático na Steam ou qualquer coleta que exija a senha do usuário.
5. Coleta de perfis de pessoas que não deram consentimento, mesmo que públicos.
6. Docker na execução em nuvem (na v1 ele é só o ambiente local).
7. Página web pública para visualizar o painel.
8. Plataformas além da Steam (Epic, PlayStation, Xbox).
9. Compras no jogo feitas fora da Steam. Não existe fonte confiável para elas: os sites de cada empresa exigem login, e uma planilha preenchida à mão foi descartada por ser insustentável (a pessoa não tem esses valores).
10. Horas em jogos emprestados pela Biblioteca Familiar. A API principal não os devolve, e a de jogos recentes só cobriria o que foi jogado nas últimas 2 semanas, a partir do início da coleta. Avaliado e descartado em 16/10/2026.

## Open Questions

1. Nome criativo do projeto (o repositório segue como steam-cost-per-hour por enquanto).
2. ~~Preço de referência para jogos que não estão mais à venda na loja.~~ Respondida em 16/10/2026: a origem "sem valor conhecido" (regras 2 e 18) e a divisão igual no pacote (regra 4).
3. Como tratar um pacote que contém DLCs ou jogos que a pessoa já tinha antes da compra.
4. ~~Se os jogos compartilhados pela Biblioteca Familiar da Steam aparecem na API e, se aparecerem, como tratá-los.~~ Respondida em 16/10/2026: não aparecem. A API devolve só os jogos da conta e os gratuitos jogados.
5. ~~Verificar se a API do IsThereAnyDeal tem histórico de preços em reais.~~ Respondida em 27/10/2026: o próprio histórico de compras mostra o preço original e o desconto da época (regra 21).
6. Licenças recebidas de graça junto com outro jogo, como as edições Enhanced do GTA V e do Metro Exodus, entregues a quem tinha a versão original. Hoje elas viram "estimado" pelo preço da loja e inflam o dinheiro parado (R$ 373,90 dos R$ 431,89 no painel do autor, em 19/10/2026). Decidir no ticket 08, com o histórico real: por exemplo, a edição original aparece no histórico e a Enhanced não.
7. ~~As horas exibidas na biblioteca são playtime_forever + playtime_disconnected, e a coleta gravava só playtime_forever.~~ Resolvida em 27/10/2026: a coleta passou a somar os dois campos, e os snapshots antigos receberam o tempo desconectado atual de cada jogo (script de uso único src/backfill_disconnected.py), sem alterar nenhuma hora por dia. O Deadlock ficou com 438,43 h no banco e 438,4 h na biblioteca.
