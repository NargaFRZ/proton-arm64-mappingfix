#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>

static DWORD WINAPI worker(void *unused)
{
    return 0;
}

static int batch(void)
{
    HANDLE threads[64];
    unsigned int i;

    for (i = 0; i < 64; ++i)
    {
        threads[i] = CreateThread(NULL, 0, worker, NULL, 0, NULL);
        if (!threads[i])
        {
            fprintf(stderr, "CreateThread failed: %lu\n", GetLastError());
            return 1;
        }
    }
    if (WaitForMultipleObjects(64, threads, TRUE, INFINITE) != WAIT_OBJECT_0)
    {
        fprintf(stderr, "WaitForMultipleObjects failed: %lu\n", GetLastError());
        return 1;
    }
    for (i = 0; i < 64; ++i) CloseHandle(threads[i]);
    Sleep(10);
    return 0;
}

int main(void)
{
    unsigned int i;

    for (i = 0; i < 32; ++i) if (batch()) return 1;
    Sleep(500);
    puts("WARMED");
    fflush(stdout);
    Sleep(500);
    for (i = 1; i <= 1000; ++i)
    {
        if (batch()) return 1;
        if (!(i % 100))
        {
            Sleep(500);
            printf("SAMPLE %u\n", i * 64);
            fflush(stdout);
            Sleep(500);
        }
    }
    puts("DONE");
    fflush(stdout);
    Sleep(500);
    return 0;
}
