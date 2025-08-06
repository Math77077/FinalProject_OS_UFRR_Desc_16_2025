#include <pthread.h>
#include <stdio.h>

int global_counter = 0; 

void* unprotected_increment(void* arg) {
    int i;
    for (i = 0; i < 100000; i++) {
        global_counter = global_counter + 1; 
    }
    return NULL;
}

int main() {
    pthread_t thread1, thread2;

    pthread_create(&thread1, NULL, unprotected_increment, NULL);
    pthread_create(&thread2, NULL, unprotected_increment, NULL);

    pthread_join(thread1, NULL);
    pthread_join(thread2, NULL);

    // O valor esperado seria 200000, mas a condição de corrida provavelmente gerara em um valor menor ou inconsistente
    printf("Contador Final: %d\n", global_counter);

    return 0;
}