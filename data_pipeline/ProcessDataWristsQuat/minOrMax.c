/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 * File: minOrMax.c
 *
 * MATLAB Coder version            : 25.1
 * C/C++ source code generated on  : 03-Sep-2025 17:31:54
 */

/* Include Files */
#include "minOrMax.h"
#include "rt_nonfinite.h"
#include "rt_nonfinite.h"

/* Function Definitions */
/*
 * Arguments    : const float x[150]
 * Return Type  : float
 */
float maximum(const float x[150])
{
  float ex;
  int b_k;
  int idx;
  if (!rtIsNaNF(x[0])) {
    idx = 1;
  } else {
    int k;
    boolean_T exitg1;
    idx = 0;
    k = 2;
    exitg1 = false;
    while ((!exitg1) && (k < 151)) {
      if (!rtIsNaNF(x[k - 1])) {
        idx = k;
        exitg1 = true;
      } else {
        k++;
      }
    }
  }
  if (idx == 0) {
    ex = x[0];
  } else {
    ex = x[idx - 1];
    idx++;
    for (b_k = idx; b_k < 151; b_k++) {
      float f;
      f = x[b_k - 1];
      if (ex < f) {
        ex = f;
      }
    }
  }
  return ex;
}

/*
 * Arguments    : const float x[150]
 * Return Type  : float
 */
float minimum(const float x[150])
{
  float ex;
  int b_k;
  int idx;
  if (!rtIsNaNF(x[0])) {
    idx = 1;
  } else {
    int k;
    boolean_T exitg1;
    idx = 0;
    k = 2;
    exitg1 = false;
    while ((!exitg1) && (k < 151)) {
      if (!rtIsNaNF(x[k - 1])) {
        idx = k;
        exitg1 = true;
      } else {
        k++;
      }
    }
  }
  if (idx == 0) {
    ex = x[0];
  } else {
    ex = x[idx - 1];
    idx++;
    for (b_k = idx; b_k < 151; b_k++) {
      float f;
      f = x[b_k - 1];
      if (ex > f) {
        ex = f;
      }
    }
  }
  return ex;
}

/*
 * File trailer for minOrMax.c
 *
 * [EOF]
 */
