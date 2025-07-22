Este repositório contém o projeto final para a disciplina de Sistemas Operacionais, focado na verificação de Data Races em programas concorrentes via SAT Solver.

## Objetivo

O projeto tem como objetivo investigar se o uso de mecanismos de sincronização (locks, mutexes, semáforos) é suficiente para evitar data races em programas concorrentes, utilizando verificação formal com lógica proposicional e resolução com SAT Solvers.

## Estrutura do Projeto

- `src/`: Contém o código Python do analisador estático e do gerador de CNF.
- `tests/`: Contém exemplos de código C para teste da ferramenta.
- `docs/`: Contém o relatório final e outras documentações.
- `img/`: Contém imagens relacionadas ao projeto e que estão presentes na documentação.

## Status Atual (22 de Julho de 2025)

- **Ambiente de desenvolvimento configurado:** Python e `pycparser` estão instalados e prontos para uso em ambiente Linux Fedora.
- **Análise Estática Inicial Concluída:** A ferramenta já consegue parsear arquivos C e extrair informações básicas da Árvore de Sintaxe Abstrata (AST), como declarações de funções e variáveis, chamadas a `pthread_mutex_lock`/`unlock` e operações de atribuição (escrita).
- **Relatório de Status Disponível:** Um relatório detalhado com o progresso, exemplos de código e a saída da análise inicial foi adicionado à pasta `docs/`.

## Próximos Passos

Até a próxima atualização de status (Quinta-feira, 24 de Julho), o foco será em:

- Identificação Detalhada de Acessos: Aprimorar a lógica para distinguir claramente entre operações de leitura e escrita em variáveis globais.

- Associação de Acessos a Threads: Mapear cada acesso (leitura/escrita) e operação de lock/unlock à sua respectiva thread ou função.

- Modelagem de Transições: Começar a estruturar os dados extraídos em um formato que represente as transições do programa concorrente, preparando para a etapa de codificação de regras para o SAT Solver.
