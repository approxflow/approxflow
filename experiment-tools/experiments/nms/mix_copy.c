unsigned int mix_copy(unsigned int x) {
  unsigned int y = ((x >> 16) ^x) & 0xffff;
  return y | (y << 16);
}
