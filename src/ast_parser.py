from __future__ import print_function
import sys
import os
from itertools import combinations

#dependencias (pycparser e pysat)
from pycparser import c_parser, c_ast, parse_file
from pysat.solvers import Glucose3
from pysat.formula import CNF

# O caminho para o fake_libc_include do pycparser precisa ser configurado corretamente
# ATENCAO: Se o script nAo funcionar, provavelmente seja necessario ajustar este caminho.
PYCPARSER_UTILS_DIR = '/home/user/Documents/FinalProject_OS_UFRR_Desc_16_2025/venv_os_project/lib64/python3.13/site-packages/pycparser/utils'

class AST_Visitor(c_ast.NodeVisitor):
    def __init__(self):
        self.global_variables = []
        self.lock_calls = []
        self.unlock_calls = []
        self.accesses = [] #vai servir pra gente armazenar todos os acessos que dizem a leitura/escrita
        self.current_function = None
        self.global_var_names = set()
        self.thread_functions = set()  #armazenar os nomes das variaveis globais achadas/encontradas

    def visit_FuncDef(self, node): #ira visitar as definicoes de funcao
        self.current_function = node.decl.name
        # print(f" --FUNCAO-- Nome: {node.decl.name}, Linha: {node.decl.coord.line}")
        self.generic_visit(node) #visita os nos filhos
        self.current_function = None

    def visit_Decl(self, node):
        # vai achar as declaracao de variaveis globais (elas ocorrem fora da funcao)
        if self.current_function is None and isinstance(node.type, (c_ast.TypeDecl, c_ast.PtrDecl, c_ast.ArrayDecl)):
            if hasattr(node.type, 'declname') and node.type.declname is not None:
                self.global_variables.append({'name': node.name, 'line': node.coord.line, 'column': node.coord.column})
                self.global_var_names.add(node.name)
        
        # isso vai achar nossas leituras na inicializacao de QUALQUER variavel, seja ela global ou local
        if node.init:
            self._find_reads_in_expr(node.init)
        #print(f" --LEITURA (INIT)-- Variavel: {node.init.name}, Linha: {node.coord.line}")
        self.generic_visit(node)

    def visit_Assignment(self, node): #aqui vamos capturar as operacoes de escrita

        if isinstance(node.lvalue, c_ast.ID) and node.lvalue.name in self.global_var_names:
            self.accesses.append({'variable': node.lvalue.name, 'type': 'write', 'function': self.current_function, 'line': node.coord.line, 'column': node.coord.column})
        
        # print(f" --ESCRITA-- Variavel: {node.lvalue.name}, Linha: {node.coord.line}")
        # vai encontrar leiturar no lado direito da atribuicao
        self._find_reads_in_expr(node.rvalue) #evitar duplicacao de logica se tiver outros nos que tenham IDs de leitura
        self.generic_visit(node)

    def visit_If(self, node):
        # vai encontrar leituras na condicao do if
        if node.cond:
            self._find_reads_in_expr(node.cond)
        
        # continua a visita nos blocos if/else
        self.generic_visit(node)

    def _find_reads_in_expr(self, node):  #encontrar leituras em expressoes
        if isinstance(node, c_ast.ID) and node.name in self.global_var_names:
            self.accesses.append({'variable': node.name, 'type': 'read', 'function': self.current_function, 'line': node.coord.line, 'column': node.coord.column})
            # print(f" --LEITURA-- Variavel: {node.name}, Linha: {node.coord.line}")
        elif isinstance(node, c_ast.BinaryOp):
            self._find_reads_in_expr(node.left)
            self._find_reads_in_expr(node.right)
        elif isinstance(node, c_ast.UnaryOp):
            self._find_reads_in_expr(node.expr)
        elif isinstance(node, c_ast.FuncCall):
            if node.args:
                for arg in node.args.exprs:
                    self._find_reads_in_expr(arg)

    def visit_FuncCall(self, node): #visita as chamadas de funcao
        if isinstance(node.name, c_ast.ID):
            func_name = node.name.name
            
            # detecta quais funcoes sao usadas para criar threads
            if func_name == 'pthread_create':
                if node.args and len(node.args.exprs) > 2:
                    thread_func_node = node.args.exprs[2]
                    if isinstance(thread_func_node, c_ast.ID):
                        self.thread_functions.add(thread_func_node.name)
            
            mutex_arg = None
            if node.args and node.args.exprs:
                # caso nao houver argumentos, isso evitara o erro
                first_arg = node.args.exprs[0]
                if isinstance(first_arg, c_ast.UnaryOp) and isinstance(first_arg.expr, c_ast.ID):
                    mutex_arg = first_arg.expr.name
                elif isinstance(first_arg, c_ast.ID):
                    mutex_arg = first_arg.name

            if func_name == 'pthread_mutex_lock':
                self.lock_calls.append({'function': self.current_function, 'name': func_name, 'mutex': mutex_arg, 'line': node.coord.line})
            elif func_name == 'pthread_mutex_unlock':
                self.unlock_calls.append({'function': self.current_function, 'name': func_name, 'mutex': mutex_arg, 'line': node.coord.line})
        
        #encontrar leituras nos argumentos da chamada de funcao (recursivo)
        if node.args:
            for arg in node.args.exprs:
                self._find_reads_in_expr(arg)
        
        self.generic_visit(node)


def analyze_program_flow(visitor):
    #consolida todos os eventos (locks, unlocks, acessos), ordena eles por funcao linha, e determina se os acessos as variaveis globais estão protegidos.

    events_by_function = {}
    for access in visitor.accesses:
        func = access['function']
        if func not in events_by_function: events_by_function[func] = []
        events_by_function[func].append({**access, 'event_type': 'access'})
    for lock in visitor.lock_calls:
        func = lock['function']
        if func not in events_by_function: events_by_function[func] = []
        events_by_function[func].append({**lock, 'event_type': 'lock'})
    for unlock in visitor.unlock_calls:
        func = unlock['function']
        if func not in events_by_function: events_by_function[func] = []
        events_by_function[func].append({**unlock, 'event_type': 'unlock'})

    analysis_result = {}
    for func, events in events_by_function.items():
        sorted_events = sorted(events, key=lambda x: x['line'])
        current_mutex_states = {}
        processed_events = []
        for event in sorted_events:
            if event['event_type'] == 'lock':
                if event['mutex']: current_mutex_states[event['mutex']] = 'locked'
            elif event['event_type'] == 'unlock':
                if event['mutex']: current_mutex_states[event['mutex']] = 'unlocked'
            if event['event_type'] == 'access':
                is_protected = any(state == 'locked' for state in current_mutex_states.values())
                event['protected'] = is_protected
            processed_events.append(event)
        analysis_result[func] = processed_events
    return analysis_result

def parse_c_file(filename):
    # sera realizado o parse de um arquivo C e retornara a AST. Se der erro, vai retornar None
    fake_libc_include_path = os.path.join(PYCPARSER_UTILS_DIR, 'fake_libc_include')
    try:
        ast = parse_file(filename, use_cpp=True, cpp_args=['-E', '-nostdinc', '-I' + fake_libc_include_path])
        return ast
    except Exception as e:
        print(f"Erro ao fazer o parse do arquivo {filename}: {e}", file=sys.stderr)
        return None

def analyze_ast(ast):
    # vai pegar nossa AST, executa o visitor e a analise de fluxo. Ele vai retornar os detalhes do resultado e as funcoes de thread
    visitor = AST_Visitor()
    visitor.visit(ast)
    detailed_analysis = analyze_program_flow(visitor)
    return detailed_analysis, visitor.thread_functions

def print_cnf_formula(formula):
    # Aqui onde receberemos um objeto CNF e o printaremos no formato DIMACS padrao
    print("\n--- Visualizacao da Formula CNF ---")
    num_vars = formula.nv
    num_clauses = len(formula.clauses)
    
    print(f"p cnf {num_vars} {num_clauses}")
    
    if not formula.clauses:
        print("c A formula esta vazia (trivialmente SATISFATIVEL).")
    else:
        for clause in formula.clauses:
            clause_str = " ".join(map(str, clause))
            print(f"{clause_str} 0")
    print("------------------------------------")

def solve_and_report(detailed_analysis, thread_functions):
    # usaremos PySAT para construir as regras de seguranca e testar os pares de acessos para identificar um data race
    if not thread_functions:
        print("\nAviso: Nenhuma chamada a 'pthread_create' foi encontrada. Não e possível detectar data races.")
        return

    print(f"\nFuncoes de thread identificadas: {list(thread_functions)}")

    # considera apenas os acessos que ocorrem dentro das funcoes de thread identificadas
    all_accesses = [
        event for events in detailed_analysis.values() 
        for event in events 
        if event['event_type'] == 'access' and event.get('function') in thread_functions
    ]

    if len(all_accesses) < 2:
        print("Nao ha acessos concorrentes suficientes nas funcoes de thread para um data race.")
        return

    access_map = {i + 1: access for i, access in enumerate(all_accesses)}
    
    formula = CNF()
    for v1, v2 in combinations(access_map.keys(), 2):
        acc1, acc2 = access_map[v1], access_map[v2]
        
        if acc1['type'] == 'read' and acc2['type'] == 'read':
            formula.append([-v1, -v2])
            
        if acc1['protected'] and acc2['protected']:
            formula.append([-v1, -v2])

    print_cnf_formula(formula)

    print("\n--- Verificacao Formal com PySAT ---")
    
    found_race = False
    with Glucose3(bootstrap_with=formula.clauses) as solver:
        candidate_pairs = []
        for v1, v2 in combinations(access_map.keys(), 2):
            acc1, acc2 = access_map[v1], access_map[v2]
            
            # um par sera concorrente se acessar a mesma variavel, bem como os acessos estão em funcoes de thread diferentes ou os acessos estao na mesma funcao, e essa funcao é uma funcao de thread
            is_concurrent = (acc1['function'] != acc2['function']) or \
                            (acc1['function'] == acc2['function'] and acc1['function'] in thread_functions)

            if acc1['variable'] == acc2['variable'] and is_concurrent:
                candidate_pairs.append((v1, v2))
        
        for v1, v2 in candidate_pairs:
            if solver.solve(assumptions=[v1, v2]):
                print("Resultado do Solver: SATISFATIVEL (Potencial Data Race Encontrado!)")
                print("\nContraexemplo Encontrado (Acessos que formam o Data Race):")
                
                access1 = access_map[v1]
                status1 = "Protegido" if access1['protected'] else "DESPROTEGIDO"
                print(f"  - Em '{access1['function']}' (Linha {access1['line']}): "
                      f"Acesso de '{access1['type']}' à variável '{access1['variable']}' ({status1})")

                access2 = access_map[v2]
                status2 = "Protegido" if access2['protected'] else "DESPROTEGIDO"
                print(f"  - Em '{access2['function']}' (Linha {access2['line']}): "
                      f"Acesso de '{access2['type']}' à variável '{access2['variable']}' ({status2})")
                
                found_race = True
                break

    if not found_race:
        print("Resultado do Solver: INSATISFATIVEL (Seguro)")
        print("Nenhum data race que satisfaca as condicoes foi encontrado.")


def check_program(c_file_path):
    # onde faremos a verificacao do programa
    if not os.path.isfile(c_file_path):
        print(f"Erro: O arquivo '{c_file_path}' nao foi encontrado.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Analisando o arquivo: {c_file_path}\n")
    
    ast = parse_c_file(c_file_path)
    if not ast:
        return
        
    detailed_analysis, thread_functions = analyze_ast(ast)
    
    print("--- Analise Detalhada de Transicoes e Protecao por Locks ---")
    if not detailed_analysis:
        print("Nenhuma funcao com operacoes concorrentes para analisar.")
    for func, events in detailed_analysis.items():
        print(f"\n[ Funcao: {func} ]")
        if not events: print("  Nenhum evento (acesso, lock, unlock) identificado."); continue
        for event in events:
            if event['event_type'] == 'access':
                status = "Protegido" if event['protected'] else "DESPROTEGIDO"
                print(f"  - Linha {event['line']}: Acesso '{event['type']}' a var '{event['variable']}'. Status: {status}")
            else:
                print(f"  - Linha {event['line']}: Chamada a '{event['name']}' (Mutex: {event.get('mutex', 'N/A')})")

    solve_and_report(detailed_analysis, thread_functions)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Erro: O caminho para o arquivo C nao foi fornecido.", file=sys.stderr)
        print("Uso: python3 ast_parser.py <caminho_para_o_arquivo.c>", file=sys.stderr)
        sys.exit(1)

    c_file_path = sys.argv[1]
    check_program(c_file_path)
