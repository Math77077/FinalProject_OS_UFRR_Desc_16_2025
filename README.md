Este repositório contém o projeto final para a disciplina de Sistemas Operacionais, focado na verificação de Data Races em programas concorrentes via SAT Solver.

## Objetivo

O projeto tem como objetivo investigar se o uso de mecanismos de sincronização (locks, mutexes, semáforos) é suficiente para evitar data races em programas concorrentes, utilizando verificação formal com lógica proposicional e resolução com SAT Solvers.

## Estrutura do Projeto

- `src/`: Contém o código Python do analisador estático e do gerador de CNF.
- `tests/`: Contém exemplos de código C para teste da ferramenta.
- `docs/`: Contém o relatório final e outras documentações.
- `img/`: Contém imagens relacionadas ao projeto e que estão presentes na documentação.

## Status - 22 de Julho de 2025

- **Ambiente de desenvolvimento configurado:** Python e `pycparser` estão instalados e prontos para uso em ambiente Linux Fedora.
- **Análise Estática Inicial Concluída:** A ferramenta já consegue parsear arquivos C e extrair informações básicas da Árvore de Sintaxe Abstrata (AST), como declarações de funções e variáveis, chamadas a `pthread_mutex_lock`/`unlock` e operações de atribuição (escrita).
- **Relatório de Status Disponível:** Um relatório detalhado com o progresso, exemplos de código e a saída da análise inicial foi adicionado à pasta `docs/`.

## Status Atual (24 de Julho de 2025)

- **Ambiente de desenvolvimento configurado:** Python e `pycparser` estão instalados e prontos para uso em ambiente Linux Fedora.
- **Análise Estática Aprimorada:** A ferramenta agora consegue parsear arquivos C e extrair informações detalhadas da Árvore de Sintaxe Abstrata (AST), incluindo:
  - Declarações de variáveis globais.
  - Chamadas a `pthread_mutex_lock` e `pthread_mutex_unlock`.
  - **Identificação de acessos (leitura e escrita) a variáveis globais, com distinção clara entre os tipos de acesso.**
  - **Associação de cada acesso e operação de lock/unlock à sua respectiva função (representando a thread de execução).**
- **Modelagem de Transições (Fase Inicial):** Os dados extraídos estão sendo estruturados em um formato inicial que representa as transições do programa concorrente, preparando para a etapa de codificação das regras para o SAT Solver.
- **Relatório de Status Disponível:** Um relatório detalhado com o progresso, exemplos de código e a saída da análise aprimorada foi adicionado à pasta `docs/`.

## Próximos Passos

Até a próxima atualização de status (Terça-feira, 29 de Julho), o foco será em:

- **Modelagem Completa de Transições:** Refinar e consolidar a estrutura de dados para representar todas as transições do programa concorrente de forma abrangente, incluindo o status inicial do lock.
- **Início da Associação de Acessos a Locks:** Começar a implementar a lógica para determinar se um acesso a uma variável está "protegido" por um lock, rastreando o estado dos locks ativos ao percorrer a AST.
