/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 * File: sign.c
 *
 * MATLAB Coder version            : 25.1
 * C/C++ source code generated on  : 03-Sep-2025 17:31:54
 */

/* Include Files */
#include "sign.h"
#include "rt_nonfinite.h"
#include "rt_nonfinite.h"

/* Function Definitions */
/*
 * Arguments    : float x[150]
 * Return Type  : void
 */
void b_sign(float x[150])
{
  int k;
  for (k = 0; k < 150; k++) {
    if (rtIsNaNF(x[k])) {
      x[k] = rtNaNF;
    } else if (x[k] < 0.0F) {
      x[k] = -1.0F;
    } else {
      x[k] = (float)(x[k] > 0.0F);
    }
  }
}

/*
 * File trailer for sign.c
 *
 * [EOF]
 */
