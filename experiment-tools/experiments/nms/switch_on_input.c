int do_switch(char *src) {
  int i = 0;
  switch(src[0]) {
    case 'a': i = 1; break;
    case 'b': i = 2; break;
    case 'c': i = 3; break;
    case 'd': i = 4; break;
    case 'e': i = 5; break;
    case 'f': i = 6; break;
    case 'g': i = 7; break;
    case 'h': i = 8; break;
    case 'i': i = 9; break;
    case 'j': i = 10; break;
    case 'k': i = 11; break;
    case 'l': i = 12; break;
    case 'm': i = 13; break;
    case 'n': i = 14; break;
    case 'o': i = 15; break;
    case 'p': i = 16; break;
    case 'q': i = 17; break;
    case 'r': i = 18; break;
    default: i = 19; break;
  }
  return i;
}
