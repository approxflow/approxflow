//#include <math.h>
#include "fdlibm.h"

#ifdef __STDC__
  double cos(double x)
#else
  double cos(x)
  double x;
#endif
{
  double y[2],z=0.0;
  int n, ix;

    /* High word of x. */
  ix = __HI(x);

    /* |x| ~< pi/4 */
  ix &= 0x7fffffff;
  if(ix <= 0x3fe921fb) return __kernel_cos(x,z);

    /* cos(Inf or NaN) is NaN */
  else if (ix>=0x7ff00000) return x-x;

    /* argument reduction needed */
  else {
      n = __ieee754_rem_pio2(x,y);
      switch(n&3) {
    case 0: return  __kernel_cos(y[0],y[1]);
    case 1: return -__kernel_sin(y[0],y[1],1);
    case 2: return -__kernel_cos(y[0],y[1]);
    default:
            return  __kernel_sin(y[0],y[1],1);
      }
  }
}

#ifdef __STDC__
  double sin(double x)
#else
  double sin(x)
  double x;
#endif
{
  double y[2],z=0.0;
  int n, ix;

    /* High word of x. */
  ix = __HI(x);

    /* |x| ~< pi/4 */
  ix &= 0x7fffffff;
  if(ix <= 0x3fe921fb) return __kernel_sin(x,z,0);

    /* sin(Inf or NaN) is NaN */
  else if (ix>=0x7ff00000) return x-x;

    /* argument reduction needed */
  else {
      n = __ieee754_rem_pio2(x,y);
      switch(n&3) {
    case 0: return  __kernel_sin(y[0],y[1],1);
    case 1: return  __kernel_cos(y[0],y[1]);
    case 2: return -__kernel_sin(y[0],y[1],1);
    default:
      return -__kernel_cos(y[0],y[1]);
      }
  }
}

int main(int argc, char **argv) {

 unsigned char x,y; // secret inputs
 __CPROVER_assume(x>=0 && x<125); // range limit
 __CPROVER_assume(y>=0 && y<125);
 unsigned char newx, newy; // observable outputs

 double center = (double) 125/2.0;
 double radius = center;
 double degrees = (double) (3.141593*720.0/180.0);
 double deltay = (double) (y-center);
 double deltax = (double) (x-center);
 double distance = deltax*deltax + deltay*deltay;

 if (distance < radius*radius) {
 double factor=1.0-sqrt((double) distance)/radius;
 double d = (double) (degrees*factor*factor);
 double sine=sin(d);
 double cosine=cos(d);

 newx = ((cosine*deltax -sine*deltay)+center);
 newy = ((sine*deltax+cosine*deltay)+center);
 } else { newx = x; newy = y; }
 assert(0);
 return 0;
 }
