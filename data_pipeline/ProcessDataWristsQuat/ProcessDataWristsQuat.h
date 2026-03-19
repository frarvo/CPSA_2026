/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 * File: ProcessDataWristsQuat.h
 *
 * MATLAB Coder version            : 25.1
 * C/C++ source code generated on  : 03-Sep-2025 17:31:54
 */

#ifndef PROCESSDATAWRISTSQUAT_H
#define PROCESSDATAWRISTSQUAT_H

/* Include Files */
#include "rtwtypes.h"
#include <stddef.h>
#include <stdlib.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Function Declarations */
extern void
ProcessDataWristsQuat(float accX_R[150], float accY_R[150], float accZ_R[150],
                      float gyrX_R[150], float gyrY_R[150], float gyrZ_R[150],
                      float accX_L[150], float accY_L[150], float accZ_L[150],
                      float gyrX_L[150], float gyrY_L[150], float gyrZ_L[150],
                      const float quatRW_x[150], const float quatRW_y[150],
                      const float quatRW_z[150], const float quatRW_w[150],
                      const float quatLW_x[150], const float quatLW_y[150],
                      const float quatLW_z[150], const float quatLW_w[150],
                      float imuFeatures[18]);

void ProcessDataWristsQuat_init(void);

#ifdef __cplusplus
}
#endif

#endif
/*
 * File trailer for ProcessDataWristsQuat.h
 *
 * [EOF]
 */
