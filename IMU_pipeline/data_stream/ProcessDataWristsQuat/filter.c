/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 * File: filter.c
 *
 * MATLAB Coder version            : 25.1
 * C/C++ source code generated on  : 03-Sep-2025 17:31:54
 */

/* Include Files */
#include "filter.h"
#include "rt_nonfinite.h"
#include <string.h>

/* Function Definitions */
/*
 * Arguments    : const float x[150]
 *                float y[150]
 * Return Type  : void
 */
void filter(const float x[150], float y[150])
{
  static const float fv[5] = {0.662015855F, -2.64806342F, 3.97209501F,
                              -2.64806342F, 0.662015855F};
  static const float fv1[5] = {1.0F, -3.18063855F, 3.86119437F, -2.11215544F,
                               0.438265145F};
  int j;
  int k;
  memset(&y[0], 0, 150U * sizeof(float));
  for (k = 0; k < 150; k++) {
    float as;
    int i;
    int y_tmp;
    if (150 - k < 5) {
      i = 149 - k;
    } else {
      i = 4;
    }
    for (j = 0; j <= i; j++) {
      y_tmp = k + j;
      y[y_tmp] += x[k] * fv[j];
    }
    if (149 - k < 4) {
      i = 148 - k;
    } else {
      i = 3;
    }
    as = -y[k];
    for (j = 0; j <= i; j++) {
      y_tmp = (k + j) + 1;
      y[y_tmp] += as * fv1[j + 1];
    }
  }
}

/*
 * File trailer for filter.c
 *
 * [EOF]
 */
