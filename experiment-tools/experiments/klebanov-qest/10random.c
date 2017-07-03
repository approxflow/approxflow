#          4294967295
#define R1 2869075806
#define R2 4101320879
#define R3 92887022
#define R4 2119564035
#define R5 862050725
#define R6 683977803
#define R7 1614573254
#define R8 3768262452
#define R9 129
#define R10 1000000

int nondet_uint(void);


int main() {
    unsigned int I = nondet_uint();

    unsigned int O = 0;

    if (I == R1) O = R1;
    else if (I == R2) O = R2;
    else if (I == R3) O = R3;
    else if (I == R4) O = R4;
    else if (I == R5) O = R5;
    else if (I == R6) O = R6;
    else if (I == R7) O = R7;
    else if (I == R8) O = R8;
    else if (I == R9) O = R9;
    else O = R10;
    return O;
}
