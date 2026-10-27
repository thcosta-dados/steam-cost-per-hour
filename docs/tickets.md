# Tickets: steam-cost-per-hour

Baseados na especificação em `docs/spec.md`. Cada ticket cabe em uma sessão de trabalho e entrega algo que funciona e pode ser conferido sozinho. A ordem abaixo respeita as dependências. Depois do ticket 02, os tickets 03, 05, 07 e 08 podem ser feitos em qualquer ordem.

Ao concluir um ticket, marque os critérios de aceite com [x].

---

# 01: Preparação do ambiente

**What to build:** o repositório steam-cost-per-hour existe no GitHub, com um ambiente local que sobe Python e PostgreSQL em containers Docker com um único comando. Um primeiro teste automático roda e passa. O repositório já tem um README provisório, a lista de arquivos que nunca devem ser enviados ao GitHub (credenciais, arquivos de histórico de compras) e um modelo das variáveis de ambiente necessárias, sem valores reais.

**Blocked by:** None (can start immediately).

**Acceptance criteria:**
- [x] O repositório existe no GitHub com a especificação e os tickets.
- [x] Git, Python e Docker Desktop estão instalados e funcionando no computador de desenvolvimento.
- [x] Com o Docker instalado, um único comando sobe o ambiente local e o banco PostgreSQL fica acessível.
- [x] Um teste de exemplo roda com pytest dentro do ambiente e passa.
- [x] Credenciais e arquivos de histórico estão listados para serem ignorados pelo Git, e um teste manual confirma que um arquivo desses não aparece para commit.
- [x] O modelo de variáveis de ambiente lista a chave da API da Steam e os dados de conexão do banco, sem valores reais.
- [x] Existe um README provisório.

---

# 02: Primeira coleta da biblioteca

**What to build:** um comando busca na API da Steam todos os jogos da biblioteca do autor com os minutos jogados e grava no banco local. O usuário é registrado com o SteamID transformado em hash e um apelido. Cada execução grava um snapshot por jogo naquele dia, e rodar duas vezes no mesmo dia não duplica nada.

**Blocked by:** 01.

**Acceptance criteria:**
- [x] As tabelas de usuários, jogos, biblioteca e snapshots existem no banco local com as chaves definidas na especificação.
- [x] Após rodar o comando, o número de jogos no banco bate com o perfil da Steam, com cada diferença explicada. Conferido em 16/10/2026: banco 79 = 54 jogos da conta + 25 gratuitos jogados. O contador "Jogos" do perfil (52) não inclui gratuitos nem 2 dos 4 itens de teste ou programa. A lista "Todos os jogos" (100) inclui jogos jogados da Biblioteca Familiar, que a API não devolve.
- [x] Para 5 jogos escolhidos ao acaso, as horas no banco batem com as horas exibidas na biblioteca da Steam.
- [x] Rodar o comando duas vezes no mesmo dia mantém exatamente um snapshot por jogo naquele dia.
- [x] Nenhum SteamID em texto aberto existe no banco.
- [x] A chave da API é lida da variável de ambiente, nunca escrita no código.

---

# 03: Catálogo de preços

**What to build:** para cada jogo novo encontrado na biblioteca, o pipeline busca na loja da Steam o tipo e os gêneros do item, o preço cheio de tabela em reais, o link da imagem de capa e se o jogo é gratuito, e registra isso uma única vez, junto com a data do registro. Jogos que já estão no catálogo não são consultados de novo.

**Blocked by:** 02.

**Acceptance criteria:**
- [x] Todo jogo da biblioteca tem nome no catálogo.
- [x] Para 5 jogos pagos, o preço registrado bate com o preço cheio exibido na página da loja (sem desconto). Conferido em 16/10/2026 com Cyberpunk 2077, Mortal Kombat 11, Hades II, Dying Light 2 e Dead by Daylight. Dois estavam em promoção, e o banco registrou o preço riscado.
- [x] Jogos gratuitos estão marcados como gratuitos pela regra de licença (spec, regra 6): a coleta marca na biblioteca os jogos que a pessoa joga sem licença. Conferido pela própria pessoa, que confirmou que não pagou por nenhum dos 25 marcados. CS2, PUBG e R6 ficaram "com licença". Se a licença foi paga ou não, quem decide é o histórico de compras (ticket 08), sem suposição.
- [x] A regra de classificação em SQL separa jogo, programa e outro. Na revisão manual da lista, o Wallpaper Engine aparece como programa, os servidores de teste e playtests como outro, e nenhum jogo de verdade fica fora de "jogo". O GrandChase Classic, sem gêneros na loja, ficou como outro por decisão do dono.
- [x] Rodar o pipeline de novo não altera preços já registrados.
- [x] Jogos sem preço na loja (fora de venda) ficam registrados sem preço e aparecem numa lista para decidir a regra (pergunta em aberto da especificação). HITMAN™ 2 e GRID Autosport conferidos na loja. A regra foi decidida (spec, regras 2, 18 e 20).
- [x] As chamadas à loja respeitam um intervalo entre requisições para não sobrecarregar o serviço.

---

# 04: Primeiro painel com preço estimado

**What to build:** views no banco calculam o custo por hora de cada jogo usando o preço estimado e um Power BI simples, conectado ao banco local, mostra o ranking dos jogos com 1 hora ou mais, o grupo de jogos mal começados (menos de 1 hora) e o total de dinheiro parado em jogos com 0 horas. É a primeira versão ponta a ponta do projeto.

**Blocked by:** 03.

**Acceptance criteria:**
- [x] O custo por hora é calculado e guardado para todos os jogos com horas maiores que zero.
- [x] As views consideram só itens classificados como "jogo" (regra do ticket 03): programas, servidores de teste e playtests ficam fora das métricas.
- [x] Cada jogo recebe a origem do valor ("gratuito", "estimado" ou "sem valor conhecido"). Os "sem valor conhecido" ficam fora do ranking e do dinheiro parado, e o painel mostra quantos são.
- [x] O painel tem a lista de itens fora das métricas, com o motivo de cada um.
- [x] O ranking do painel mostra só jogos com 1 hora ou mais, com as horas e a origem do preço ao lado.
- [x] O custo por hora de 3 jogos no painel bate com uma conta feita à mão (preço da loja dividido pelas horas exibidas na biblioteca da Steam). Conferido em 21/10/2026 com ARC Raiders, Ready or Not e Cities: Skylines.
- [x] O total de dinheiro parado bate com a soma manual dos preços dos jogos com 0 horas. Conferido: R$ 431,89 (Company of Heroes 2, GTA V Enhanced e Metro Exodus Enhanced). Ver a pergunta em aberto 6 da spec.
- [x] O ranking principal mostra só jogos pagos. Os gratuitos aparecem num ranking próprio, ordenado por horas, e o grupo "comprados e mal começados" tem só jogos pagos.

---

# 05: Banco na nuvem

**What to build:** as mesmas tabelas criadas no Supabase, e o comando de coleta funcionando contra esse banco quando rodado manualmente. O ambiente local continua funcionando para desenvolvimento e testes, e escolher entre os dois depende só das variáveis de ambiente.

**Blocked by:** 02.

**Acceptance criteria:**
- [x] A estrutura das tabelas no Supabase é idêntica à do banco local, criada pelos mesmos scripts. Conferido em 21/10/2026: o catálogo dos dois bancos (colunas, chaves, checks, RLS, opções e definição das views) é idêntico, 58 de 58 linhas.
- [x] Uma coleta manual grava os dados no Supabase, e o número de jogos bate com o do banco local na mesma data (que já foi conferido contra o perfil da Steam no ticket 02). Conferido: 79 jogos, 79 snapshots e 490.104 minutos em 21/10 nos dois bancos, com o mesmo código de usuário e o mesmo catálogo.
- [x] Trocar de banco não exige mudar nenhuma linha de código, só as variáveis de ambiente.
- [x] As credenciais do Supabase não aparecem em nenhum arquivo do repositório.
- [x] Os dados não ficam expostos pela API pública do Supabase: RLS ligado nas tabelas, views com security_invoker e o Security Advisor do Supabase sem alertas (só o aviso informativo esperado de RLS sem policies).

---

# 06: Coleta automática diária

**What to build:** o GitHub Actions roda a coleta e o catálogo uma vez por dia, sozinho, gravando no Supabase. Cada execução fica registrada com horário, status e quantidade de jogos coletados. Se a execução falhar, o GitHub avisa por e-mail. Se o perfil de um usuário estiver privado, isso é registrado como falha daquele usuário e a coleta dos demais continua.

**Blocked by:** 03, 05.

**Acceptance criteria:**
- [x] A coleta roda no horário agendado sem nenhuma ação manual, e a execução aparece na aba de ações do repositório. Conferido: 5 execuções seguidas com gatilho schedule e sucesso (23 a 27/10/2026). O GitHub atrasou o início em 5 a 7 horas (rodaram entre 08:05 e 10:07), sem mudar a data dos snapshots.
- [x] Cada execução gera um registro na tabela de execuções, com status e quantidade de jogos. Conferido em 22/10/2026: as execuções no GitHub batem com as linhas de pipeline_runs no Supabase (status, horário e 79 jogos).
- [x] Uma falha forçada de teste (por exemplo, chave inválida) gera registro de falha e e-mail do GitHub. Conferido em 22/10/2026: HTTP 401 registrado como failed, execução vermelha e e-mail recebido pelo dono.
- [x] Um usuário de teste com perfil privado gera registro de falha só para ele, sem derrubar a execução. Coberto por teste automático com usuários fictícios e conferido em 27/10/2026 com uma conta real de familiar, que consentiu e estava com perfil privado: execução partial (79 jogos do dono, falha só da conta de teste), nenhum dado dela gravado e conta removida dos segredos logo depois.
- [x] A chave da API e as credenciais do banco estão guardadas como segredos do GitHub. Seis segredos cadastrados pelo gh a partir do .env.cloud, mascarados como *** nos logs e ausentes dos arquivos do repositório.

---

# 07: Horas por dia

**What to build:** uma view calcula quantas horas foram jogadas em cada dia, por jogo, pela diferença entre snapshots seguidos. Jogo novo começa a contar a partir do primeiro snapshot. Jogo que some da biblioteca mantém o histórico e é marcado como removido. Se o total de um jogo diminuir de um dia para o outro, aquele dia vai para a quarentena com o motivo, em vez de gerar horas negativas.

**Blocked by:** 02.

**Acceptance criteria:**
- [x] Testes automáticos cobrem: dia normal, jogo novo, jogo removido, total que diminui e dia sem coleta.
- [x] Nenhum valor de horas por dia é negativo. Conferido nos dois bancos (zero linhas negativas).
- [x] Com dados reais de pelo menos 2 dias, as horas de um jogo jogado no período batem com a diferença das horas exibidas na biblioteca da Steam nos dois dias (anotadas à mão). Primeira anotação: Deadlock com 430,5 h na biblioteca em 22/10/2026 às 17:22, sem jogar depois da coleta das 17:05. Segunda anotação: 438,4 h em 27/10/2026. Diferença na biblioteca: 7,9 h. Soma da daily_playtime entre os snapshots de 22 e 27/10: 7,92 h (475 min). Bate, com diferença só de arredondamento.
- [x] Todo registro na quarentena tem motivo preenchido. Conferido nos dois bancos. Nos dados reais não houve queda de total, e o motivo é exigido pelo teste automático.

---

# 08: Histórico de compras, casos simples

**What to build:** um script rodado no computador da pessoa lê o arquivo HTML do histórico de compras salvo da Steam e carrega no banco as compras normais, os presentes recebidos e as compras no jogo (microtransações pagas pela Steam, inclusive em jogos gratuitos). Créditos de carteira, itens do Mercado da Comunidade, linhas não reconhecidas e compras em outra moeda vão para a quarentena com o motivo. O arquivo HTML nunca sai do computador. O repositório público usa um arquivo de histórico fictício para os testes.

**Blocked by:** 02.

**Acceptance criteria:**
- [x] Linhas aceitas mais linhas na quarentena somam exatamente o total de linhas do arquivo de histórico. Conferido em 27/10/2026 nos dois bancos: 105 aceitas + 86 na quarentena = 191, igual à contagem independente das linhas do arquivo (grep).
- [x] Toda linha na quarentena tem motivo preenchido.
- [x] Para 3 compras normais e 1 DLC, o valor, a data e o jogo no banco batem com a página de Histórico de compras da Steam. Conferido pelo dono: Subnautica 2, Battlefield 6, Hades II e a DLC Dead by Daylight: Jason.
- [x] Todo item aceito está ligado a um jogo da biblioteca (spec, regra 22). Os produtos não identificados ficam na quarentena com o nome.
- [x] Para 2 compras com desconto, o preço original e o percentual gravados batem com a página. Conferido: Machine Party e MECCHA CHAMELEON (-15%).
- [x] Forma de pagamento, saldo da carteira, destinatário de presente e número da transação não são gravados no banco. Conferido por varredura: 0 de 116 números de transação, nenhuma bandeira de cartão e 0 de 6 destinatários de presente (nomes, SteamIDs e ids de perfil) gravados.
- [x] Para 2 compras no jogo (pelo menos uma em jogo gratuito), o valor, a data e o jogo no banco batem com a página de Histórico de compras, e nenhum crédito de carteira é contado como gasto. Conferido: Warframe (gratuito para o dono, 2020) e Dead by Daylight (2026). Os 5 créditos de carteira ficaram na quarentena.
- [x] Testes automáticos usam um histórico fictício com todos os tipos de linha, e nenhum histórico real está no repositório.
- [x] Carregar o mesmo arquivo duas vezes não duplica compras. Conferido nos dois bancos. A página real reutiliza o número da transação no reembolso, e por isso o tipo da linha entra na impressão digital.

---

# 08b: Jogos sem compra na Steam (presentes, cortesias e promoções)

**What to build:** com o histórico de compras completo carregado, os jogos com licença e sem nenhuma compra recebem a origem "sem compra na Steam" (spec, regra 24): valor zero, no ranking de gratuitos e presentes e fora do dinheiro parado. Responde a pergunta em aberto 6 sem a página de licenças, que foi avaliada e descartada por ser paginada (muito trabalho manual).

**Blocked by:** 08.

**Acceptance criteria:**
- [x] A carga do histórico registra que o usuário tem histórico completo, e só a partir disso a regra 24 vale para ele. Coluna users.purchase_history_loaded_at, gravada pela carga, nos dois bancos.
- [x] Os jogos "sem compra na Steam" do autor são exatamente os 9 da lista revisada por ele em 27/10/2026, com valor zero, no ranking de gratuitos e presentes. Conferido nos dois bancos (9 de 9, sem sobras nem faltas) e no painel.
- [x] GTA V Enhanced, Metro Exodus Enhanced e Company of Heroes 2 saem do dinheiro parado, que é conferido por uma soma manual. Dinheiro parado: de R$ 431,89 para R$ 0,00 (soma manual: 0 + 0 + 0), igual no painel.
- [x] Testes automáticos cobrem: jogo sem compra com histórico carregado, jogo com compra e usuário sem histórico carregado (continua estimado).

---

# 09: Pacotes e reembolsos

**What to build:** compras de pacote têm o valor dividido entre os jogos proporcionalmente ao preço cheio de tabela de cada um. Compras reembolsadas são anuladas pelo estorno. Se um jogo reembolsado continuar na biblioteca por outro motivo, segue a regra desse outro motivo.

**Blocked by:** 03, 08.

**Acceptance criteria:**
- [x] Testes automáticos cobrem: pacote com jogos de preços diferentes, pacote com jogo gratuito, pacote com jogo sem preço de tabela (divisão igual), reembolso simples e jogo reembolsado e depois recebido de presente. Tests em tests/test_split.py, tests/test_purchase_history.py e tests/test_views.py, com valores calculados à mão.
- [x] A soma dos valores atribuídos aos jogos de um pacote é exatamente igual ao valor pago pelo pacote (sem perda de centavos). Método dos maiores restos, em centavos inteiros. Conferido nos dois bancos: 0 compras com soma das partes diferente do total.
- [x] Para 1 pacote e 1 reembolso reais, o resultado no banco confere com a página de Histórico de compras da Steam. Conferido pelo dono em 27/10/2026: o pacote de 03/01/2019 (Dead by Daylight + The Halloween Chapter, R$ 22,62 = 11,31 + 11,31) e o reembolso do The Witcher 3 de 17/09/2020 (compra riscada na página, compra e estorno se anulam).
- [x] Nenhum valor pago negativo existe no banco. Conferido nos dois bancos: itens, compras e valor líquido (net_purchases, que usa GREATEST(..., 0)).

---

# 10: Painel com preço pago

**What to build:** o Power BI passa a ler do Supabase e o custo por hora usa o preço pago quando existe no histórico e o estimado quando não existe, sempre mostrando a origem. O painel ganha a visão de horas jogadas por dia e por jogo.

**Blocked by:** 04, 05, 08b, 09.

**Acceptance criteria:**
- [ ] O Power BI se conecta ao Supabase em modo de importação e atualiza com um clique.
- [ ] Todo valor de custo exibido mostra se a origem é pago ou estimado.
- [ ] O painel mostra, por jogo, o valor pago e o gasto em compras no jogo separados. O ranking dos gratuitos e presentes ganha o gasto e o custo por hora, e o painel permite comparar gratuitos e pagos e informa que compras feitas fora da Steam não estão incluídas.
- [ ] O painel mostra o desconto obtido por compra e a economia total (spec, regra 21), com o aviso de que a comparação é com o preço cheio atual. Para 3 compras, o desconto bate com uma conta feita à mão (valor do histórico de compras e preço cheio da página da loja).
- [ ] O custo por hora de 3 jogos com preço pago bate com uma conta feita à mão (valor do histórico de compras dividido pelas horas exibidas na biblioteca da Steam).
- [ ] A visão de horas por dia mostra os dias coletados sem valores negativos.

---

# 11: Design interativo do painel

**What to build:** o painel ganha cara de aplicativo: tema escuro próprio aplicado em tudo, capa dos jogos no ranking, tela inicial com os números principais e botões de navegação entre as visões, filtros (período, origem do preço, grupo de horas), página de detalhe por jogo acessada com um clique e dicas ao passar o mouse com valor pago, horas e data de compra. Ao final, é gravado um GIF curto mostrando a interação, para o README.

**Blocked by:** 10.

**Acceptance criteria:**
- [ ] O tema é aplicado de forma uniforme em todas as páginas.
- [ ] O ranking exibe a capa de cada jogo.
- [ ] Clicar em um jogo abre a página de detalhe com a evolução das horas daquele jogo.
- [ ] Os filtros atualizam todas as visões da página.
- [ ] A navegação entre telas funciona só pelos botões, sem usar as abas do Power BI.
- [ ] O GIF de demonstração mostra filtros, clique no jogo e navegação, em menos de 30 segundos.
- [ ] Verificado se é possível publicar o painel em link aberto com a conta disponível, e a resposta registrada.

---

# 12: Validação final e README

**What to build:** todos os critérios de sucesso da especificação são conferidos contra a Steam e registrados, a coleta automática tem 7 dias seguidos de sucesso e o README final explica o projeto com diagrama do fluxo, decisões de design, prints e o GIF do painel, com um resumo curto em inglês no topo. É o fechamento da v1.

**Blocked by:** 06, 07, 11.

**Acceptance criteria:**
- [ ] Os 8 critérios de sucesso da especificação foram conferidos, e o resultado de cada um está registrado.
- [ ] O GitHub Actions mostra 7 execuções diárias seguidas com sucesso.
- [ ] O README explica em poucos segundos o que o projeto faz, mostra o fluxo dos dados, as regras de negócio principais e como rodar o ambiente local.
- [ ] O README tem prints do painel e o GIF de demonstração.
- [ ] Nenhuma credencial, SteamID em texto aberto ou histórico real existe em todo o histórico do repositório.
