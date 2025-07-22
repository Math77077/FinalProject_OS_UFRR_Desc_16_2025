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
    def visit_FuncDef(self, node): #ira visitar as definicoes de funcao
        print(f" --FUNCAO-- Nome: {node.decl.name}, Linha: {node.decl.coord.line}")
        self.generic_visit(node) #visita os nos filhos

    def visit_Decl(self, node): #vai visitar as declaracoes, como variaveis
        if node.name == 'global_var':
            print(f" --DECLARACAO-- Variavel: {node.name}, Linha: {node.coord.line}")
        self.generic_visit(node)

    def visit_FuncCall(self, node): #visita as chamadas de funcao
        if isinstance(node.name, c_ast.ID):
            if node.name.name == 'pthread_mutex_lock':
                print(f" --CHAMADA-- pthread_mutex_lock na linha: {node.coord.line}")
            elif node.name.name == 'pthread_mutex_unlock':
                print(f" --CHAMADA-- pthread_mutex_unlock na linha: {node.coord.line}")
            elif node.name.name == 'printf':
                print(f" --CHAMADA-- printf na linha: {node.coord.line}")
        self.generic_visit(node)

    def visit_Assignment(self, node): #aqui vamos capturar as operacoes de escrita
        if isinstance(node.lvalue, c_ast.ID):
            print(f" --ATRIBUICAO-- Variavel: {node.lvalue.name}, Linha: {node.coord.line}")
        self.generic_visit(node)

    def visit_ID(self, node):
        if node.name == 'global_var':
            print(f" --USO ID-- Variavel: {node.name}, Linha: {node.coord.line}")
        self.generic_visit(node)

def parse_c_file(filename):
    fake_libc_include_path = os.path.join(PYCPARSER_UTILS_DIR, 'fake_libc_include') #vai permitir que lidemos/resolvamos includes como <pthread.h>
    print(f"Fazendo uso de fake_libc_include de: {fake_libc_include_path}")

    try:
        cpp_executable = 'cpp'

        ast = parse_file(filename, use_cpp=True, cpp_args=['-E', '-nostdinc', '-I' + fake_libc_include_path])
        print(f"\n--- AST para '{filename}' ---")

        print("\n--- Relevant Info ---")
        visitor = AST_Visitor()
        visitor.visit(ast)
        print("------------------------------")

    except Exception as e:
        print(f"Erro ao parsear o arquivo {filename}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    c_file_path = os.path.join(os.path.dirname(__file__), '..', 'tests', 'example.c')
    print(f"Tentando parsear: {c_file_path}")
    parse_c_file(c_file_path)