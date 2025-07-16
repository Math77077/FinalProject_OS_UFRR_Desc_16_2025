Investigar se o uso de mecanismos de sincronização (locks, mutexes, semáforos) é suficiente para
evitar data races em programas concorrentes, por meio de verificação formal utilizando lógica
proposicional e resolução com SAT Solvers.
Em ambientes com múltiplas threads, o uso incorreto de locks pode levar a data races, onde duas
ou mais threads acessam uma mesma variável simultaneamente, e pelo menos uma dessas acessa
para escrita. Este projeto propõe o uso de técnicas formais, modelagem de estados e resolução
lógica para detectar automaticamente possíveis data races em programas concorrentes.
