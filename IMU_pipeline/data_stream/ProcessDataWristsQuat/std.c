/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 * File: std.c
 *
 * MATLAB Coder version            : 25.1
 * C/C++ source code generated on  : 03-Sep-2025 17:31:54
 */

/* Include Files */
#include "std.h"
#include "rt_nonfinite.h"
#include <math.h>

/* Function Definitions */
/*
 * Arguments    : const float x[150]
 * Return Type  : float
 */
float b_std(const float x[150])
{
  float scale;
  float xbar;
  float y;
  int k;
  xbar = x[0];
  for (k = 0; k < 149; k++) {
    xbar += x[k + 1];
  }
  xbar /= 150.0F;
  y = 0.0F;
  scale = 1.29246971E-26F;
  for (k = 0; k < 150; k++) {
    float f;
    f = fabsf(x[k] - xbar);
    if (f > scale) {
      float t;
      t = scale / f;
      y = y * t * t + 1.0F;
      scale = f;
    } else {
      float t;
      t = f / scale;
      y += t * t;
    }
  }
  return scale * sqrtf(y) / 12.2065554F;
}

/*
 * File trailer for std.c
 *
 * [EOF]
 */
