// Slightly different from NMS masked_copy

int masked_copy(int S) {
  int O = S & 0xffff0000;
  return O;
}
