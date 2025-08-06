# Verificação de Data Races via SAT Solver

Este repositório contém o projeto final para a disciplina de Sistemas Operacionais, focado na detecção de **Data Races** em programas concorrentes usando verificação formal. A ferramenta analisa o código C, gera uma fórmula CNF e utiliza a simulação de um SAT Solver para identificar potenciais condições de corrida em variáveis globais desprotegidas.

## Objetivo

O principal objetivo do projeto é demonstrar a viabilidade de usar técnicas de verificação formal com **SAT Solvers** para validar a correção de programas concorrentes. A ferramenta implementada verifica se o uso de mecanismos de sincronização (`pthread_mutex_lock`, `pthread_mutex_unlock`) é suficiente para proteger o acesso a variáveis globais, identificando e reportando quaisquer data races.

## Funcionalidades da Ferramenta

A ferramenta de análise estática de código C, desenvolvida em Python, realiza as seguintes etapas:

- **Análise da Árvore de Sintaxe Abstrata (AST):** Percorre a AST do código-fonte para identificar elementos-chave do programa.
- **Identificação de Variáveis Globais:** Mapeia todas as variáveis globais, que são candidatas a sofrerem condições de corrida.
- **Detecção de Operações Concorrentes:** Registra todas as chamadas a `pthread_mutex_lock` e `pthread_mutex_unlock`, além de todos os acessos (leitura e escrita) a variáveis globais dentro das funções.
- **Análise de Fluxo e Proteção:** Determina, por meio da análise do fluxo de execução, se cada acesso a uma variável global está protegido por um lock.
- **Geração de Fórmula CNF:** Converte o problema de detecção de data race em uma fórmula na **Forma Normal Conjuntiva (CNF)**, que é a entrada padrão para SAT Solvers.
- **Verificação com SAT Solver:** Simula a chamada a um SAT Solver (como o MiniSAT) para verificar se a fórmula CNF é satisfatível.
- **Extração de Contraexemplo:** Em caso de satisfatibilidade (`SAT`), a ferramenta extrai e exibe o contraexemplo, indicando a variável e as funções que causam o data race, e onde a proteção falhou.

## Estrutura do Repositório

- `src/`: Contém o código Python principal do analisador de AST e do gerador de CNF.
- `tests/`: Inclui arquivos de exemplo em C, sendo um com um data race intencional e outro sem, para validação da ferramenta.
- `docs/`: Documentação e relatório final do projeto.
- `img/`: Imagens e diagramas utilizados na documentação.

## Como Executar a Ferramenta

1.  Clone este repositório.
2.  Certifique-se de que o Python e as dependências (`pycparser`) estejam instalados.
3.  Modifique o caminho para o arquivo C na linha `c_file_path` no final do script `src/ast_parser.py`.
4.  Execute o script Python a partir do terminal:
    ```bash
    python3 src/ast_parser.py
    ```
