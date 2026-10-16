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
- [ ] As tabelas de usuários, jogos, biblioteca e snapshots existem no banco local com as chaves definidas na especificação.
- [ ] Após rodar o comando, o número de jogos no banco é igual ao total exibido no perfil da Steam.
- [ ] Para 5 jogos escolhidos ao acaso, as horas no banco batem com as horas exibidas na biblioteca da Steam.
- [ ] Rodar o comando duas vezes no mesmo dia mantém exatamente um snapshot por jogo naquele dia.
- [ ] Nenhum SteamID em texto aberto existe no banco.
- [ ] A chave da API é lida da variável de ambiente, nunca escrita no código.

---

# 03: Catálogo de preços

**What to build:** para cada jogo novo encontrado na biblioteca, o pipeline busca na loja da Steam o nome, o preço cheio de tabela em reais, o link da imagem de capa e se o jogo é gratuito, e registra isso uma única vez, junto com a data do registro. Jogos que já estão no catálogo não são consultados de novo.

**Blocked by:** 02.

**Acceptance criteria:**
- [ ] Todo jogo da biblioteca tem nome no catálogo.
- [ ] Para 5 jogos pagos, o preço registrado bate com o preço cheio exibido na página da loja (sem desconto).
- [ ] Jogos gratuitos estão marcados como gratuitos.
- [ ] Rodar o pipeline de novo não altera preços já registrados.
- [ ] Jogos sem preço na loja (fora de venda) ficam registrados sem preço e aparecem numa lista para decidir a regra (pergunta em aberto da especificação).
- [ ] As chamadas à loja respeitam um intervalo entre requisições para não sobrecarregar o serviço.

---

# 04: Primeiro painel com preço estimado

**What to build:** views no banco calculam o custo por hora de cada jogo usando o preço estimado e um Power BI simples, conectado ao banco local, mostra o ranking dos jogos com 1 hora ou mais, o grupo de jogos mal começados (menos de 1 hora) e o total de dinheiro parado em jogos com 0 horas. É a primeira versão ponta a ponta do projeto.

**Blocked by:** 03.

**Acceptance criteria:**
- [ ] O custo por hora é calculado e guardado para todos os jogos com horas maiores que zero.
- [ ] O ranking do painel mostra só jogos com 1 hora ou mais, com as horas e a origem do preço ao lado.
- [ ] O custo por hora de 3 jogos no painel bate com uma conta feita à mão (preço da loja dividido pelas horas exibidas na biblioteca da Steam).
- [ ] O total de dinheiro parado bate com a soma manual dos preços dos jogos com 0 horas.
- [ ] Jogos gratuitos aparecem com R$ 0 por hora.

---

# 05: Banco na nuvem

**What to build:** as mesmas tabelas criadas no Supabase, e o comando de coleta funcionando contra esse banco quando rodado manualmente. O ambiente local continua funcionando para desenvolvimento e testes, e escolher entre os dois depende só das variáveis de ambiente.

**Blocked by:** 02.

**Acceptance criteria:**
- [ ] A estrutura das tabelas no Supabase é idêntica à do banco local, criada pelos mesmos scripts.
- [ ] Uma coleta manual grava os dados no Supabase, e o número de jogos bate com o perfil da Steam.
- [ ] Trocar de banco não exige mudar nenhuma linha de código, só as variáveis de ambiente.
- [ ] As credenciais do Supabase não aparecem em nenhum arquivo do repositório.

---

# 06: Coleta automática diária

**What to build:** o GitHub Actions roda a coleta e o catálogo uma vez por dia, sozinho, gravando no Supabase. Cada execução fica registrada com horário, status e quantidade de jogos coletados. Se a execução falhar, o GitHub avisa por e-mail. Se o perfil de um usuário estiver privado, isso é registrado como falha daquele usuário e a coleta dos demais continua.

**Blocked by:** 03, 05.

**Acceptance criteria:**
- [ ] A coleta roda no horário agendado sem nenhuma ação manual, e a execução aparece na aba de ações do repositório.
- [ ] Cada execução gera um registro na tabela de execuções, com status e quantidade de jogos.
- [ ] Uma falha forçada de teste (por exemplo, chave inválida) gera registro de falha e e-mail do GitHub.
- [ ] Um usuário de teste com perfil privado gera registro de falha só para ele, sem derrubar a execução.
- [ ] A chave da API e as credenciais do banco estão guardadas como segredos do GitHub.

---

# 07: Horas por dia

**What to build:** uma view calcula quantas horas foram jogadas em cada dia, por jogo, pela diferença entre snapshots seguidos. Jogo novo começa a contar a partir do primeiro snapshot. Jogo que some da biblioteca mantém o histórico e é marcado como removido. Se o total de um jogo diminuir de um dia para o outro, aquele dia vai para a quarentena com o motivo, em vez de gerar horas negativas.

**Blocked by:** 02.

**Acceptance criteria:**
- [ ] Testes automáticos cobrem: dia normal, jogo novo, jogo removido, total que diminui e dia sem coleta.
- [ ] Nenhum valor de horas por dia é negativo.
- [ ] Com dados reais de pelo menos 2 dias, as horas de um jogo jogado no período batem com a diferença das horas exibidas na biblioteca da Steam nos dois dias (anotadas à mão).
- [ ] Todo registro na quarentena tem motivo preenchido.

---

# 08: Histórico de compras, casos simples

**What to build:** um script rodado no computador da pessoa lê o arquivo HTML do histórico de compras salvo da Steam e carrega no banco as compras normais e os presentes recebidos. Créditos de carteira, itens de jogo, linhas não reconhecidas e compras em outra moeda vão para a quarentena com o motivo. O arquivo HTML nunca sai do computador. O repositório público usa um arquivo de histórico fictício para os testes.

**Blocked by:** 02.

**Acceptance criteria:**
- [ ] Linhas aceitas mais linhas na quarentena somam exatamente o total de linhas do arquivo de histórico.
- [ ] Toda linha na quarentena tem motivo preenchido.
- [ ] Para 3 compras normais e 1 presente, o valor e a data no banco batem com a página de Histórico de compras da Steam.
- [ ] Presentes recebidos ficam com custo zero e marcados como presente.
- [ ] Testes automáticos usam um histórico fictício com todos os tipos de linha, e nenhum histórico real está no repositório.
- [ ] Carregar o mesmo arquivo duas vezes não duplica compras.

---

# 09: Pacotes e reembolsos

**What to build:** compras de pacote têm o valor dividido entre os jogos proporcionalmente ao preço cheio de tabela de cada um. Compras reembolsadas são anuladas pelo estorno. Se um jogo reembolsado continuar na biblioteca por outro motivo, segue a regra desse outro motivo.

**Blocked by:** 03, 08.

**Acceptance criteria:**
- [ ] Testes automáticos cobrem: pacote com jogos de preços diferentes, pacote com jogo gratuito, reembolso simples e jogo reembolsado e depois recebido de presente.
- [ ] A soma dos valores atribuídos aos jogos de um pacote é exatamente igual ao valor pago pelo pacote (sem perda de centavos).
- [ ] Para 1 pacote e 1 reembolso reais, o resultado no banco confere com a página de Histórico de compras da Steam.
- [ ] Nenhum valor pago negativo existe no banco.

---

# 10: Painel com preço pago

**What to build:** o Power BI passa a ler do Supabase e o custo por hora usa o preço pago quando existe no histórico e o estimado quando não existe, sempre mostrando a origem. O painel ganha a visão de horas jogadas por dia e por jogo.

**Blocked by:** 04, 05, 09.

**Acceptance criteria:**
- [ ] O Power BI se conecta ao Supabase em modo de importação e atualiza com um clique.
- [ ] Todo valor de custo exibido mostra se a origem é pago ou estimado.
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
