int popcnt(unsigned int i) {
  i = (i & 0x55555555) + ((i >> 1) & 0x55555555);
  i = (i & 0x33333333) + ((i >> 2) & 0x33333333);
  i = (i & 0x0f0f0f0f) + ((i >> 4) & 0x0f0f0f0f);
  i = (i & 0x00ff00ff) + ((i >> 8) & 0x00ff00ff);
  return (i + (i >> 16)) & 0xffff;
}
