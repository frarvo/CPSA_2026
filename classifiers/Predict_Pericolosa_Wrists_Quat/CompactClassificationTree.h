/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 * File: CompactClassificationTree.h
 *
 * MATLAB Coder version            : 25.1
 * C/C++ source code generated on  : 13-Aug-2025 14:37:24
 */

#ifndef COMPACTCLASSIFICATIONTREE_H
#define COMPACTCLASSIFICATIONTREE_H

/* Include Files */
#include "Predict_Pericolosa_Wrists_Quat_internal_types.h"
#include "rtwtypes.h"
#include <stddef.h>
#include <stdlib.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Function Declarations */
int c_CompactClassificationTree_Com(
    double obj_CutPredictorIndex[185], double obj_Children[370],
    double obj_CutPoint[185], double obj_PruneList_data[],
    boolean_T obj_NanCutPoints[185], boolean_T obj_InfCutPoints[185],
    int obj_ClassNamesLength[3],
    c_classreg_learning_coderutils_ *obj_ScoreTransform, double obj_Prior[3],
    boolean_T obj_ClassLogicalIndices[3], double obj_Cost[9],
    double obj_ClassProbability[555]);

double c_CompactClassificationTree_pre(
    const double obj_CutPredictorIndex[185], const double obj_Children[370],
    const double obj_CutPoint[185], const double obj_PruneList_data[],
    const boolean_T obj_NanCutPoints[185], const double obj_Cost[9],
    const double obj_ClassProbability[555], const double Xin[18]);

#ifdef __cplusplus
}
#endif

#endif
/*
 * File trailer for CompactClassificationTree.h
 *
 * [EOF]
 */
