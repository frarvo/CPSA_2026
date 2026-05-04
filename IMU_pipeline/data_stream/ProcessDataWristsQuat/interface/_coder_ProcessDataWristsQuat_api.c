/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 * File: _coder_ProcessDataWristsQuat_api.c
 *
 * MATLAB Coder version            : 25.1
 * C/C++ source code generated on  : 03-Sep-2025 17:31:54
 */

/* Include Files */
#include "_coder_ProcessDataWristsQuat_api.h"
#include "_coder_ProcessDataWristsQuat_mex.h"

/* Variable Definitions */
emlrtCTX emlrtRootTLSGlobal = NULL;

emlrtContext emlrtContextGlobal = {
    true,                                                 /* bFirstTime */
    false,                                                /* bInitialized */
    131674U,                                              /* fVersionInfo */
    NULL,                                                 /* fErrorFunction */
    "ProcessDataWristsQuat",                              /* fFunctionName */
    NULL,                                                 /* fRTCallStack */
    false,                                                /* bDebugMode */
    {2045744189U, 2170104910U, 2743257031U, 4284093946U}, /* fSigWrd */
    NULL                                                  /* fSigMem */
};

/* Function Declarations */
static real32_T (*b_emlrt_marshallIn(const emlrtStack *sp, const mxArray *u,
                                     const emlrtMsgIdentifier *parentId))[150];

static real32_T (*c_emlrt_marshallIn(const emlrtStack *sp, const mxArray *src,
                                     const emlrtMsgIdentifier *msgId))[150];

static void emlrtExitTimeCleanupDtorFcn(const void *r);

static real32_T (*emlrt_marshallIn(const emlrtStack *sp, const mxArray *nullptr,
                                   const char_T *identifier))[150];

static const mxArray *emlrt_marshallOut(real32_T u[18]);

/* Function Definitions */
/*
 * Arguments    : const emlrtStack *sp
 *                const mxArray *u
 *                const emlrtMsgIdentifier *parentId
 * Return Type  : real32_T (*)[150]
 */
static real32_T (*b_emlrt_marshallIn(const emlrtStack *sp, const mxArray *u,
                                     const emlrtMsgIdentifier *parentId))[150]
{
  real32_T(*y)[150];
  y = c_emlrt_marshallIn(sp, emlrtAlias(u), parentId);
  emlrtDestroyArray(&u);
  return y;
}

/*
 * Arguments    : const emlrtStack *sp
 *                const mxArray *src
 *                const emlrtMsgIdentifier *msgId
 * Return Type  : real32_T (*)[150]
 */
static real32_T (*c_emlrt_marshallIn(const emlrtStack *sp, const mxArray *src,
                                     const emlrtMsgIdentifier *msgId))[150]
{
  static const int32_T dims = 150;
  int32_T i;
  real32_T(*ret)[150];
  boolean_T b = false;
  emlrtCheckVsBuiltInR2012b((emlrtConstCTX)sp, msgId, src, "single", false, 1U,
                            (const void *)&dims, &b, &i);
  ret = (real32_T(*)[150])emlrtMxGetData(src);
  emlrtDestroyArray(&src);
  return ret;
}

/*
 * Arguments    : const void *r
 * Return Type  : void
 */
static void emlrtExitTimeCleanupDtorFcn(const void *r)
{
  emlrtExitTimeCleanup(&emlrtContextGlobal);
}

/*
 * Arguments    : const emlrtStack *sp
 *                const mxArray *nullptr
 *                const char_T *identifier
 * Return Type  : real32_T (*)[150]
 */
static real32_T (*emlrt_marshallIn(const emlrtStack *sp, const mxArray *nullptr,
                                   const char_T *identifier))[150]
{
  emlrtMsgIdentifier thisId;
  real32_T(*y)[150];
  thisId.fIdentifier = (const char_T *)identifier;
  thisId.fParent = NULL;
  thisId.bParentIsCell = false;
  y = b_emlrt_marshallIn(sp, emlrtAlias(nullptr), &thisId);
  emlrtDestroyArray(&nullptr);
  return y;
}

/*
 * Arguments    : real32_T u[18]
 * Return Type  : const mxArray *
 */
static const mxArray *emlrt_marshallOut(real32_T u[18])
{
  static const int32_T iv[2] = {0, 0};
  static const int32_T iv1[2] = {1, 18};
  const mxArray *m;
  const mxArray *y;
  y = NULL;
  m = emlrtCreateNumericArray(2, (const void *)&iv[0], mxSINGLE_CLASS, mxREAL);
  emlrtMxSetData((mxArray *)m, &u[0]);
  emlrtSetDimensions((mxArray *)m, &iv1[0], 2);
  emlrtAssign(&y, m);
  return y;
}

/*
 * Arguments    : const mxArray * const prhs[20]
 *                const mxArray **plhs
 * Return Type  : void
 */
void ProcessDataWristsQuat_api(const mxArray *const prhs[20],
                               const mxArray **plhs)
{
  emlrtStack st = {
      NULL, /* site */
      NULL, /* tls */
      NULL  /* prev */
  };
  const mxArray *prhs_copy_idx_0;
  const mxArray *prhs_copy_idx_1;
  const mxArray *prhs_copy_idx_10;
  const mxArray *prhs_copy_idx_11;
  const mxArray *prhs_copy_idx_2;
  const mxArray *prhs_copy_idx_3;
  const mxArray *prhs_copy_idx_4;
  const mxArray *prhs_copy_idx_5;
  const mxArray *prhs_copy_idx_6;
  const mxArray *prhs_copy_idx_7;
  const mxArray *prhs_copy_idx_8;
  const mxArray *prhs_copy_idx_9;
  real32_T(*accX_L)[150];
  real32_T(*accX_R)[150];
  real32_T(*accY_L)[150];
  real32_T(*accY_R)[150];
  real32_T(*accZ_L)[150];
  real32_T(*accZ_R)[150];
  real32_T(*gyrX_L)[150];
  real32_T(*gyrX_R)[150];
  real32_T(*gyrY_L)[150];
  real32_T(*gyrY_R)[150];
  real32_T(*gyrZ_L)[150];
  real32_T(*gyrZ_R)[150];
  real32_T(*quatLW_w)[150];
  real32_T(*quatLW_x)[150];
  real32_T(*quatLW_y)[150];
  real32_T(*quatLW_z)[150];
  real32_T(*quatRW_w)[150];
  real32_T(*quatRW_x)[150];
  real32_T(*quatRW_y)[150];
  real32_T(*quatRW_z)[150];
  real32_T(*imuFeatures)[18];
  st.tls = emlrtRootTLSGlobal;
  imuFeatures = (real32_T(*)[18])mxMalloc(sizeof(real32_T[18]));
  prhs_copy_idx_0 = emlrtProtectR2012b(prhs[0], 0, false, -1);
  prhs_copy_idx_1 = emlrtProtectR2012b(prhs[1], 1, false, -1);
  prhs_copy_idx_2 = emlrtProtectR2012b(prhs[2], 2, false, -1);
  prhs_copy_idx_3 = emlrtProtectR2012b(prhs[3], 3, false, -1);
  prhs_copy_idx_4 = emlrtProtectR2012b(prhs[4], 4, false, -1);
  prhs_copy_idx_5 = emlrtProtectR2012b(prhs[5], 5, false, -1);
  prhs_copy_idx_6 = emlrtProtectR2012b(prhs[6], 6, false, -1);
  prhs_copy_idx_7 = emlrtProtectR2012b(prhs[7], 7, false, -1);
  prhs_copy_idx_8 = emlrtProtectR2012b(prhs[8], 8, false, -1);
  prhs_copy_idx_9 = emlrtProtectR2012b(prhs[9], 9, false, -1);
  prhs_copy_idx_10 = emlrtProtectR2012b(prhs[10], 10, false, -1);
  prhs_copy_idx_11 = emlrtProtectR2012b(prhs[11], 11, false, -1);
  /* Marshall function inputs */
  accX_R = emlrt_marshallIn(&st, emlrtAlias(prhs_copy_idx_0), "accX_R");
  accY_R = emlrt_marshallIn(&st, emlrtAlias(prhs_copy_idx_1), "accY_R");
  accZ_R = emlrt_marshallIn(&st, emlrtAlias(prhs_copy_idx_2), "accZ_R");
  gyrX_R = emlrt_marshallIn(&st, emlrtAlias(prhs_copy_idx_3), "gyrX_R");
  gyrY_R = emlrt_marshallIn(&st, emlrtAlias(prhs_copy_idx_4), "gyrY_R");
  gyrZ_R = emlrt_marshallIn(&st, emlrtAlias(prhs_copy_idx_5), "gyrZ_R");
  accX_L = emlrt_marshallIn(&st, emlrtAlias(prhs_copy_idx_6), "accX_L");
  accY_L = emlrt_marshallIn(&st, emlrtAlias(prhs_copy_idx_7), "accY_L");
  accZ_L = emlrt_marshallIn(&st, emlrtAlias(prhs_copy_idx_8), "accZ_L");
  gyrX_L = emlrt_marshallIn(&st, emlrtAlias(prhs_copy_idx_9), "gyrX_L");
  gyrY_L = emlrt_marshallIn(&st, emlrtAlias(prhs_copy_idx_10), "gyrY_L");
  gyrZ_L = emlrt_marshallIn(&st, emlrtAlias(prhs_copy_idx_11), "gyrZ_L");
  quatRW_x = emlrt_marshallIn(&st, emlrtAlias(prhs[12]), "quatRW_x");
  quatRW_y = emlrt_marshallIn(&st, emlrtAlias(prhs[13]), "quatRW_y");
  quatRW_z = emlrt_marshallIn(&st, emlrtAlias(prhs[14]), "quatRW_z");
  quatRW_w = emlrt_marshallIn(&st, emlrtAlias(prhs[15]), "quatRW_w");
  quatLW_x = emlrt_marshallIn(&st, emlrtAlias(prhs[16]), "quatLW_x");
  quatLW_y = emlrt_marshallIn(&st, emlrtAlias(prhs[17]), "quatLW_y");
  quatLW_z = emlrt_marshallIn(&st, emlrtAlias(prhs[18]), "quatLW_z");
  quatLW_w = emlrt_marshallIn(&st, emlrtAlias(prhs[19]), "quatLW_w");
  /* Invoke the target function */
  ProcessDataWristsQuat(*accX_R, *accY_R, *accZ_R, *gyrX_R, *gyrY_R, *gyrZ_R,
                        *accX_L, *accY_L, *accZ_L, *gyrX_L, *gyrY_L, *gyrZ_L,
                        *quatRW_x, *quatRW_y, *quatRW_z, *quatRW_w, *quatLW_x,
                        *quatLW_y, *quatLW_z, *quatLW_w, *imuFeatures);
  /* Marshall function outputs */
  *plhs = emlrt_marshallOut(*imuFeatures);
}

/*
 * Arguments    : void
 * Return Type  : void
 */
void ProcessDataWristsQuat_atexit(void)
{
  emlrtStack st = {
      NULL, /* site */
      NULL, /* tls */
      NULL  /* prev */
  };
  mexFunctionCreateRootTLS();
  st.tls = emlrtRootTLSGlobal;
  emlrtPushHeapReferenceStackR2021a(
      &st, false, NULL, (void *)&emlrtExitTimeCleanupDtorFcn, NULL, NULL, NULL);
  emlrtEnterRtStackR2012b(&st);
  emlrtDestroyRootTLS(&emlrtRootTLSGlobal);
  ProcessDataWristsQuat_xil_terminate();
  ProcessDataWristsQuat_xil_shutdown();
  emlrtExitTimeCleanup(&emlrtContextGlobal);
}

/*
 * Arguments    : void
 * Return Type  : void
 */
void ProcessDataWristsQuat_initialize(void)
{
  emlrtStack st = {
      NULL, /* site */
      NULL, /* tls */
      NULL  /* prev */
  };
  mexFunctionCreateRootTLS();
  st.tls = emlrtRootTLSGlobal;
  emlrtClearAllocCountR2012b(&st, false, 0U, NULL);
  emlrtEnterRtStackR2012b(&st);
  emlrtFirstTimeR2012b(emlrtRootTLSGlobal);
}

/*
 * Arguments    : void
 * Return Type  : void
 */
void ProcessDataWristsQuat_terminate(void)
{
  emlrtDestroyRootTLS(&emlrtRootTLSGlobal);
}

/*
 * File trailer for _coder_ProcessDataWristsQuat_api.c
 *
 * [EOF]
 */
