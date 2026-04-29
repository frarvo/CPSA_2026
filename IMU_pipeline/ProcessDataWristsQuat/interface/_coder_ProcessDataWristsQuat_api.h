/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 * File: _coder_ProcessDataWristsQuat_api.h
 *
 * MATLAB Coder version            : 25.1
 * C/C++ source code generated on  : 03-Sep-2025 17:31:54
 */

#ifndef _CODER_PROCESSDATAWRISTSQUAT_API_H
#define _CODER_PROCESSDATAWRISTSQUAT_API_H

/* Include Files */
#include "emlrt.h"
#include "mex.h"
#include "tmwtypes.h"
#include <string.h>

/* Variable Declarations */
extern emlrtCTX emlrtRootTLSGlobal;
extern emlrtContext emlrtContextGlobal;

#ifdef __cplusplus
extern "C" {
#endif

/* Function Declarations */
void ProcessDataWristsQuat(
    real32_T accX_R[150], real32_T accY_R[150], real32_T accZ_R[150],
    real32_T gyrX_R[150], real32_T gyrY_R[150], real32_T gyrZ_R[150],
    real32_T accX_L[150], real32_T accY_L[150], real32_T accZ_L[150],
    real32_T gyrX_L[150], real32_T gyrY_L[150], real32_T gyrZ_L[150],
    real32_T quatRW_x[150], real32_T quatRW_y[150], real32_T quatRW_z[150],
    real32_T quatRW_w[150], real32_T quatLW_x[150], real32_T quatLW_y[150],
    real32_T quatLW_z[150], real32_T quatLW_w[150], real32_T imuFeatures[18]);

void ProcessDataWristsQuat_api(const mxArray *const prhs[20],
                               const mxArray **plhs);

void ProcessDataWristsQuat_atexit(void);

void ProcessDataWristsQuat_initialize(void);

void ProcessDataWristsQuat_terminate(void);

void ProcessDataWristsQuat_xil_shutdown(void);

void ProcessDataWristsQuat_xil_terminate(void);

#ifdef __cplusplus
}
#endif

#endif
/*
 * File trailer for _coder_ProcessDataWristsQuat_api.h
 *
 * [EOF]
 */
