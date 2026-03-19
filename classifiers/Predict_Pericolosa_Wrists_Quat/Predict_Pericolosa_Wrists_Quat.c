/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 * File: Predict_Pericolosa_Wrists_Quat.c
 *
 * MATLAB Coder version            : 25.1
 * C/C++ source code generated on  : 13-Aug-2025 14:37:24
 */

/* Include Files */
#include "Predict_Pericolosa_Wrists_Quat.h"
#include "CompactClassificationTree.h"
#include "Predict_Pericolosa_Wrists_Quat_data.h"
#include "Predict_Pericolosa_Wrists_Quat_initialize.h"
#include "Predict_Pericolosa_Wrists_Quat_internal_types.h"
#include "rt_nonfinite.h"
#include <math.h>

#ifndef MAX_uint8_T
#define MAX_uint8_T ((uint8_T)255U)
#endif

/* Type Definitions */
#ifndef struct_emxArray_real_T_185
#define struct_emxArray_real_T_185
struct emxArray_real_T_185 {
  double data[185];
};
#endif /* struct_emxArray_real_T_185 */
#ifndef typedef_emxArray_real_T_185
#define typedef_emxArray_real_T_185
typedef struct emxArray_real_T_185 emxArray_real_T_185;
#endif /* typedef_emxArray_real_T_185 */

#ifndef d_typedef_c_classreg_learning_c
#define d_typedef_c_classreg_learning_c
typedef struct {
  double CutPredictorIndex[185];
  double Children[370];
  double CutPoint[185];
  emxArray_real_T_185 PruneList;
  boolean_T NanCutPoints[185];
  boolean_T InfCutPoints[185];
  int ClassNamesLength[3];
  c_classreg_learning_coderutils_ ScoreTransform;
  double Prior[3];
  boolean_T ClassLogicalIndices[3];
  double Cost[9];
  double ClassProbability[555];
} c_classreg_learning_classif_Com;
#endif /* d_typedef_c_classreg_learning_c */

/* Variable Definitions */
static boolean_T mdl_not_empty;

/* Function Declarations */
static double rt_roundd_snf(double u);

/* Function Definitions */
/*
 * Arguments    : double u
 * Return Type  : double
 */
static double rt_roundd_snf(double u)
{
  double y;
  if (fabs(u) < 4.503599627370496E+15) {
    if (u >= 0.5) {
      y = floor(u + 0.5);
    } else if (u > -0.5) {
      y = u * 0.0;
    } else {
      y = ceil(u - 0.5);
    }
  } else {
    y = u;
  }
  return y;
}

/*
 * PREDICT_PERICOLOSA_WRISTS_QUAT
 *  Predizione multiclass per distinguere il tipo di stereotipia pericolosa.
 *
 *  INPUT:
 *    x : vettore 1x18 con le feature standard + 2 angoli articolari
 *
 *  OUTPUT:
 *    label : intero (1, 2 o 3)
 *        Classe della stereotipia pericolosa (definita nel training)
 *
 * Arguments    : const float x[18]
 * Return Type  : unsigned char
 */
unsigned char Predict_Pericolosa_Wrists_Quat(const float x[18])
{
  static c_classreg_learning_classif_Com mdl;
  double b_x[18];
  double d;
  int i;
  unsigned char label;
  if (!isInitialized_Predict_Pericolosa_Wrists_Quat) {
    Predict_Pericolosa_Wrists_Quat_initialize();
  }
  if (!mdl_not_empty) {
    c_CompactClassificationTree_Com(
        mdl.CutPredictorIndex, mdl.Children, mdl.CutPoint, mdl.PruneList.data,
        mdl.NanCutPoints, mdl.InfCutPoints, mdl.ClassNamesLength,
        &mdl.ScoreTransform, mdl.Prior, mdl.ClassLogicalIndices, mdl.Cost,
        mdl.ClassProbability);
    mdl_not_empty = true;
    /*  saved model */
  }
  for (i = 0; i < 18; i++) {
    b_x[i] = x[i];
  }
  /*   trained on double */
  d = rt_roundd_snf(c_CompactClassificationTree_pre(
      mdl.CutPredictorIndex, mdl.Children, mdl.CutPoint, mdl.PruneList.data,
      mdl.NanCutPoints, mdl.Cost, mdl.ClassProbability, b_x));
  if (d < 256.0) {
    if (d >= 0.0) {
      label = (unsigned char)d;
    } else {
      label = 0U;
    }
  } else if (d >= 256.0) {
    label = MAX_uint8_T;
  } else {
    label = 0U;
  }
  return label;
}

/*
 * Arguments    : void
 * Return Type  : void
 */
void c_Predict_Pericolosa_Wrists_Qua(void)
{
  mdl_not_empty = false;
}

/*
 * File trailer for Predict_Pericolosa_Wrists_Quat.c
 *
 * [EOF]
 */
