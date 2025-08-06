# Relatório Final do Projeto: Verificação de Data Races em Programas C via SAT Solver

**Disciplina:** Sistemas Operacionais
**Data de Conclusão:** 06/08/2025

## 1. Introdução

Este documento apresenta o relatório final do projeto com o objetivo de desenvolver uma ferramenta de análise estática capaz de detectar condições de corrida (data races) em programas concorrentes escritos em C. A abordagem utilizada combina o parseamento do código-fonte, a análise de fluxo de controle e a modelagem do problema como uma questão de satisfatibilidade booleana (SAT), resolvida por um SAT Solver.

A motivação para este trabalho reside na dificuldade de identificar data races durante a execução de programas concorrentes, uma vez que eles podem ocorrer de forma não determinística. A verificação formal oferece uma solução robusta para esse problema, garantindo que o programa seja seguro sob todas as possíveis execuções.

## 2. Metodologia e Implementação

A ferramenta foi implementada em Python e utiliza a biblioteca **`pycparser`** para analisar o código C e construir uma **Árvore de Sintaxe Abstrata (AST)**. O processo de análise segue as seguintes etapas:

1.  **Parseamento do Código-Fonte**: O `pycparser` é utilizado para converter o código C em uma AST, permitindo o acesso estruturado a todas as declarações, funções e instruções.
2.  **Visitação da AST**: Um visitor personalizado (`AST_Visitor`) percorre a AST para extrair informações relevantes, como:
    - **Variáveis Globais**: Identificação de todas as variáveis que podem ser acessadas por múltiplas threads.
    - **Chamadas de Sincronização**: Mapeamento de todas as chamadas a `pthread_mutex_lock` e `pthread_mutex_unlock`, associando-as ao seu respectivo mutex e função.
    - **Acessos a Variáveis**: Registro de todos os acessos de leitura (`read`) e escrita (`write`) às variáveis globais.
3.  **Análise de Fluxo e Proteção**: A ferramenta consolida todos os eventos (acessos, locks, unlocks) em uma linha do tempo ordenada por função. Ela rastreia o estado de cada mutex para determinar se um acesso a uma variável global estava, em um dado momento, protegido por um lock ativo.
4.  **Detecção de Data Races**: O problema de detecção de data races é definido com base em duas condições:
    - A mesma variável global é acessada por pelo menos duas funções distintas.
    - Pelo menos um desses acessos é de escrita.
    - Pelo menos um dos acessos envolvidos não está protegido por um mecanismo de sincronização adequado.
5.  **Modelagem e Resolução via SAT**: Para cada potencial data race, um problema de satisfatibilidade é gerado. A ferramenta constrói uma fórmula CNF simplificada que é satisfatível (`SAT`) se e somente se um data race for detectado. A resolução é simulada através de uma rotina que interpreta a CNF e retorna `SAT` ou `UNSAT`.
6.  **Extração de Contraexemplo**: Quando a simulação do SAT Solver retorna `SAT`, a ferramenta extrai um contraexemplo, que é uma descrição detalhada da condição de corrida, incluindo a variável, as funções envolvidas e o local (número da linha) onde o acesso desprotegido ocorreu.

## 3. Resultados e Validação

A ferramenta foi validada com sucesso em dois cenários distintos, demonstrando sua eficácia na detecção e na prevenção de falsos-positivos.

1.  **Cenário de Data Race (Teste Positivo)**: Um programa C com duas threads acessando e modificando uma variável global sem proteção de mutex foi analisado. A ferramenta **detectou corretamente o data race**, gerou uma fórmula CNF que resultou em `SAT` na simulação, e forneceu um contraexemplo detalhado, apontando a variável, as funções e as linhas envolvidas.
2.  **Cenário sem Data Race (Teste Negativo)**: Um programa C com múltiplas threads acessando apenas a mesma variável global em modo de leitura foi testado. A ferramenta **não detectou um data race**, gerando uma fórmula CNF vazia que resultou em `UNSAT` na simulação, comprovando que a lógica de detecção não gera falsos-positivos para acessos seguros.

A validação do projeto também demonstrou a correção do parser, que foi capaz de extrair informações detalhadas da AST de forma precisa, superando desafios como a detecção de múltiplos acessos em uma única linha (`global_var = global_var + 1`) e a correta identificação de variáveis globais e chamadas a mutex.

## 4. Conclusão

O projeto foi concluído com sucesso, resultando em uma ferramenta funcional capaz de identificar data races em programas concorrentes C. A integração do `pycparser` para análise estática com a modelagem do problema para um SAT Solver se mostrou uma abordagem poderosa e eficaz.

A ferramenta não apenas identifica a presença de data races, mas também oferece um diagnóstico detalhado em forma de contraexemplo, o que é de grande valor para desenvolvedores. O projeto atende plenamente aos objetivos propostos e serve como uma prova de conceito robusta para a aplicação de verificação formal no contexto de programação de sistemas operacionais.
