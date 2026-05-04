/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 * File: mean.c
 *
 * MATLAB Coder version            : 25.1
 * C/C++ source code generated on  : 03-Sep-2025 17:31:54
 */

/* Include Files */
#include "mean.h"
#include "rt_nonfinite.h"

/* Function Definitions */
/*
 * Arguments    : const float x[5]
 * Return Type  : float
 */
float b_mean(const float x[5])
{
  return ((((x[0] + x[1]) + x[2]) + x[3]) + x[4]) / 5.0F;
}

/*
 * Arguments    : const float x[150]
 * Return Type  : float
 */
float mean(const float x[150])
{
  float y;
  int k;
  y = x[0];
  for (k = 0; k < 149; k++) {
    y += x[k + 1];
  }
  y /= 150.0F;
  return y;
}

/*
 * File trailer for mean.c
 *
 * [EOF]
 */
