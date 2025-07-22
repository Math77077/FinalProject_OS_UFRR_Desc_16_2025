#include <pthread.h>
#include <stdio.h>

int global_var = 10;

void* thread_behaviour(void* arg) {
    pthread_mutex_t* my_lock = (pthread_mutex_t*)arg;
    pthread_mutex_lock(my_lock);
    global_var = global_var + 1;
    pthread_mutex_unlock(my_lock);
    return NULL;
}

int main() {
    pthread_t thread1;
    pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
    pthread_create(&thread1, NULL, thread_behaviour, &lock);
    pthread_join(thread1, NULL);
    printf("Variavel Global: %d\n", global_var);
    return 0;
}