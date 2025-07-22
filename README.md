Este repositório contém o projeto final para a disciplina de Sistemas Operacionais, focado na verificação de Data Races em programas concorrentes via SAT Solver.

## Objetivo

O projeto tem como objetivo investigar se o uso de mecanismos de sincronização (locks, mutexes, semáforos) é suficiente para evitar data races em programas concorrentes, utilizando verificação formal com lógica proposicional e resolução com SAT Solvers.

## Estrutura do Projeto

* `src/`: Contém o código Python do analisador estático e do gerador de CNF.
* `tests/`: Contém exemplos de código C para teste da ferramenta.
* `docs/`: Contém o relatório final e outras documentações.

## Status Atual (22 de Julho de 2025)

* Ambiente de desenvolvimento configurado (Python e `pycparser`).
* Capacidade inicial de parsear arquivos C e explorar a Árvore de Sintaxe Abstrata (AST).

## Próximos Passos

* Implementar a identificação de variáveis globais e chamadas de funções de sincronização (`pthread_mutex_lock`, `pthread_mutex_unlock`).
* Detalhes sobre como rodar a ferramenta e exemplos de uso serão adicionados em breve.
