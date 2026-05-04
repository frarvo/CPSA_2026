/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 * File: ProcessDataWristsQuat.c
 *
 * MATLAB Coder version            : 25.1
 * C/C++ source code generated on  : 03-Sep-2025 17:31:54
 */

/* Include Files */
#include "ProcessDataWristsQuat.h"
#include "ProcessDataWristsQuat_data.h"
#include "ProcessDataWristsQuat_initialize.h"
#include "any.h"
#include "filter.h"
#include "mean.h"
#include "minOrMax.h"
#include "rt_nonfinite.h"
#include "sign.h"
#include "std.h"
#include <math.h>
#include <string.h>

/* Variable Definitions */
static boolean_T initialized_r;

static float qrw0;

static float qrx0;

static float qry0;

static float qrz0;

static boolean_T initialized_l;

static float qlw0;

static float qlx0;

static float qly0;

static float qlz0;

/* Function Definitions */
/*
 * Inputs: 6 vectors [150×1] of type single for Right writs imu data
 *          6 vectors [150×1] of type single for Left writs imu data
 *          4 vectors [150x1] of type single for Right wrist quaternion
 * coefficients 4 vectors [150x1] of type single for Left wrist quaternion
 * coefficients
 *
 *  Output: imuFeatures [1×18] single
 *  [AccStdR, AccStdL, VelStdR, VelStdL, AccAmpR, AccAmpL, VelAmpR, VelAmpL,
 *   AccZcrR, AccZcrL, VelZcrR, VelZcrL, AccEngR, AccEngL, VelEngR, VelEngL,
 *   ThetaRW, ThetaLW]
 *
 * Arguments    : float accX_R[150]
 *                float accY_R[150]
 *                float accZ_R[150]
 *                float gyrX_R[150]
 *                float gyrY_R[150]
 *                float gyrZ_R[150]
 *                float accX_L[150]
 *                float accY_L[150]
 *                float accZ_L[150]
 *                float gyrX_L[150]
 *                float gyrY_L[150]
 *                float gyrZ_L[150]
 *                const float quatRW_x[150]
 *                const float quatRW_y[150]
 *                const float quatRW_z[150]
 *                const float quatRW_w[150]
 *                const float quatLW_x[150]
 *                const float quatLW_y[150]
 *                const float quatLW_z[150]
 *                const float quatLW_w[150]
 *                float imuFeatures[18]
 * Return Type  : void
 */
void ProcessDataWristsQuat(
    float accX_R[150], float accY_R[150], float accZ_R[150], float gyrX_R[150],
    float gyrY_R[150], float gyrZ_R[150], float accX_L[150], float accY_L[150],
    float accZ_L[150], float gyrX_L[150], float gyrY_L[150], float gyrZ_L[150],
    const float quatRW_x[150], const float quatRW_y[150],
    const float quatRW_z[150], const float quatRW_w[150],
    const float quatLW_x[150], const float quatLW_y[150],
    const float quatLW_z[150], const float quatLW_w[150], float imuFeatures[18])
{
  float accNormL[150];
  float accNormR[150];
  float b_s[150];
  float b_y[150];
  float c_s[150];
  float d_s[150];
  float e_y[150];
  float f_y[150];
  float gyrNormL[150];
  float gyrNormR[150];
  float nrm_LW[150];
  float nrm_RW[150];
  float ql_w[150];
  float ql_x[150];
  float ql_y[150];
  float ql_z[150];
  float qr_w[150];
  float qr_x[150];
  float qr_y[150];
  float qr_z[150];
  float s[150];
  float y[150];
  float c_y;
  float d_y;
  float g_y;
  float n0;
  int h_y;
  int i;
  int i_y;
  int j_y;
  int k_y;
  boolean_T mask_r[150];
  boolean_T x[149];
  if (!isInitialized_ProcessDataWristsQuat) {
    ProcessDataWristsQuat_initialize();
  }
  /*  RIGHT IMUs */
  /*  LEFT IMUs */
  /*  RIGHT QUATERNIONS */
  /*  LEFT QUATERNIONS */
  /*  --- Butterworth HP filter (4th order, cutoff 0.1) */
  /*  Apply filter to signals */
  memcpy(&accNormR[0], &accX_R[0], 150U * sizeof(float));
  filter(accNormR, accX_R);
  memcpy(&accNormR[0], &accY_R[0], 150U * sizeof(float));
  filter(accNormR, accY_R);
  memcpy(&accNormR[0], &accZ_R[0], 150U * sizeof(float));
  filter(accNormR, accZ_R);
  memcpy(&accNormR[0], &gyrX_R[0], 150U * sizeof(float));
  filter(accNormR, gyrX_R);
  memcpy(&accNormR[0], &gyrY_R[0], 150U * sizeof(float));
  filter(accNormR, gyrY_R);
  memcpy(&accNormR[0], &gyrZ_R[0], 150U * sizeof(float));
  filter(accNormR, gyrZ_R);
  memcpy(&accNormR[0], &accX_L[0], 150U * sizeof(float));
  filter(accNormR, accX_L);
  memcpy(&accNormR[0], &accY_L[0], 150U * sizeof(float));
  filter(accNormR, accY_L);
  memcpy(&accNormR[0], &accZ_L[0], 150U * sizeof(float));
  filter(accNormR, accZ_L);
  memcpy(&accNormR[0], &gyrX_L[0], 150U * sizeof(float));
  filter(accNormR, gyrX_L);
  memcpy(&accNormR[0], &gyrY_L[0], 150U * sizeof(float));
  filter(accNormR, gyrY_L);
  memcpy(&accNormR[0], &gyrZ_L[0], 150U * sizeof(float));
  filter(accNormR, gyrZ_L);
  /*  Norms: collapse 3x1D vectors into 1x1D vector */
  for (i = 0; i < 150; i++) {
    n0 = accX_R[i];
    c_y = accY_R[i];
    d_y = accZ_R[i];
    accNormR[i] = sqrtf((n0 * n0 + c_y * c_y) + d_y * d_y);
    n0 = gyrX_R[i];
    c_y = gyrY_R[i];
    d_y = gyrZ_R[i];
    gyrNormR[i] = sqrtf((n0 * n0 + c_y * c_y) + d_y * d_y);
    n0 = accX_L[i];
    c_y = accY_L[i];
    d_y = accZ_L[i];
    accNormL[i] = sqrtf((n0 * n0 + c_y * c_y) + d_y * d_y);
    n0 = gyrX_L[i];
    c_y = gyrY_L[i];
    d_y = gyrZ_L[i];
    gyrNormL[i] = sqrtf((n0 * n0 + c_y * c_y) + d_y * d_y);
  }
  /*  Features */
  /*  [AccStdR, AccStdL, VelStdR, VelStdL, AccAmpR, AccAmpL, VelAmpR, VelAmpL,
   */
  /*   AccZcrR, AccZcrL, VelZcrR, VelZcrL, AccEngR, AccEngL, VelEngR, VelEngL,
   */
  /*   ThetaRW, ThetaLW] */
  /*  Center the signal around the mean (the new 0) */
  /*  handle exact zeros consistently: carry forward previous sign  */
  /*  (because 0 signal can result as 2 crossing both negative and positive) */
  n0 = mean(accNormR);
  for (i = 0; i < 150; i++) {
    s[i] = accNormR[i] - n0;
  }
  b_sign(s);
  for (i = 0; i < 149; i++) {
    if (s[i + 1] == 0.0F) {
      s[i + 1] = s[i];
    }
  }
  /*  count sign changes between consecutive samples */
  /*  custom zcr because MATLAB's zerocrossrate is non codegen friendly  */
  /*  Center the signal around the mean (the new 0) */
  /*  handle exact zeros consistently: carry forward previous sign  */
  /*  (because 0 signal can result as 2 crossing both negative and positive) */
  n0 = mean(accNormL);
  for (i = 0; i < 150; i++) {
    b_s[i] = accNormL[i] - n0;
  }
  b_sign(b_s);
  for (i = 0; i < 149; i++) {
    if (b_s[i + 1] == 0.0F) {
      b_s[i + 1] = b_s[i];
    }
  }
  /*  count sign changes between consecutive samples */
  /*  Center the signal around the mean (the new 0) */
  /*  handle exact zeros consistently: carry forward previous sign  */
  /*  (because 0 signal can result as 2 crossing both negative and positive) */
  n0 = mean(gyrNormR);
  for (i = 0; i < 150; i++) {
    c_s[i] = gyrNormR[i] - n0;
  }
  b_sign(c_s);
  for (i = 0; i < 149; i++) {
    if (c_s[i + 1] == 0.0F) {
      c_s[i + 1] = c_s[i];
    }
  }
  /*  count sign changes between consecutive samples */
  /*  Center the signal around the mean (the new 0) */
  /*  handle exact zeros consistently: carry forward previous sign  */
  /*  (because 0 signal can result as 2 crossing both negative and positive) */
  n0 = mean(gyrNormL);
  for (i = 0; i < 150; i++) {
    d_s[i] = gyrNormL[i] - n0;
  }
  b_sign(d_s);
  for (i = 0; i < 149; i++) {
    if (d_s[i + 1] == 0.0F) {
      d_s[i + 1] = d_s[i];
    }
  }
  /*  count sign changes between consecutive samples */
  /*  Quaternions */
  /*  Quaternions normalization */
  /*  RIGHT */
  /*  LEFT */
  for (i = 0; i < 150; i++) {
    float f;
    float f1;
    float f2;
    float f3;
    float f4;
    n0 = accNormR[i];
    y[i] = n0 * n0;
    n0 = accNormL[i];
    b_y[i] = n0 * n0;
    n0 = gyrNormR[i];
    e_y[i] = n0 * n0;
    n0 = gyrNormL[i];
    f_y[i] = n0 * n0;
    n0 = quatRW_w[i] * 0.0001F;
    c_y = quatRW_x[i] * 0.0001F;
    d_y = quatRW_y[i] * 0.0001F;
    g_y = quatRW_z[i] * 0.0001F;
    f = quatLW_w[i] * 0.0001F;
    f1 = quatLW_x[i] * 0.0001F;
    f2 = quatLW_y[i] * 0.0001F;
    f3 = quatLW_z[i] * 0.0001F;
    f4 = sqrtf(((n0 * n0 + c_y * c_y) + d_y * d_y) + g_y * g_y);
    if (f4 == 0.0F) {
      f4 = 1.0F;
    }
    qr_w[i] = n0 / f4;
    qr_x[i] = c_y / f4;
    qr_y[i] = d_y / f4;
    qr_z[i] = g_y / f4;
    n0 = sqrtf(((f * f + f1 * f1) + f2 * f2) + f3 * f3);
    if (n0 == 0.0F) {
      n0 = 1.0F;
    }
    f /= n0;
    ql_w[i] = f;
    f1 /= n0;
    ql_x[i] = f1;
    f2 /= n0;
    ql_y[i] = f2;
    f3 /= n0;
    ql_z[i] = f3;
  }
  /*  Reference Quaternion (Absolute initial position) RIGHT */
  if (!initialized_r) {
    /*  average first K samples */
    qrw0 = b_mean(&qr_w[0]);
    qrx0 = b_mean(&qr_x[0]);
    qry0 = b_mean(&qr_y[0]);
    qrz0 = b_mean(&qr_z[0]);
    /*  normalize & fix hemisphere */
    n0 = sqrtf(((qrw0 * qrw0 + qrx0 * qrx0) + qry0 * qry0) + qrz0 * qrz0);
    if (n0 == 0.0F) {
      n0 = 1.0F;
    }
    qrw0 /= n0;
    qrx0 /= n0;
    qry0 /= n0;
    qrz0 /= n0;
    if (qrw0 < 0.0F) {
      qrw0 = -qrw0;
      qrx0 = -qrx0;
      qry0 = -qry0;
      qrz0 = -qrz0;
    }
    initialized_r = true;
  }
  /*  Reference Quaternion (Absolute initial position) LEFT */
  if (!initialized_l) {
    qlw0 = b_mean(&ql_w[0]);
    qlx0 = b_mean(&ql_x[0]);
    qly0 = b_mean(&ql_y[0]);
    qlz0 = b_mean(&ql_z[0]);
    n0 = sqrtf(((qlw0 * qlw0 + qlx0 * qlx0) + qly0 * qly0) + qlz0 * qlz0);
    if (n0 == 0.0F) {
      n0 = 1.0F;
    }
    qlw0 /= n0;
    qlx0 /= n0;
    qly0 /= n0;
    qlz0 /= n0;
    if (qlw0 < 0.0F) {
      qlw0 = -qlw0;
      qlx0 = -qlx0;
      qly0 = -qly0;
      qlz0 = -qlz0;
    }
    initialized_l = true;
  }
  /*  Enforce hemisphere consistency: make per-sample qw >= 0 */
  for (i = 0; i < 150; i++) {
    mask_r[i] = (qr_w[i] < 0.0F);
  }
  if (any(mask_r)) {
    for (i = 0; i < 150; i++) {
      if (mask_r[i]) {
        qr_w[i] = -qr_w[i];
        qr_x[i] = -qr_x[i];
        qr_y[i] = -qr_y[i];
        qr_z[i] = -qr_z[i];
      }
    }
  }
  for (i = 0; i < 150; i++) {
    mask_r[i] = (ql_w[i] < 0.0F);
  }
  if (any(mask_r)) {
    for (i = 0; i < 150; i++) {
      if (mask_r[i]) {
        ql_w[i] = -ql_w[i];
        ql_x[i] = -ql_x[i];
        ql_y[i] = -ql_y[i];
        ql_z[i] = -ql_z[i];
      }
    }
  }
  /*  Relative angle calculation (only w needed for angle)  */
  /*  RIGHT */
  /*  Relative angle calculation (only w needed for angle)  */
  /*  LEFT */
  for (i = 0; i < 150; i++) {
    n0 = ((qr_w[i] * qrw0 + qr_x[i] * qrx0) + qr_y[i] * qry0) + qr_z[i] * qrz0;
    qr_w[i] = n0;
    nrm_LW[i] = fminf(fmaxf(n0, -1.0F), 1.0F);
    n0 = ((ql_w[i] * qlw0 + ql_x[i] * qlx0) + ql_y[i] * qly0) + ql_z[i] * qlz0;
    ql_w[i] = n0;
    n0 = fmaxf(n0, -1.0F);
    qr_x[i] = n0;
    nrm_RW[i] = fminf(n0, 1.0F);
  }
  /*  OUTPUT features */
  for (i = 0; i < 149; i++) {
    x[i] = (s[i + 1] * s[i] < 0.0F);
  }
  h_y = x[0];
  for (i = 0; i < 148; i++) {
    h_y += x[i + 1];
  }
  for (i = 0; i < 149; i++) {
    x[i] = (b_s[i + 1] * b_s[i] < 0.0F);
  }
  i_y = x[0];
  for (i = 0; i < 148; i++) {
    i_y += x[i + 1];
  }
  for (i = 0; i < 149; i++) {
    x[i] = (c_s[i + 1] * c_s[i] < 0.0F);
  }
  j_y = x[0];
  for (i = 0; i < 148; i++) {
    j_y += x[i + 1];
  }
  for (i = 0; i < 149; i++) {
    x[i] = (d_s[i + 1] * d_s[i] < 0.0F);
  }
  k_y = x[0];
  for (i = 0; i < 148; i++) {
    k_y += x[i + 1];
  }
  n0 = y[0];
  c_y = b_y[0];
  d_y = e_y[0];
  g_y = f_y[0];
  for (i = 0; i < 149; i++) {
    n0 += y[i + 1];
    c_y += b_y[i + 1];
    d_y += e_y[i + 1];
    g_y += f_y[i + 1];
  }
  for (i = 0; i < 150; i++) {
    nrm_LW[i] = 114.59156F * acosf(nrm_LW[i]);
    nrm_RW[i] = 114.59156F * acosf(nrm_RW[i]);
  }
  imuFeatures[0] = b_std(accNormR);
  imuFeatures[1] = b_std(accNormL);
  imuFeatures[2] = b_std(gyrNormR);
  imuFeatures[3] = b_std(gyrNormL);
  imuFeatures[4] = maximum(accNormR) - minimum(accNormR);
  imuFeatures[5] = maximum(accNormL) - minimum(accNormL);
  imuFeatures[6] = maximum(gyrNormR) - minimum(gyrNormR);
  imuFeatures[7] = maximum(gyrNormL) - minimum(gyrNormL);
  imuFeatures[8] = (float)((double)h_y / 149.0);
  imuFeatures[9] = (float)((double)i_y / 149.0);
  imuFeatures[10] = (float)((double)j_y / 149.0);
  imuFeatures[11] = (float)((double)k_y / 149.0);
  imuFeatures[12] = n0;
  imuFeatures[13] = c_y;
  imuFeatures[14] = d_y;
  imuFeatures[15] = g_y;
  imuFeatures[16] = mean(nrm_LW);
  imuFeatures[17] = mean(nrm_RW);
}

/*
 * Arguments    : void
 * Return Type  : void
 */
void ProcessDataWristsQuat_init(void)
{
  initialized_r = false;
  qrw0 = 1.0F;
  qrx0 = 0.0F;
  qry0 = 0.0F;
  qrz0 = 0.0F;
  initialized_l = false;
  qlw0 = 1.0F;
  qlx0 = 0.0F;
  qly0 = 0.0F;
  qlz0 = 0.0F;
}

/*
 * File trailer for ProcessDataWristsQuat.c
 *
 * [EOF]
 */
