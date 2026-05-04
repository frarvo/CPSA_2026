/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 * File: main.c
 *
 * MATLAB Coder version            : 25.1
 * C/C++ source code generated on  : 03-Sep-2025 17:31:54
 */

/*************************************************************************/
/* This automatically generated example C main file shows how to call    */
/* entry-point functions that MATLAB Coder generated. You must customize */
/* this file for your application. Do not modify this file directly.     */
/* Instead, make a copy of this file, modify it, and integrate it into   */
/* your development environment.                                         */
/*                                                                       */
/* This file initializes entry-point function arguments to a default     */
/* size and value before calling the entry-point functions. It does      */
/* not store or use any values returned from the entry-point functions.  */
/* If necessary, it does pre-allocate memory for returned values.        */
/* You can use this file as a starting point for a main function that    */
/* you can deploy in your application.                                   */
/*                                                                       */
/* After you copy the file, and before you deploy it, you must make the  */
/* following changes:                                                    */
/* * For variable-size function arguments, change the example sizes to   */
/* the sizes that your application requires.                             */
/* * Change the example values of function arguments to the values that  */
/* your application requires.                                            */
/* * If the entry-point functions return values, store these values or   */
/* otherwise use them as required by your application.                   */
/*                                                                       */
/*************************************************************************/

/* Include Files */
#include "main.h"
#include "ProcessDataWristsQuat.h"
#include "ProcessDataWristsQuat_initialize.h"
#include "ProcessDataWristsQuat_terminate.h"
#include "rt_nonfinite.h"
#include <string.h>

/* Function Declarations */
static void argInit_150x1_real32_T(float result[150]);

static float argInit_real32_T(void);

/* Function Definitions */
/*
 * Arguments    : float result[150]
 * Return Type  : void
 */
static void argInit_150x1_real32_T(float result[150])
{
  int idx0;
  /* Loop over the array to initialize each element. */
  for (idx0 = 0; idx0 < 150; idx0++) {
    /* Set the value of the array element.
Change this value to the value that the application requires. */
    result[idx0] = argInit_real32_T();
  }
}

/*
 * Arguments    : void
 * Return Type  : float
 */
static float argInit_real32_T(void)
{
  return 0.0F;
}

/*
 * Arguments    : int argc
 *                char **argv
 * Return Type  : int
 */
int main(int argc, char **argv)
{
  (void)argc;
  (void)argv;
  /* Initialize the application.
You do not need to do this more than one time. */
  ProcessDataWristsQuat_initialize();
  /* Invoke the entry-point functions.
You can call entry-point functions multiple times. */
  main_ProcessDataWristsQuat();
  /* Terminate the application.
You do not need to do this more than one time. */
  ProcessDataWristsQuat_terminate();
  return 0;
}

/*
 * Arguments    : void
 * Return Type  : void
 */
void main_ProcessDataWristsQuat(void)
{
  float accX_R_tmp[150];
  float b_accX_R_tmp[150];
  float c_accX_R_tmp[150];
  float d_accX_R_tmp[150];
  float e_accX_R_tmp[150];
  float f_accX_R_tmp[150];
  float g_accX_R_tmp[150];
  float h_accX_R_tmp[150];
  float i_accX_R_tmp[150];
  float j_accX_R_tmp[150];
  float k_accX_R_tmp[150];
  float l_accX_R_tmp[150];
  float m_accX_R_tmp[150];
  float imuFeatures[18];
  /* Initialize function 'ProcessDataWristsQuat' input arguments. */
  /* Initialize function input argument 'accX_R'. */
  argInit_150x1_real32_T(accX_R_tmp);
  /* Initialize function input argument 'accY_R'. */
  /* Initialize function input argument 'accZ_R'. */
  /* Initialize function input argument 'gyrX_R'. */
  /* Initialize function input argument 'gyrY_R'. */
  /* Initialize function input argument 'gyrZ_R'. */
  /* Initialize function input argument 'accX_L'. */
  /* Initialize function input argument 'accY_L'. */
  /* Initialize function input argument 'accZ_L'. */
  /* Initialize function input argument 'gyrX_L'. */
  /* Initialize function input argument 'gyrY_L'. */
  /* Initialize function input argument 'gyrZ_L'. */
  /* Initialize function input argument 'quatRW_x'. */
  /* Initialize function input argument 'quatRW_y'. */
  /* Initialize function input argument 'quatRW_z'. */
  /* Initialize function input argument 'quatRW_w'. */
  /* Initialize function input argument 'quatLW_x'. */
  /* Initialize function input argument 'quatLW_y'. */
  /* Initialize function input argument 'quatLW_z'. */
  /* Initialize function input argument 'quatLW_w'. */
  /* Call the entry-point 'ProcessDataWristsQuat'. */
  memcpy(&b_accX_R_tmp[0], &accX_R_tmp[0], 150U * sizeof(float));
  memcpy(&c_accX_R_tmp[0], &accX_R_tmp[0], 150U * sizeof(float));
  memcpy(&d_accX_R_tmp[0], &accX_R_tmp[0], 150U * sizeof(float));
  memcpy(&e_accX_R_tmp[0], &accX_R_tmp[0], 150U * sizeof(float));
  memcpy(&f_accX_R_tmp[0], &accX_R_tmp[0], 150U * sizeof(float));
  memcpy(&g_accX_R_tmp[0], &accX_R_tmp[0], 150U * sizeof(float));
  memcpy(&h_accX_R_tmp[0], &accX_R_tmp[0], 150U * sizeof(float));
  memcpy(&i_accX_R_tmp[0], &accX_R_tmp[0], 150U * sizeof(float));
  memcpy(&j_accX_R_tmp[0], &accX_R_tmp[0], 150U * sizeof(float));
  memcpy(&k_accX_R_tmp[0], &accX_R_tmp[0], 150U * sizeof(float));
  memcpy(&l_accX_R_tmp[0], &accX_R_tmp[0], 150U * sizeof(float));
  memcpy(&m_accX_R_tmp[0], &accX_R_tmp[0], 150U * sizeof(float));
  ProcessDataWristsQuat(
      b_accX_R_tmp, c_accX_R_tmp, d_accX_R_tmp, e_accX_R_tmp, f_accX_R_tmp,
      g_accX_R_tmp, h_accX_R_tmp, i_accX_R_tmp, j_accX_R_tmp, k_accX_R_tmp,
      l_accX_R_tmp, m_accX_R_tmp, accX_R_tmp, accX_R_tmp, accX_R_tmp,
      accX_R_tmp, accX_R_tmp, accX_R_tmp, accX_R_tmp, accX_R_tmp, imuFeatures);
}

/*
 * File trailer for main.c
 *
 * [EOF]
 */
