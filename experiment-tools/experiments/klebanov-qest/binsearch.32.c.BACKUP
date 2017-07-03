#define BITS 32
int nondet_uint(void);


int main() {
    unsigned int I = nondet_uint();

    unsigned int O = 0;

    unsigned int m;
    int i;

    for (i = 0; i < BITS; i++) {
      m = 1<<(31-i);
      if (O + m <= I) O += m;
    }
    return O;
}
