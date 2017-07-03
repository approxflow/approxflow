// very similar to NMS checked_copy by base isn't nondet here
#define base 0x00001000
int sanity_check(int S) {
  int O;
  if (S < 16)
    O = base + S;
  else
    O = base;
  return O;
}
