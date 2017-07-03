int nondet_uint(void);

int main() {
    unsigned int x = nondet_uint();
    unsigned int y = ( ( x >> 16 ) ^ x ) & 0xffff;
    unsigned int o = y | ( y << 16 );
    return o;
}
