"""
train.py
---------
Purpose:
- Implements Step 6 of the FinSight AI machine learning pipeline.
- Trains a global XGBoost multiclass classification model for 1-day stock trend prediction.
- Loads the chronological 70/15/15 train/validation/test splits from Step 5.
- Performs a controlled baseline + hyperparameter search using validation macro F1.
- Uses early stopping on the validation set; test data is never touched during tuning.
- Evaluates the final selected model once on the held-out test set.
- Saves the trained model, metadata JSON, feature importance CSV, and test predictions CSV.

Target Classes:
  0 = DOWN   (next-day return < -1%)
  1 = FLAT   (next-day return [-1%, +1%])
  2 = UP     (next-day return > +1%)

Model: XGBoost 3.4.1 — XGBClassifier — multi:softprob — CPU hist tree method.

Usage:
  python src/train.py
"""

import json
import sys
import warnings
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
SPLITS_DIR = BASE_DIR / "data" / "splits"
MODELS_DIR = BASE_DIR / "models"

TRAIN_CSV = SPLITS_DIR / "train.csv"
VAL_CSV = SPLITS_DIR / "validation.csv"
TEST_CSV = SPLITS_DIR / "test.csv"
FEATURE_JSON = SPLITS_DIR / "feature_columns.json"
TARGET_JSON = SPLITS_DIR / "target_definition.json"

MODEL_FILE = MODELS_DIR / "xgboost_trend_model.json"
METADATA_FILE = MODELS_DIR / "model_metadata.json"
FEAT_IMP_FILE = MODELS_DIR / "feature_importance.csv"
TEST_PRED_FILE = MODELS_DIR / "test_predictions.csv"

# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------
RANDOM_STATE = 42
TARGET_COL = "Trend_Code"
LABEL_COL = "Trend_Label"
CODE_TO_LABEL = {0: "DOWN", 1: "FLAT", 2: "UP"}
LABEL_TO_CODE = {"DOWN": 0, "FLAT": 1, "UP": 2}
N_CLASSES = 3


# -------------------------------------------------------------------
# Data Loading
# -------------------------------------------------------------------

def load_splits(
    feature_cols: List[str],
) -> Tuple[
    pd.DataFrame, pd.Series, pd.DataFrame,
    pd.DataFrame, pd.Series, pd.DataFrame,
    pd.DataFrame, pd.Series, pd.DataFrame,
]:
    """
    Loads and validates the train / validation / test splits from disk.

    Args:
        feature_cols: Ordered list of 17 feature column names.

    Returns:
        Tuple of (X_train, y_train, meta_train,
                  X_val, y_val, meta_val,
                  X_test, y_test, meta_test)
    """
    print("Loading split datasets...")
    train_df = pd.read_csv(TRAIN_CSV)
    val_df = pd.read_csv(VAL_CSV)
    test_df = pd.read_csv(TEST_CSV)

    print(f"  Train rows   : {len(train_df):,}")
    print(f"  Val rows     : {len(val_df):,}")
    print(f"  Test rows    : {len(test_df):,}")

    meta_cols = ["Date", "Ticker", "Market", LABEL_COL]

    for split_name, df in [("train", train_df), ("validation", val_df), ("test", test_df)]:
        # Verify feature columns present
        missing = [c for c in feature_cols if c not in df.columns]
        if missing:
            raise KeyError(f"Missing feature columns in {split_name}: {missing}")

        # Verify target column present
        if TARGET_COL not in df.columns:
            raise KeyError(f"Target column '{TARGET_COL}' missing from {split_name}.")

        # Verify no forbidden columns in X
        X_check = df[feature_cols]
        if TARGET_COL in X_check.columns:
            raise ValueError(f"Target column leaked into features in {split_name}!")

        # Verify no NaN / Inf in features
        if X_check.isna().any().any():
            raise ValueError(f"NaN values in feature matrix for {split_name}.")
        if np.isinf(X_check.values).any():
            raise ValueError(f"Infinite values in feature matrix for {split_name}.")

        # Verify feature order uniformity
        if list(X_check.columns) != feature_cols:
            raise ValueError(f"Feature column order mismatch in {split_name}.")

    # Construct X and y
    X_train = train_df[feature_cols].astype(np.float32)
    y_train = train_df[TARGET_COL].astype(np.int32)
    meta_train = train_df[meta_cols]

    X_val = val_df[feature_cols].astype(np.float32)
    y_val = val_df[TARGET_COL].astype(np.int32)
    meta_val = val_df[meta_cols]

    X_test = test_df[feature_cols].astype(np.float32)
    y_test = test_df[TARGET_COL].astype(np.int32)
    meta_test = test_df[meta_cols]

    print("Data loading and validation completed.")
    return X_train, y_train, meta_train, X_val, y_val, meta_val, X_test, y_test, meta_test


# -------------------------------------------------------------------
# Model Evaluation
# -------------------------------------------------------------------

def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    split_name: str,
) -> Dict[str, Any]:
    """
    Computes classification metrics for a split, including per-class stats and OvR ROC-AUC.

    Args:
        y_true: Ground-truth integer class labels.
        y_pred: Predicted integer class labels.
        y_prob: Predicted class probability matrix (n_samples, 3).
        split_name: Name of the split for labeling output.

    Returns:
        Dict of metric names to values.
    """
    acc = accuracy_score(y_true, y_pred)
    prec_macro = precision_score(y_true, y_pred, average="macro", zero_division=0)
    prec_weighted = precision_score(y_true, y_pred, average="weighted", zero_division=0)
    rec_macro = recall_score(y_true, y_pred, average="macro", zero_division=0)
    rec_weighted = recall_score(y_true, y_pred, average="weighted", zero_division=0)
    f1_macro = f1_score(y_true, y_pred, average="macro", zero_division=0)
    f1_weighted = f1_score(y_true, y_pred, average="weighted", zero_division=0)

    # Per-class metrics
    class_prec = precision_score(y_true, y_pred, average=None, zero_division=0, labels=[0, 1, 2])
    class_rec = recall_score(y_true, y_pred, average=None, zero_division=0, labels=[0, 1, 2])
    class_f1 = f1_score(y_true, y_pred, average=None, zero_division=0, labels=[0, 1, 2])

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])

    # Multiclass ROC-AUC (One-vs-Rest)
    try:
        roc_auc_ovr = roc_auc_score(y_true, y_prob, multi_class="ovr", average="macro")
    except Exception:
        roc_auc_ovr = None

    report = classification_report(y_true, y_pred, target_names=["DOWN", "FLAT", "UP"], zero_division=0)

    metrics = {
        "split": split_name,
        "accuracy": float(acc),
        "precision_macro": float(prec_macro),
        "precision_weighted": float(prec_weighted),
        "recall_macro": float(rec_macro),
        "recall_weighted": float(rec_weighted),
        "f1_macro": float(f1_macro),
        "f1_weighted": float(f1_weighted),
        "roc_auc_ovr_macro": float(roc_auc_ovr) if roc_auc_ovr is not None else None,
        "per_class": {
            "DOWN":  {"precision": float(class_prec[0]), "recall": float(class_rec[0]), "f1": float(class_f1[0])},
            "FLAT":  {"precision": float(class_prec[1]), "recall": float(class_rec[1]), "f1": float(class_f1[1])},
            "UP":    {"precision": float(class_prec[2]), "recall": float(class_rec[2]), "f1": float(class_f1[2])},
        },
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
    }

    return metrics


def print_metrics(metrics: Dict[str, Any]) -> None:
    """Prints formatted evaluation metrics to stdout."""
    split = metrics["split"]
    print(f"\n{'=' * 60}")
    print(f"  Evaluation Metrics — {split.upper()} SET")
    print(f"{'=' * 60}")
    print(f"  Accuracy          : {metrics['accuracy']:.4f}  ({metrics['accuracy']*100:.2f}%)")
    print(f"  Precision (macro) : {metrics['precision_macro']:.4f}")
    print(f"  Precision (wgtd)  : {metrics['precision_weighted']:.4f}")
    print(f"  Recall    (macro) : {metrics['recall_macro']:.4f}")
    print(f"  Recall    (wgtd)  : {metrics['recall_weighted']:.4f}")
    print(f"  F1        (macro) : {metrics['f1_macro']:.4f}")
    print(f"  F1        (wgtd)  : {metrics['f1_weighted']:.4f}")
    if metrics["roc_auc_ovr_macro"] is not None:
        print(f"  ROC-AUC (OvR)     : {metrics['roc_auc_ovr_macro']:.4f}")
    print(f"\n  Per-Class Metrics:")
    print(f"  {'Class':<8} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print(f"  {'-'*40}")
    for cls in ["DOWN", "FLAT", "UP"]:
        pc = metrics["per_class"][cls]
        print(f"  {cls:<8} {pc['precision']:>10.4f} {pc['recall']:>10.4f} {pc['f1']:>10.4f}")
    print(f"\n  Confusion Matrix (rows=Actual, cols=Predicted):")
    cm = metrics["confusion_matrix"]
    print(f"  {'':>8} {'DOWN':>8} {'FLAT':>8} {'UP':>8}")
    for i, label in enumerate(["DOWN", "FLAT", "UP"]):
        row = cm[i]
        print(f"  {label:>8} {row[0]:>8} {row[1]:>8} {row[2]:>8}")
    print(f"\n  Classification Report:\n{metrics['classification_report']}")


# -------------------------------------------------------------------
# Model Training
# -------------------------------------------------------------------

def build_base_params() -> Dict[str, Any]:
    """Returns the baseline XGBoost hyperparameter dictionary."""
    return {
        "objective": "multi:softprob",
        "num_class": N_CLASSES,
        "n_estimators": 500,
        "learning_rate": 0.05,
        "max_depth": 6,
        "min_child_weight": 1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.0,
        "reg_lambda": 1.0,
        "tree_method": "hist",
        "random_state": RANDOM_STATE,
        "verbosity": 0,
        "n_jobs": -1,
    }


def train_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    params: Dict[str, Any],
    early_stopping_rounds: int = 30,
) -> xgb.XGBClassifier:
    """
    Trains an XGBClassifier with the given parameters and early stopping on validation.

    Args:
        X_train, y_train: Training feature matrix and labels.
        X_val, y_val: Validation set used only for early stopping.
        params: XGBoost hyperparameter dict.
        early_stopping_rounds: Stop if no improvement in this many rounds.

    Returns:
        Fitted XGBClassifier.
    """
    model = xgb.XGBClassifier(
        **params,
        early_stopping_rounds=early_stopping_rounds,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )
    return model


def hyperparameter_search(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
) -> Tuple[Dict[str, Any], float, xgb.XGBClassifier]:
    """
    Controlled hyperparameter search over a small grid.
    Selects the best configuration by validation macro F1.

    Grid:
      learning_rate: [0.03, 0.05, 0.1]
      max_depth:     [4, 6, 8]
      min_child_weight: [1, 3, 5]
      subsample:     [0.8, 1.0]
      colsample_bytree: [0.8, 1.0]

    Args:
        X_train, y_train: Training data.
        X_val, y_val: Validation data.

    Returns:
        Tuple of (best_params, best_val_f1_macro, best_model)
    """
    # Reduced grid to keep training feasible
    search_grid = {
        "learning_rate": [0.03, 0.05, 0.1],
        "max_depth": [4, 6, 8],
        "min_child_weight": [1, 3, 5],
        "subsample": [0.8, 1.0],
        "colsample_bytree": [0.8, 1.0],
    }

    # Build all combinations
    keys = list(search_grid.keys())
    all_combos = list(product(*search_grid.values()))
    total = len(all_combos)
    print(f"\nHyperparameter search: {total} combinations over {len(keys)} parameters.")
    print("Selection criterion: Validation Macro F1")

    best_f1 = -1.0
    best_params = None
    best_model = None

    for i, combo in enumerate(all_combos, start=1):
        params = build_base_params()
        for k, v in zip(keys, combo):
            params[k] = v

        model = train_model(X_train, y_train, X_val, y_val, params, early_stopping_rounds=30)
        y_pred = model.predict(X_val)
        f1 = f1_score(y_val, y_pred, average="macro", zero_division=0)

        if f1 > best_f1:
            best_f1 = f1
            best_params = params.copy()
            best_model = model
            print(f"  [{i:>3}/{total}] NEW BEST — F1={f1:.4f} | lr={combo[0]} depth={combo[1]} mcw={combo[2]} sub={combo[3]} cstree={combo[4]}")
        else:
            if i % 30 == 0:
                print(f"  [{i:>3}/{total}] Best so far F1={best_f1:.4f}")

    print(f"\nSearch complete. Best validation macro F1: {best_f1:.4f}")
    return best_params, best_f1, best_model


# -------------------------------------------------------------------
# Feature Importance
# -------------------------------------------------------------------

def compute_feature_importance(
    model: xgb.XGBClassifier,
    feature_cols: List[str],
) -> pd.DataFrame:
    """
    Computes gain-based feature importance from the trained model.

    Args:
        model: Fitted XGBClassifier.
        feature_cols: List of feature names.

    Returns:
        DataFrame sorted by importance descending.
    """
    booster = model.get_booster()
    scores = booster.get_score(importance_type="gain")
    df_imp = pd.DataFrame([
        {"Feature": f, "Gain": scores.get(f, 0.0)}
        for f in feature_cols
    ])
    df_imp = df_imp.sort_values("Gain", ascending=False).reset_index(drop=True)
    df_imp["Rank"] = range(1, len(df_imp) + 1)
    return df_imp[["Rank", "Feature", "Gain"]]


# -------------------------------------------------------------------
# Test Predictions
# -------------------------------------------------------------------

def create_test_predictions(
    model: xgb.XGBClassifier,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    meta_test: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generates a detailed prediction audit table for the held-out test set.

    Args:
        model: Fitted XGBClassifier.
        X_test: Test feature matrix.
        y_test: Test ground-truth labels.
        meta_test: Test metadata (Date, Ticker, Market, Trend_Label).

    Returns:
        DataFrame with prediction details.
    """
    y_prob = model.predict_proba(X_test)
    y_pred = np.argmax(y_prob, axis=1)

    pred_df = meta_test.reset_index(drop=True).copy()
    pred_df["Actual_Code"] = y_test.reset_index(drop=True).values
    pred_df["Predicted_Code"] = y_pred
    pred_df["Actual_Label"] = pred_df["Actual_Code"].map(CODE_TO_LABEL)
    pred_df["Predicted_Label"] = pred_df["Predicted_Code"].map(CODE_TO_LABEL)
    pred_df["Probability_DOWN"] = y_prob[:, 0]
    pred_df["Probability_FLAT"] = y_prob[:, 1]
    pred_df["Probability_UP"] = y_prob[:, 2]
    pred_df["Confidence"] = y_prob.max(axis=1)

    output_cols = [
        "Date", "Ticker", "Market",
        "Actual_Label", "Predicted_Label",
        "Actual_Code", "Predicted_Code",
        "Probability_DOWN", "Probability_FLAT", "Probability_UP",
        "Confidence",
    ]
    return pred_df[output_cols]


# -------------------------------------------------------------------
# Main Pipeline
# -------------------------------------------------------------------

def main() -> None:
    """
    Main training orchestration for Step 6:
    1. Load data and validate.
    2. Train baseline XGBoost model.
    3. Perform controlled hyperparameter search.
    4. Evaluate final selected model on validation set.
    5. Evaluate once on untouched test set.
    6. Save model, metadata, feature importance, and test predictions.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  FinSight AI - Step 6: XGBoost Trend Prediction Model Training")
    print("=" * 70)
    print(f"  XGBoost version : {xgb.__version__}")
    print(f"  Random seed     : {RANDOM_STATE}")
    print(f"  Tree method     : hist (CPU)")
    print(f"  Objective       : multi:softprob (3 classes)")
    print(f"  Training start  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # -------------------------------------------------------------------
    # 1. Load feature and target configs
    # -------------------------------------------------------------------
    with open(FEATURE_JSON, "r") as f:
        feature_cols: List[str] = json.load(f)
    with open(TARGET_JSON, "r") as f:
        target_def: Dict[str, Any] = json.load(f)

    assert len(feature_cols) == 17, f"Expected 17 features, got {len(feature_cols)}"
    assert target_def["target_name"] == TARGET_COL, "Target column mismatch."

    print(f"\nFeature matrix X : {len(feature_cols)} features")
    print(f"Target column y  : {TARGET_COL}")

    # -------------------------------------------------------------------
    # 2. Load and validate splits
    # -------------------------------------------------------------------
    (X_train, y_train, meta_train,
     X_val, y_val, meta_val,
     X_test, y_test, meta_test) = load_splits(feature_cols)

    print(f"\nClass distribution — TRAIN:")
    for code, label in CODE_TO_LABEL.items():
        cnt = (y_train == code).sum()
        print(f"  {label:<5} (Code {code}): {cnt:>6,} ({cnt/len(y_train)*100:.1f}%)")

    # -------------------------------------------------------------------
    # 3. Train Baseline Model
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  BASELINE MODEL TRAINING")
    print("=" * 70)
    baseline_params = build_base_params()
    print(f"Baseline params: lr={baseline_params['learning_rate']}, depth={baseline_params['max_depth']}, "
          f"mcw={baseline_params['min_child_weight']}, sub={baseline_params['subsample']}, "
          f"cstree={baseline_params['colsample_bytree']}")

    baseline_model = train_model(X_train, y_train, X_val, y_val, baseline_params, early_stopping_rounds=30)
    b_pred = baseline_model.predict(X_val)
    b_prob = baseline_model.predict_proba(X_val)
    baseline_metrics = compute_metrics(y_val.values, b_pred, b_prob, "Validation (Baseline)")
    print_metrics(baseline_metrics)

    # Naive baseline: always predict FLAT (majority class)
    majority_pred = np.ones(len(y_val), dtype=int)  # FLAT = 1
    majority_f1 = f1_score(y_val, majority_pred, average="macro", zero_division=0)
    majority_acc = accuracy_score(y_val, majority_pred)
    print(f"  [Baseline Comparison] Majority-class (FLAT) Accuracy={majority_acc:.4f}, Macro F1={majority_f1:.4f}")
    print(f"  XGBoost Baseline beats majority-class on Macro F1: "
          f"{'YES' if baseline_metrics['f1_macro'] > majority_f1 else 'NO'}")

    # -------------------------------------------------------------------
    # 4. Hyperparameter Search
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  HYPERPARAMETER SEARCH")
    print("=" * 70)
    best_params, best_val_f1, best_model = hyperparameter_search(
        X_train, y_train, X_val, y_val
    )
    print(f"\nSelected hyperparameters:")
    for k in ["learning_rate", "max_depth", "min_child_weight", "subsample", "colsample_bytree"]:
        print(f"  {k:<22}: {best_params[k]}")
    print(f"  best_iteration     : {best_model.best_iteration}")

    val_pred = best_model.predict(X_val)
    val_prob = best_model.predict_proba(X_val)
    val_metrics = compute_metrics(y_val.values, val_pred, val_prob, "Validation (Best)")
    print_metrics(val_metrics)

    # Improvement over baseline
    improvement_f1 = val_metrics["f1_macro"] - baseline_metrics["f1_macro"]
    print(f"  F1 Macro improvement over baseline: {improvement_f1:+.4f}")

    # -------------------------------------------------------------------
    # 5. Final Test Evaluation (once, untouched)
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  FINAL TEST SET EVALUATION (held-out, evaluated once)")
    print("=" * 70)
    test_pred = best_model.predict(X_test)
    test_prob = best_model.predict_proba(X_test)
    test_metrics = compute_metrics(y_test.values, test_pred, test_prob, "Test (Final)")
    print_metrics(test_metrics)

    # Compare to naive baseline on test set
    majority_pred_test = np.ones(len(y_test), dtype=int)
    majority_f1_test = f1_score(y_test, majority_pred_test, average="macro", zero_division=0)
    majority_acc_test = accuracy_score(y_test, majority_pred_test)
    print(f"  [Test Baseline] Majority-class (FLAT) Accuracy={majority_acc_test:.4f}, Macro F1={majority_f1_test:.4f}")
    print(f"  Model beats majority-class on Test Macro F1: "
          f"{'YES' if test_metrics['f1_macro'] > majority_f1_test else 'NO'}")

    # -------------------------------------------------------------------
    # 6. Feature Importance
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  FEATURE IMPORTANCE (Gain-Based, Top 10)")
    print("=" * 70)
    feat_imp_df = compute_feature_importance(best_model, feature_cols)
    print(feat_imp_df.head(10).to_string(index=False))
    feat_imp_df.to_csv(FEAT_IMP_FILE, index=False)
    print(f"\n[SAVED] Feature importance: {FEAT_IMP_FILE}")

    # -------------------------------------------------------------------
    # 7. Save Model
    # -------------------------------------------------------------------
    best_model.save_model(str(MODEL_FILE))
    print(f"[SAVED] Model: {MODEL_FILE}")

    # -------------------------------------------------------------------
    # 8. Save Test Predictions
    # -------------------------------------------------------------------
    test_pred_df = create_test_predictions(best_model, X_test, y_test, meta_test)
    test_pred_df.to_csv(TEST_PRED_FILE, index=False)
    print(f"[SAVED] Test predictions: {TEST_PRED_FILE} ({len(test_pred_df):,} rows)")

    # -------------------------------------------------------------------
    # 9. Save Model Metadata
    # -------------------------------------------------------------------
    import sys as _sys
    training_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    metadata = {
        "model_type": "XGBClassifier",
        "objective": "multi:softprob",
        "num_classes": N_CLASSES,
        "class_mapping": CODE_TO_LABEL,
        "random_seed": RANDOM_STATE,
        "tree_method": "hist (CPU)",
        "xgboost_version": xgb.__version__,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "python_version": _sys.version.split(" ")[0],
        "training_datetime": training_time,
        "feature_names": feature_cols,
        "feature_count": len(feature_cols),
        "target_name": TARGET_COL,
        "target_definition": target_def,
        "train_row_count": int(len(X_train)),
        "validation_row_count": int(len(X_val)),
        "test_row_count": int(len(X_test)),
        "best_iteration": int(best_model.best_iteration),
        "selected_hyperparameters": {
            "n_estimators": best_params["n_estimators"],
            "learning_rate": best_params["learning_rate"],
            "max_depth": best_params["max_depth"],
            "min_child_weight": best_params["min_child_weight"],
            "subsample": best_params["subsample"],
            "colsample_bytree": best_params["colsample_bytree"],
            "reg_alpha": best_params["reg_alpha"],
            "reg_lambda": best_params["reg_lambda"],
            "early_stopping_rounds": 30,
        },
        "baseline_val_metrics": {
            "accuracy": baseline_metrics["accuracy"],
            "f1_macro": baseline_metrics["f1_macro"],
        },
        "majority_class_baseline": {
            "val_accuracy": float(majority_acc),
            "val_f1_macro": float(majority_f1),
            "test_accuracy": float(majority_acc_test),
            "test_f1_macro": float(majority_f1_test),
        },
        "validation_metrics": {
            "accuracy": val_metrics["accuracy"],
            "precision_macro": val_metrics["precision_macro"],
            "precision_weighted": val_metrics["precision_weighted"],
            "recall_macro": val_metrics["recall_macro"],
            "recall_weighted": val_metrics["recall_weighted"],
            "f1_macro": val_metrics["f1_macro"],
            "f1_weighted": val_metrics["f1_weighted"],
            "roc_auc_ovr_macro": val_metrics["roc_auc_ovr_macro"],
            "per_class": val_metrics["per_class"],
            "confusion_matrix": val_metrics["confusion_matrix"],
        },
        "test_metrics": {
            "accuracy": test_metrics["accuracy"],
            "precision_macro": test_metrics["precision_macro"],
            "precision_weighted": test_metrics["precision_weighted"],
            "recall_macro": test_metrics["recall_macro"],
            "recall_weighted": test_metrics["recall_weighted"],
            "f1_macro": test_metrics["f1_macro"],
            "f1_weighted": test_metrics["f1_weighted"],
            "roc_auc_ovr_macro": test_metrics["roc_auc_ovr_macro"],
            "per_class": test_metrics["per_class"],
            "confusion_matrix": test_metrics["confusion_matrix"],
        },
        "model_artifacts": {
            "model_file": str(MODEL_FILE),
            "metadata_file": str(METADATA_FILE),
            "feature_importance_file": str(FEAT_IMP_FILE),
            "test_predictions_file": str(TEST_PRED_FILE),
        },
    }

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"[SAVED] Metadata: {METADATA_FILE}")

    # -------------------------------------------------------------------
    # Final Summary
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  STEP 6 COMPLETE — TRAINING SUMMARY")
    print("=" * 70)
    print(f"  Model            : XGBoost {xgb.__version__} (CPU hist)")
    print(f"  Best Iteration   : {best_model.best_iteration}")
    print(f"  Val  Accuracy    : {val_metrics['accuracy']:.4f}")
    print(f"  Val  F1 (macro)  : {val_metrics['f1_macro']:.4f}")
    print(f"  Val  ROC-AUC     : {val_metrics['roc_auc_ovr_macro']:.4f}")
    print(f"  Test Accuracy    : {test_metrics['accuracy']:.4f}")
    print(f"  Test F1 (macro)  : {test_metrics['f1_macro']:.4f}")
    print(f"  Test ROC-AUC     : {test_metrics['roc_auc_ovr_macro']:.4f}")
    print(f"  Beats FLAT-only baseline (Test F1): "
          f"{'YES' if test_metrics['f1_macro'] > majority_f1_test else 'NO'}")
    print(f"  Saved model      : {MODEL_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()
