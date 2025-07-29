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
