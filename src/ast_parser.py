from __future__ import print_function
import sys
import os

from pycparser import c_parser, c_ast, parse_file

# Linhas de inferência automática #
#_base_pycparser_path = os.path.dirname(os.path.abspath(__file__))
#_current_dir = os.path.dirname(os.path.abspath(__file__))
#_venv_path = os.path.join(_current_dir, '..', 'venv_os_project')
#_lib_path = next((os.path.join(_venv_path, 'lib', d) for d in os.listdir(os.path.join(_venv_path, 'lib')) if d.startswith('python')), None)

#if _lib_path:
   #PYCPARSER_UTILS_DIR = os.path.join(_lib_path, 'site-packages', 'pycparser', 'utils')
#else:from __future__ import print_function
import sys
import os

from pycparser import c_parser, c_ast, parse_file

# Linhas de inferência automática #
#_base_pycparser_path = os.path.dirname(os.path.abspath(__file__))
#_current_dir = os.path.dirname(os.path.abspath(__file__))
#_venv_path = os.path.join(_current_dir, '..', 'venv_os_project')
#_lib_path = next((os.path.join(_venv_path, 'lib', d) for d in os.listdir(os.path.join(_venv_path, 'lib')) if d.startswith('python')), None)

#if _lib_path:
   #PYCPARSER_UTILS_DIR = os.path.join(_lib_path, 'site-packages', 'pycparser', 'utils')
#else:
    #print("Atencao: nao foi possivel achar o caminho do pycparser/utils automaticamente. Verifique PYCPARSER_UTILS_DIR e o ajuste manualmente.")
    #PYCPARSER_UTILS_DIR = '/usr/local/lib/python3.X/dist-packages/pycparser/utils'

PYCPARSER_UTILS_DIR = '/home/user/Documents/FinalProject_OS_UFRR_Desc_16_2025/venv_os_project/lib64/python3.13/site-packages/pycparser/utils'

class AST_Visitor(c_ast.NodeVisitor):
    def __init__(self):
        self.global_variables = []
        self.lock_calls = []
        self.unlock_calls = []
        self.accesses = [] #vai servir pra gente armazenar todos os acessos que dizem a leitura/escrita
        self.current_function = None
        self.global_var_names = set() #armazenar os nomes das variaveis globais achadas/encontradas

    def visit_FuncDef(self, node): #ira visitar as definicoes de funcao
        self.current_function = node.decl.name
        # print(f" --FUNCAO-- Nome: {node.decl.name}, Linha: {node.decl.coord.line}")
        self.generic_visit(node) #visita os nos filhos
        self.current_function = None

    def visit_Decl(self, node): #vai identificar as variaveis globais, caso nao estejamos dentro de uma funcao e sera uma declaracao de variaveis
        if self.current_function is None and isinstance(node.type, (c_ast.TypeDecl, c_ast.PtrDecl, c_ast.ArrayDecl)):
            if hasattr(node.type, 'declname') and node.type.declname is not None:
                self.global_variables.append({
                    'name': node.name,
                    'line': node.coord.line,
                    'column': node.coord.column
                })
                self.global_var_names.add(node.name)
                # print(f" --VARIAVEL GLOBAL-- Nome: {node.name}, Linha: {node.coord.line}, Coluna: {node.coord.column}")

            #declaracao com inicializacao (como int x = u), 'u' sera uma leitura
            if node.init and isinstance(node.init, c_ast.ID) and node.init.name in self.global_var_names:
                self.accesses.append({
                    'variable': node.init.name,
                    'type':'read',
                    'function': self.current_function,
                    'line': node.coord.line,
                    'column': node.coord.column
                })
                #print(f" --LEITURA (INIT)-- Variavel: {node.init.name}, Linha: {node.coord.line}")
            self.generic_visit(node)
            
    def visit_Assignment(self, node): #aqui vamos capturar as operacoes de escrita
        if isinstance(node.lvalue, c_ast.ID) and node.lvalue.name in self.global_var_names:
            self.accesses.append({
                'variable': node.lvalue.name,
                'type': 'write',
                'function': self.current_function,
                'line': node.coord.line,
                'column': node.coord.column
            })
            # print(f" --ESCRITA-- Variavel: {node.lvalue.name}, Linha: {node.coord.line}")
        self._find_reads_in_expr(node.rvalue) #evitar duplicacao de logica se tiver outros nos que tenham IDs de leitura
        self.generic_visit(node)

    def _find_reads_in_expr(self, node): #encontrar leituras em expressoes
        if isinstance(node, c_ast.ID) and node.name in self.global_var_names:
            self.accesses.append({
                'variable': node.name,
                'type': 'read',
                'function': self.current_function,
                'line': node.coord.line,
                'column': node.coord.column
            })
            # print(f" --LEITURA-- Variavel: {node.name}, Linha: {node.coord.line}")
        elif isinstance(node, c_ast.UnaryOp):
            self._find_reads_in_expr(node.expr)
        elif isinstance(node, c_ast.BinaryOp):
            self._find_reads_in_expr(node.left)
            self._find_reads_in_expr(node.right)
        elif isinstance(node, c_ast.FuncCall):
            if node.args:
                for arg in node.args.exprs:
                    self._find_reads_in_expr(arg)
        elif isinstance(node, c_ast.ArrayRef):
            self._find_reads_in_expr(node.name)
            self._find_reads_in_expr(node.subscript)
        elif isinstance(node, c_ast.Cast):
            self._find_reads_in_expr(node.expr)
        elif isinstance(node, c_ast.TernaryOp):
            self._find_reads_in_expr(node.cond)
            self._find_reads_in_expr(node.iftrue)
            self._find_reads_in_expr(node.iffalse)

    def visit_FuncCall(self, node): #visita as chamadas de funcao
        if isinstance(node.name, c_ast.ID):
            mutex_arg = None
            if node.args and node.args.exprs:
                # Vai tentar extrair o nome do mutex do primeiro argumento
                # &my_lock ou my_lock
                if isinstance(node.args.exprs[0], c_ast.UnaryOp) and isinstance(node.args.exprs[0].expr, c_ast.ID):
                    mutex_arg = node.args.exprs[0].expr.name
                elif isinstance(node.args.exprs[0], c_ast.ID):
                    mutex_arg = node.args.exprs[0].name

            if node.name.name == 'pthread_mutex_lock':
                self.lock_calls.append({
                    'function': self.current_function,
                    'name': node.name.name,
                    'mutex': mutex_arg,
                    'line': node.coord.line,
                    'column': node.coord.column
                })
            elif node.name.name == 'pthread_mutex_unlock':
                self.unlock_calls.append({
                    'function': self.current_function,
                    'name': node.name.name,
                    'mutex': mutex_arg,
                    'line': node.coord.line,
                    'column': node.coord.column
                })
        #encontrar leituras nos argumentos da chamada de funcao
        if node.args:
            for arg in node.args.exprs:
                self._find_reads_in_expr(arg)

        self.generic_visit(node)

def analyze_program_flow(visitor):
    
    #consolida todos os eventos (locks, unlocks, acessos), ordena eles por funcao linha, e determina se os acessos as variaveis globais estão protegidos.
    
    events_by_function = {}

    for access in visitor.accesses:
        func = access['function']
        if func not in events_by_function:
            events_by_function[func] = []
        events_by_function[func].append({**access, 'event_type': 'access'})

    for lock in visitor.lock_calls:
        func = lock['function']
        if func not in events_by_function:
            events_by_function[func] = []
        events_by_function[func].append({**lock, 'event_type': 'lock'})

    for unlock in visitor.unlock_calls:
        func = unlock['function']
        if func not in events_by_function:
            events_by_function[func] = []
        events_by_function[func].append({**unlock, 'event_type': 'unlock'})

    analysis_result = {}

    for func, events in events_by_function.items():
        sorted_events = sorted(events, key=lambda x: x['line'])
        
        #rastreia o estado de cada mutex dentro do escopo da funcao
        current_mutex_states = {}
        
        processed_events = []
        for event in sorted_events:
            if event['event_type'] == 'lock':
                if event['mutex']:
                    current_mutex_states[event['mutex']] = 'locked'
            elif event['event_type'] == 'unlock':
                if event['mutex']:
                    current_mutex_states[event['mutex']] = 'unlocked'
            
            if event['event_type'] == 'access':
                #qualquer lock ativo protege qualquer global
                is_protected = any(state == 'locked' for state in current_mutex_states.values())
                event['protected'] = is_protected

            processed_events.append(event)
        
        analysis_result[func] = processed_events

    return analysis_result

def detect_potential_data_races(detailed_analysis):
    #vai identificar pares de acesso a mesma variavel global em funcoes distintas, na qual ao menous um acesso e escrita, bem como onde possui falta de protecao adequada
    #no contexto atual, estar com falta de protecao equivale a pelo menos um dos acessos no par ser marcado como desprotegido pela analise de fluxo local da funcao

    potential_races = []
    #estrutura para agrupar acessos por variavel e por funcao, isso inclui status de protecao
    accesses_by_variable_and_function = {}

    for func, events in detailed_analysis.items():
        for event in events:
            if event['event_type'] == 'access':
                var_name = event['variable']
                if var_name not in accesses_by_variable_and_function:
                    accesses_by_variable_and_function[var_name] = {}
                if func not in accesses_by_variable_and_function[var_name]:
                    accesses_by_variable_and_function[var_name][func] = []
                accesses_by_variable_and_function[var_name][func].append(event)

    for var, funcs_accessing_var in  accesses_by_variable_and_function.items():
        functions = list(funcs_accessing_var.keys())

        # caso a variavel seja acessada por pelo menos duas funcoes diferentes
        if len(functions) >= 2:
            # vai verificar todos os pares unicos de funcoes
            for i in range(len(functions)):
                for j in range(i + 1, len(functions)):
                    func1 = functions[i]
                    func2 = functions[j]

                    accesses_in_func1 = funcs_accessing_var[func1]
                    accesses_in_func2 = funcs_accessing_var[func2]

                    # Condicao 1: Ao menos um acesso no par e uma escrita
                    has_write = any(acc['type'] == 'write' for acc in accesses_in_func1 + accesses_in_func2)

                    # Condicao 2: AO menos um acesso no par e desprotegido
                    has_unprotected_access = any(not acc['protected'] for acc in accesses_in_func1 + accesses_in_func2)

                    # caso ambas sejam verdadeiras, sera um potencial data race
                    if has_write and has_unprotected_access:
                        potential_races.append({
                            'variable': var,
                            'function1': func1,
                            'function2': func2,
                            'accesses_func1': accesses_in_func1,
                            'accesses_func2': accesses_in_func2
                        })
    return potential_races

def generate_simplified_cnf(potential_races):
    # vai gerar uma formula CNF simplificada que satisfaz se um potencial data race e achado. Esse CNF apenas afirma que e detectado, ele nao mostrara a codificacao completa de data race para SAT, ele sera mais um exemplo de formato

    num_vars = 0
    clauses = []

    if potential_races:
        # caso qualquer potencial race seja visto, afirmaremos uma unica variavel proposicional (variavel 1)
        # o problema e satisfativel se um race for achado
        num_vars = 1
        clauses.append([1])

    cnf_output = f"p cnf {num_vars} {len(clauses)}\n"
    for clause in clauses:
        cnf_output += " ".join(map(str, clause)) + " 0\n"
    return cnf_output

def call_minisat(cnf_string):
    #simulara uma chamada ao MiniSAT
    #no contexto real, voce geralment escreveria um cnf_string para uma arquivo.cnf e logo executaria o MiniSAT via subprocess, lendo a saida.

    print("\n--- Simulação da Chamada ao MiniSAT ---")
    #vai verificar se o CNF gerado para a demo indica um data race
    if "p cnf 1 1\n1 0" in cnf_string:
        print("MiniSAT Output: SAT")
        print("v 1") # ex.: atribuicao SAT (variavel 1 e verdadeira)
        return "SAT", {'1': True}
    else:
        print("MiniSAT Output: UNSAT")
        print("v") # nenhuma atribuiçao se UNSAT
        return "UNSAT", {}

def extract_counterexample(minisat_assignment, potential_races):
    # vai extrair contraexemplos.
    # no contexto real, isso envolveria a interpretacao da atribuicao do SAT solver para reconstruir uma sequencia de eventos que leva ao data race

    print("\n--- Extração de Contraexemplo ---")
    #caso nossa variavel 'RaceDetected' (variavel 1) seja verdadeira
    if minisat_assignment.get('1', False):
        if potential_races:
            print("Contraexemplo Identificado: Um potencial data race foi detectado!!")
            for race in potential_races:
                print(f"  Variavel: '{race['variable']}'")
                print(f"  Funcoes Envolvidas: '{race['function1']}' e '{race['function2']}'")
                print("  Detalhes dos Acessos Desprotegidos/Envolvidos:")
                for acc in race['accesses_func1']:
                    protection_status = "Protegido" if acc['protected'] else "DESPROTEGIDO"
                    print(f"    - Função '{acc['function']}', Linha {acc['line']}: {acc['type']} '{acc['variable']}' ({protection_status})")
                for acc in race['accesses_func2']:
                    protection_status = "Protegido" if acc['protected'] else "DESPROTEGIDO"
                    print(f"    - Função '{acc['function']}', Linha {acc['line']}: {acc['type']} '{acc['variable']}' ({protection_status})")
                break
        else:
            print("Nenhum contraexemplo detalhado pode ser extraído para esta CNF simplificada.")
    else:
        print("Nenhum data race detectado (MiniSAT retornou UNSAT para a CNF simplificada).")

def parse_c_file(filename):
    fake_libc_include_path = os.path.join(PYCPARSER_UTILS_DIR, 'fake_libc_include') #vai permitir que lidemos/resolvamos includes como <pthread.h>
    print(f"Fazendo uso de fake_libc_include de: {fake_libc_include_path}")

    try:
        ast = parse_file(filename, use_cpp=True, cpp_args=['-E', '-nostdinc', '-I' + fake_libc_include_path])
        
        visitor = AST_Visitor()
        visitor.visit(ast)

        print("\n--- Sumario da Analise Bruta ---")
        print("Variaveis Globais Identificadas")
        if not visitor.global_variables:
            print(" Nenhuma variavel global encontrada.")
        for var in visitor.global_variables:
            print(f"  - {var['name']} (Linha: {var['line']}, Coluna: {var['column']})")
        
        detailed_analysis = analyze_program_flow(visitor)

        print("\n--- Analise Detalhada de Transicoes e Protecao por Locks ---")
        if not detailed_analysis:
            print(" Nenhuma funcao com operacoes concorrentes para analisar.")

        for func, events in detailed_analysis.items():
            print(f"\n[ Funcao: {func} ]")
            if not events:
                print("  Nenhum evento (acesso, lock, unlock) identificado.")
                continue
            
            current_mutex_states_for_print = {}
            for event in events:
                if event['event_type'] == 'lock':
                    if event['mutex']:
                        current_mutex_states_for_print[event['mutex']] = 'locked'
                    print(f"  - Linha {event['line']}: Chamada a '{event['name']}' (Mutex: {event.get('mutex', 'N/A')}). Estado do lock '{event.get('mutex', 'N/A')}' -> locked")
                elif event['event_type'] == 'unlock':
                    if event['mutex']:
                        current_mutex_states_for_print[event['mutex']] = 'unlocked'
                    print(f"  - Linha {event['line']}: Chamada a '{event['name']}' (Mutex: {event.get('mutex', 'N/A')}). Estado do lock '{event.get('mutex', 'N/A')}' -> unlocked")
                elif event['event_type'] == 'access':
                    protection_status = "Protegido" if event['protected'] else "DESPROTEGIDO"
                    print(f"  - Linha {event['line']}: Acesso '{event['type']}' a var '{event['variable']}'. Status: {protection_status}")

        print("\n--- Detecção de Potenciais Data Races ---")
        potential_races = detect_potential_data_races(detailed_analysis)
        if potential_races:
            print("Potenciais Data Races Encontrados:")
            for race in potential_races:
                print(f"  - Variável '{race['variable']}' acessada em '{race['function1']}' e '{race['function2']}'.")
                print("    (Pelo menos um acesso é escrita e pelo menos um é desprotegido)")
        else:
            print("Nenhum potencial data race desprotegido detectado.")

        # gerar formula CNF e simulacao da integracao com SAT Solver
        cnf_formula = generate_simplified_cnf(potential_races)
        print("\n--- Fórmula CNF Gerada (Simplificada para Demonstração) ---")
        print(cnf_formula)

        sat_result, minisat_assignment = call_minisat(cnf_formula)
        print(f"\nResultado do MiniSAT: {sat_result}")

        extract_counterexample(minisat_assignment, potential_races)

        print("\n------------------------------------------")

    except Exception as e:
        print(f"Erro ao parsear o arquivo {filename}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    c_file_path = os.path.join(os.path.dirname(__file__), '..', 'tests', 'example.c')
    print(f"Tentando parsear: {c_file_path}")
    parse_c_file(c_file_path)
    #print("Atencao: nao foi possivel achar o caminho do pycparser/utils automaticamente. Verifique PYCPARSER_UTILS_DIR e o ajuste manualmente.")
    #PYCPARSER_UTILS_DIR = '/usr/local/lib/python3.X/dist-packages/pycparser/utils'

PYCPARSER_UTILS_DIR = '/home/user/Documents/FinalProject_OS_UFRR_Desc_16_2025/venv_os_project/lib64/python3.13/site-packages/pycparser/utils'

class AST_Visitor(c_ast.NodeVisitor):
    def __init__(self):
        self.global_variables = []
        self.lock_calls = []
        self.unlock_calls = []
        self.accesses = [] #vai servir pra gente armazenar todos os acessos que dizem a leitura/escrita
        self.current_function = None
        self.global_var_names = set() #armazenar os nomes das variaveis globais achadas/encontradas

    def visit_FuncDef(self, node): #ira visitar as definicoes de funcao
        self.current_function = node.decl.name
        # print(f" --FUNCAO-- Nome: {node.decl.name}, Linha: {node.decl.coord.line}")
        self.generic_visit(node) #visita os nos filhos
        self.current_function = None

    def visit_Decl(self, node): #vai identificar as variaveis globais, caso nao estejamos dentro de uma funcao e sera uma declaracao de variaveis
        if self.current_function is None and isinstance(node.type, (c_ast.TypeDecl, c_ast.PtrDecl, c_ast.ArrayDecl)):
            if hasattr(node.type, 'declname') and node.type.declname is not None:
                self.global_variables.append({
                    'name': node.name,
                    'line': node.coord.line,
                    'column': node.coord.column
                })
                self.global_var_names.add(node.name)
                # print(f" --VARIAVEL GLOBAL-- Nome: {node.name}, Linha: {node.coord.line}, Coluna: {node.coord.column}")

            #declaracao com inicializacao (como int x = u), 'u' sera uma leitura
            if node.init and isinstance(node.init, c_ast.ID) and node.init.name in self.global_var_names:
                self.accesses.append({
                    'variable': node.init.name,
                    'type':'read',
                    'function': self.current_function,
                    'line': node.coord.line,
                    'column': node.coord.column
                })
                #print(f" --LEITURA (INIT)-- Variavel: {node.init.name}, Linha: {node.coord.line}")
            self.generic_visit(node)
            
    def visit_Assignment(self, node): #aqui vamos capturar as operacoes de escrita
        if isinstance(node.lvalue, c_ast.ID) and node.lvalue.name in self.global_var_names:
            self.accesses.append({
                'variable': node.lvalue.name,
                'type': 'write',
                'function': self.current_function,
                'line': node.coord.line,
                'column': node.coord.column
            })
            # print(f" --ESCRITA-- Variavel: {node.lvalue.name}, Linha: {node.coord.line}")
        self._find_reads_in_expr(node.rvalue) #evitar duplicacao de logica se tiver outros nos que tenham IDs de leitura
        self.generic_visit(node)

    def _find_reads_in_expr(self, node): #encontrar leituras em expressoes
        if isinstance(node, c_ast.ID) and node.name in self.global_var_names:
            self.accesses.append({
                'variable': node.name,
                'type': 'read',
                'function': self.current_function,
                'line': node.coord.line,
                'column': node.coord.column
            })
            # print(f" --LEITURA-- Variavel: {node.name}, Linha: {node.coord.line}")
        elif isinstance(node, c_ast.UnaryOp):
            self._find_reads_in_expr(node.expr)
        elif isinstance(node, c_ast.BinaryOp):
            self._find_reads_in_expr(node.left)
            self._find_reads_in_expr(node.right)
        elif isinstance(node, c_ast.FuncCall):
            if node.args:
                for arg in node.args.exprs:
                    self._find_reads_in_expr(arg)
        elif isinstance(node, c_ast.ArrayRef):
            self._find_reads_in_expr(node.name)
            self._find_reads_in_expr(node.subscript)
        elif isinstance(node, c_ast.Cast):
            self._find_reads_in_expr(node.expr)
        elif isinstance(node, c_ast.TernaryOp):
            self._find_reads_in_expr(node.cond)
            self._find_reads_in_expr(node.iftrue)
            self._find_reads_in_expr(node.iffalse)

    def visit_FuncCall(self, node): #visita as chamadas de funcao
        if isinstance(node.name, c_ast.ID):
            if node.name.name == 'pthread_mutex_lock':
                self.lock_calls.append({
                    'function': self.current_function,
                    'name': node.name.name,
                    'line': node.coord.line,
                    'column': node.coord.column
                })
                # print(f" --CHAMADA LOCK-- {node.name.name} na função '{self.current_function}' (Linha: {node.coord.line}, Coluna: {node.coord.column})")
            elif node.name.name == 'pthread_mutex_unlock':
                self.unlock_calls.append({
                    'function': self.current_function,
                    'name': node.name.name,
                    'line': node.coord.line,
                    'column': node.coord.column
                })
                # print(f" --CHAMADA UNLOCK-- {node.name.name} na função '{self.current_function}' (Linha: {node.coord.line}, Coluna: {node.coord.column})")
        
        #encontrar leituras nos argumentos da chamada de funcao
        if node.args:
            for arg in node.args.exprs:
                self._find_reads_in_expr(arg)

        self.generic_visit(node)

def analyze_program_flow(visitor):
    """
    Consolida todos os eventos (locks, unlocks, acessos), ordena-os por função
    e linha, e determina se os acessos a variáveis globais estão protegidos.
    """
    events_by_function = {}

    for access in visitor.accesses:
        func = access['function']
        if func not in events_by_function:
            events_by_function[func] = []
        events_by_function[func].append({**access, 'event_type': 'access'})

    for lock in visitor.lock_calls:
        func = lock['function']
        if func not in events_by_function:
            events_by_function[func] = []
        events_by_function[func].append({**lock, 'event_type': 'lock'})

    for unlock in visitor.unlock_calls:
        func = unlock['function']
        if func not in events_by_function:
            events_by_function[func] = []
        events_by_function[func].append({**unlock, 'event_type': 'unlock'})

    analysis_result = {}

    for func, events in events_by_function.items():
        sorted_events = sorted(events, key=lambda x: x['line'])
        
        # assume que o lock está inicialmente liberado (unlocked)
        lock_state = 'unlocked'
        
        processed_events = []
        for event in sorted_events:
            if event['event_type'] == 'access':
                event['protected'] = (lock_state == 'locked')
            
            # atualiza o estado do lock
            if event['event_type'] == 'lock':
                lock_state = 'locked'
            elif event['event_type'] == 'unlock':
                lock_state = 'unlocked'
            
            processed_events.append(event)
        
        analysis_result[func] = processed_events

    return analysis_result


def parse_c_file(filename):
    fake_libc_include_path = os.path.join(PYCPARSER_UTILS_DIR, 'fake_libc_include') #vai permitir que lidemos/resolvamos includes como <pthread.h>
    print(f"Fazendo uso de fake_libc_include de: {fake_libc_include_path}")

    try:
        ast = parse_file(filename, use_cpp=True, cpp_args=['-E', '-nostdinc', '-I' + fake_libc_include_path])
        
        visitor = AST_Visitor()
        visitor.visit(ast)

        print("\n--- Sumario da Analise Bruta ---")
        print("Variaveis Globais Identificadas")
        if not visitor.global_variables:
            print(" Nenhuma variavel global encontrada.")
        for var in visitor.global_variables:
            print(f"  - {var['name']} (Linha: {var['line']}, Coluna: {var['column']})")
        
        detailed_analysis = analyze_program_flow(visitor)

        print("\n--- Analise Detalhada de Transicoes e Protecao por Locks ---")
        if not detailed_analysis:
            print(" Nenhuma funcao com operacoes concorrentes para analisar.")

        for func, events in detailed_analysis.items():
            print(f"\n[ Funcao: {func} ]")
            if not events:
                print("  Nenhum evento (acesso, lock, unlock) identificado.")
                continue
            
            print("  Estado inicial do Lock: unlocked")
            for event in events:
                if event['event_type'] == 'access':
                    print(f"  - Linha {event['line']}: Acesso '{event['type']}' a var '{event['variable']}'. Protegido: {event['protected']}")
                elif event['event_type'] == 'lock':
                    print(f"  - Linha {event['line']}: Chamada a '{event['name']}'. Estado do lock -> locked")
                elif event['event_type'] == 'unlock':
                    print(f"  - Linha {event['line']}: Chamada a '{event['name']}'. Estado do lock -> unlocked")

        print("\n------------------------------------------")

    except Exception as e:
        print(f"Erro ao parsear o arquivo {filename}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    c_file_path = os.path.join(os.path.dirname(__file__), '..', 'tests', 'example.c')
    print(f"Tentando parsear: {c_file_path}")
    parse_c_file(c_file_path)
