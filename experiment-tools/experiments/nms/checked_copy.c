// same as meng/smith sanity check but base is nondet here
int checked_copy(int i, int base) {
  int v;
  if (i < 16)
    v = base + i;
  else
    v = base;
  return v;
}
