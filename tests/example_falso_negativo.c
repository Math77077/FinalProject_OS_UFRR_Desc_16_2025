#include <pthread.h>
#include <stdio.h>

int readonly_var = 100; 

void* read_only_function(void* arg) {
    int value = readonly_var; 
    printf("Valor lido: %d\n", value);
    return NULL;
}

int main() {
    pthread_t thread1, thread2;

    pthread_create(&thread1, NULL, read_only_function, NULL);
    pthread_create(&thread2, NULL, read_only_function, NULL);

    pthread_join(thread1, NULL);
    pthread_join(thread2, NULL);

    return 0;
}