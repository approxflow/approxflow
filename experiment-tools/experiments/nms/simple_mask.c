unsigned int simple_mask(unsigned int i) {
  unsigned int flow = (i & 0x000ff000);
  return flow;
}
