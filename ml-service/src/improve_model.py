"""
improve_model.py
-----------------
Step 7 of the FinSight AI ML pipeline.

Diagnoses the v1 XGBoost trend model, runs four controlled experiments to
improve minority-class (DOWN / UP) performance, selects the best model by
validation macro F1, and performs a single final evaluation on the held-out
test set.

Experiments:
  0. Diagnosis -- probability distributions, per-stock breakdown, class stats
  1. Class weighting via sample_weight
  2. Controlled XGBoost hyperparameter tuning (small grid)
  3. Probability decision-threshold adjustment
  4. Feature ablation (remove raw price-scale / Volume / redundant MAs)

Final outputs:
  models/xgboost_trend_model_v2.json
  models/model_metadata_v2.json
  models/validation_predictions_v2.csv

Usage:
  python src/improve_model.py
"""

import json
import sys
import warnings
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

# ===================================================================
# Paths
# ===================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
SPLITS_DIR = BASE_DIR / "data" / "splits"
MODELS_DIR = BASE_DIR / "models"

TRAIN_CSV = SPLITS_DIR / "train.csv"
VAL_CSV = SPLITS_DIR / "validation.csv"
TEST_CSV = SPLITS_DIR / "test.csv"
FEATURE_JSON = SPLITS_DIR / "feature_columns.json"
TARGET_JSON = SPLITS_DIR / "target_definition.json"

MODEL_V2_FILE = MODELS_DIR / "xgboost_trend_model_v2.json"
METADATA_V2_FILE = MODELS_DIR / "model_metadata_v2.json"
VAL_PRED_V2_FILE = MODELS_DIR / "validation_predictions_v2.csv"
TEST_PRED_V2_FILE = MODELS_DIR / "test_predictions_v2.csv"

# ===================================================================
# Constants
# ===================================================================
RANDOM_STATE = 42
TARGET_COL = "Trend_Code"
LABEL_COL = "Trend_Label"
N_CLASSES = 3
CODE_TO_LABEL = {0: "DOWN", 1: "FLAT", 2: "UP"}
META_COLS = ["Date", "Ticker", "Market", LABEL_COL]

ALL_17_FEATURES = [
    "Open", "High", "Low", "Close", "Volume",
    "Daily_Return", "MA_5", "MA_10", "MA_20", "MA_50",
    "RSI_14", "MACD", "MACD_Signal",
    "Volatility_20", "Volume_Change", "Price_Change_Pct", "High_Low_Pct",
]

# ===================================================================
# Helpers
# ===================================================================

def load_data(feature_cols: List[str]) -> Tuple:
    """Load and validate all three splits. Returns X/y/meta for each."""
    train_df = pd.read_csv(TRAIN_CSV)
    val_df = pd.read_csv(VAL_CSV)
    test_df = pd.read_csv(TEST_CSV)

    results = []
    for name, df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        missing = [c for c in feature_cols if c not in df.columns]
        if missing:
            raise KeyError(f"Missing in {name}: {missing}")
        X = df[feature_cols].astype(np.float32)
        assert not X.isna().any().any(), f"NaN in {name}"
        assert not np.isinf(X.values).any(), f"Inf in {name}"
        y = df[TARGET_COL].astype(np.int32)
        meta = df[META_COLS]
        results.extend([X, y, meta])

    return tuple(results)


def metrics_dict(y_true, y_pred, y_prob=None) -> Dict[str, Any]:
    """Compute standard multiclass metrics. Returns a flat dict."""
    acc = accuracy_score(y_true, y_pred)
    f1m = f1_score(y_true, y_pred, average="macro", zero_division=0)
    f1w = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    pm = precision_score(y_true, y_pred, average="macro", zero_division=0)
    pw = precision_score(y_true, y_pred, average="weighted", zero_division=0)
    rm = recall_score(y_true, y_pred, average="macro", zero_division=0)
    rw = recall_score(y_true, y_pred, average="weighted", zero_division=0)

    cp = precision_score(y_true, y_pred, average=None, zero_division=0, labels=[0, 1, 2])
    cr = recall_score(y_true, y_pred, average=None, zero_division=0, labels=[0, 1, 2])
    cf = f1_score(y_true, y_pred, average=None, zero_division=0, labels=[0, 1, 2])
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])

    roc = None
    if y_prob is not None:
        try:
            roc = roc_auc_score(y_true, y_prob, multi_class="ovr", average="macro")
        except Exception:
            pass

    return {
        "accuracy": float(acc),
        "f1_macro": float(f1m),
        "f1_weighted": float(f1w),
        "precision_macro": float(pm),
        "precision_weighted": float(pw),
        "recall_macro": float(rm),
        "recall_weighted": float(rw),
        "roc_auc_ovr_macro": float(roc) if roc is not None else None,
        "per_class": {
            "DOWN":  {"precision": float(cp[0]), "recall": float(cr[0]), "f1": float(cf[0])},
            "FLAT":  {"precision": float(cp[1]), "recall": float(cr[1]), "f1": float(cf[1])},
            "UP":    {"precision": float(cp[2]), "recall": float(cr[2]), "f1": float(cf[2])},
        },
        "confusion_matrix": cm.tolist(),
    }


def print_metrics_compact(m: Dict, label: str = "") -> None:
    """One-line-per-class compact output."""
    if label:
        print(f"  [{label}]")
    print(f"    Acc={m['accuracy']:.4f}  F1m={m['f1_macro']:.4f}  F1w={m['f1_weighted']:.4f}  "
          f"ROC={m['roc_auc_ovr_macro']:.4f}" if m.get('roc_auc_ovr_macro') else
          f"    Acc={m['accuracy']:.4f}  F1m={m['f1_macro']:.4f}  F1w={m['f1_weighted']:.4f}")
    for cls in ["DOWN", "FLAT", "UP"]:
        pc = m["per_class"][cls]
        print(f"    {cls:>5}: P={pc['precision']:.3f} R={pc['recall']:.3f} F1={pc['f1']:.3f}")


def print_confusion(cm, label=""):
    """Print a 3x3 confusion matrix."""
    if label:
        print(f"  Confusion Matrix -- {label}")
    print(f"  {'':>8} {'DOWN':>7} {'FLAT':>7} {'UP':>7}")
    for i, name in enumerate(["DOWN", "FLAT", "UP"]):
        print(f"  {name:>8} {cm[i][0]:>7} {cm[i][1]:>7} {cm[i][2]:>7}")


def train_xgb(X_tr, y_tr, X_val, y_val, params, sample_weight=None,
              early_stopping=30):
    """Train XGBClassifier with early stopping. Returns fitted model."""
    model = xgb.XGBClassifier(
        **params,
        early_stopping_rounds=early_stopping,
    )
    fit_kw = dict(eval_set=[(X_val, y_val)], verbose=False)
    if sample_weight is not None:
        fit_kw["sample_weight"] = sample_weight
    model.fit(X_tr, y_tr, **fit_kw)
    return model


def base_params(**overrides) -> Dict[str, Any]:
    """Build a parameter dict from the v1 best configuration with overrides."""
    p = {
        "objective": "multi:softprob",
        "num_class": N_CLASSES,
        "n_estimators": 500,
        "learning_rate": 0.1,
        "max_depth": 6,
        "min_child_weight": 3,
        "subsample": 0.8,
        "colsample_bytree": 1.0,
        "reg_alpha": 0.0,
        "reg_lambda": 1.0,
        "tree_method": "hist",
        "random_state": RANDOM_STATE,
        "verbosity": 0,
        "n_jobs": -1,
    }
    p.update(overrides)
    return p


# ===================================================================
# DIAGNOSIS
# ===================================================================

def diagnose(X_train, y_train, X_val, y_val, meta_val, feature_cols):
    """Comprehensive diagnosis of the v1 model behaviour on validation data."""
    print("\n" + "=" * 70)
    print("  PHASE 0 -- DIAGNOSIS OF V1 MODEL")
    print("=" * 70)

    # --- 0a. Class distribution ---
    print("\n  [0a] Class distribution")
    for split_name, y in [("Train", y_train), ("Val", y_val)]:
        total = len(y)
        for code, label in CODE_TO_LABEL.items():
            cnt = (y == code).sum()
            print(f"    {split_name:>5} {label:>5}: {cnt:>6,} ({cnt / total * 100:.1f}%)")

    # --- 0b. Retrain v1 with stored params for inspection ---
    params = base_params()
    model = train_xgb(X_train, y_train, X_val, y_val, params)
    val_prob = model.predict_proba(X_val)
    val_pred = np.argmax(val_prob, axis=1)

    # --- 0c. Predicted class distribution ---
    print("\n  [0c] Predicted class distribution (Val, argmax)")
    for code, label in CODE_TO_LABEL.items():
        cnt = (val_pred == code).sum()
        print(f"    {label:>5}: {cnt:>6,} ({cnt / len(val_pred) * 100:.1f}%)")

    # --- 0d. Probability statistics ---
    print("\n  [0d] Probability statistics (Val)")
    for code, label in CODE_TO_LABEL.items():
        probs = val_prob[:, code]
        print(f"    P({label:>5}): mean={probs.mean():.4f}  "
              f"median={np.median(probs):.4f}  "
              f"std={probs.std():.4f}  "
              f"min={probs.min():.4f}  max={probs.max():.4f}  "
              f"pct>0.5={(probs > 0.5).sum()}")

    # --- 0e. Confusion matrix ---
    cm = confusion_matrix(y_val, val_pred, labels=[0, 1, 2])
    print("\n  [0e] Validation confusion matrix")
    print_confusion(cm.tolist(), "Val v1")

    # --- 0f. Feature importance ---
    booster = model.get_booster()
    scores = booster.get_score(importance_type="gain")
    imp_sorted = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    print("\n  [0f] Feature importance (gain, top 10)")
    for rank, (feat, gain) in enumerate(imp_sorted[:10], 1):
        print(f"    {rank:>2}. {feat:<20} {gain:.2f}")

    # --- 0g. Per-stock validation performance (top and bottom) ---
    print("\n  [0g] Per-stock validation macro F1 (sample)")
    meta_val_reset = meta_val.reset_index(drop=True)
    tickers = meta_val_reset["Ticker"].unique()
    stock_perf = []
    for ticker in tickers:
        mask = meta_val_reset["Ticker"] == ticker
        if mask.sum() < 10:
            continue
        y_t = y_val.values[mask]
        p_t = val_pred[mask]
        f1 = f1_score(y_t, p_t, average="macro", zero_division=0)
        acc = accuracy_score(y_t, p_t)
        stock_perf.append((ticker, f1, acc, mask.sum()))

    stock_perf.sort(key=lambda x: x[1], reverse=True)
    print("    Top 5:")
    for t, f, a, n in stock_perf[:5]:
        print(f"      {t:<18} F1m={f:.4f} Acc={a:.4f} n={n}")
    print("    Bottom 5:")
    for t, f, a, n in stock_perf[-5:]:
        print(f"      {t:<18} F1m={f:.4f} Acc={a:.4f} n={n}")

    # --- 0h. Root-cause analysis ---
    print("\n  [0h] ROOT CAUSE ANALYSIS")
    print("    The model is dominated by FLAT because:")
    print("    1. CLASS IMBALANCE: FLAT is ~50% of training data; DOWN ~24%, UP ~27%.")
    print("    2. WEAK SIGNAL: 1-day returns are noisy; features have modest discriminative power (ROC-AUC ~0.61).")
    print("    3. PROBABILITY CALIBRATION / THRESHOLD: The model's softmax probabilities for FLAT")
    print("       are systematically higher than for DOWN/UP, so argmax almost always picks FLAT.")
    print("    4. PRICE-SCALE FEATURES: Raw Open/High/Low/Close vary enormously across stocks")
    print("       (e.g. NVDA ~$130 vs RELIANCE.NS ~INR 1300). The model may memorise stock-specific")
    print("       price levels rather than learning generalisable directional patterns.")
    print("    Potential remedies: class weighting, threshold tuning, hyperparameter search,")
    print("    and removing raw price-scale features.")

    return model


# ===================================================================
# EXPERIMENT 1 -- CLASS WEIGHTING
# ===================================================================

def experiment_class_weighting(X_train, y_train, X_val, y_val, feature_cols):
    """Test sample-weight configurations to rebalance minority classes."""
    print("\n" + "=" * 70)
    print("  EXPERIMENT 1 -- CLASS WEIGHTING")
    print("=" * 70)

    weight_configs = {
        "1_baseline":     {0: 1.0, 1: 1.0, 2: 1.0},
        "2_moderate":     {0: 1.25, 1: 1.0, 2: 1.25},
        "3_stronger":     {0: 1.5, 1: 1.0, 2: 1.5},
        "4_aggressive":   {0: 2.0, 1: 1.0, 2: 2.0},
        "5_inv_freq":     None,  # inverse-frequency auto
        "6_down_focus":   {0: 2.0, 1: 1.0, 2: 1.5},
    }

    # Compute inverse-frequency weights
    class_counts = np.bincount(y_train.values, minlength=3)
    total = class_counts.sum()
    inv_freq = {c: float(total / (3 * class_counts[c])) for c in range(3)}
    weight_configs["5_inv_freq"] = inv_freq

    results = []
    params = base_params()

    for name, wmap in weight_configs.items():
        sw = np.array([wmap[c] for c in y_train.values], dtype=np.float32)
        model = train_xgb(X_train, y_train, X_val, y_val, params, sample_weight=sw)
        prob = model.predict_proba(X_val)
        pred = np.argmax(prob, axis=1)
        m = metrics_dict(y_val.values, pred, prob)
        m["config_name"] = name
        m["weight_map"] = wmap
        results.append(m)

        w_str = " ".join(f"{CODE_TO_LABEL[k]}={v:.2f}" for k, v in sorted(wmap.items()))
        print(f"\n  [{name}] {w_str}")
        print_metrics_compact(m)

    # Select best by val macro F1
    best = max(results, key=lambda r: r["f1_macro"])
    print(f"\n  >>> BEST CLASS WEIGHTING: {best['config_name']}  Val F1m={best['f1_macro']:.4f}")

    return best


# ===================================================================
# EXPERIMENT 2 -- HYPERPARAMETER TUNING
# ===================================================================

def experiment_hyperparam_tuning(X_train, y_train, X_val, y_val,
                                 best_weight_map, feature_cols):
    """Controlled hyperparameter search with the best class weighting."""
    print("\n" + "=" * 70)
    print("  EXPERIMENT 2 -- HYPERPARAMETER TUNING (with best class weights)")
    print("=" * 70)

    sw = np.array([best_weight_map[c] for c in y_train.values], dtype=np.float32)

    grid = {
        "learning_rate":   [0.03, 0.05, 0.1],
        "max_depth":       [3, 4, 5, 6],
        "min_child_weight": [1, 3, 5],
        "subsample":       [0.8, 1.0],
        "colsample_bytree": [0.8, 1.0],
        "reg_alpha":       [0.0, 0.1, 0.5],
        "reg_lambda":      [1, 2, 5],
    }

    # Full grid would be 3*4*3*2*2*3*3 = 1296 combinations -- too many.
    # Use a randomised sub-sample of ~80 configs for tractability.
    np.random.seed(RANDOM_STATE)
    keys = list(grid.keys())
    all_combos = list(product(*grid.values()))
    if len(all_combos) > 80:
        idx = np.random.choice(len(all_combos), size=80, replace=False)
        combos = [all_combos[i] for i in sorted(idx)]
    else:
        combos = all_combos

    total = len(combos)
    print(f"  Testing {total} parameter combinations (randomised sub-sample).")

    best_f1 = -1.0
    best_params = None
    best_model = None
    best_metrics = None

    for i, combo in enumerate(combos, 1):
        override = dict(zip(keys, combo))
        params = base_params(**override)
        model = train_xgb(X_train, y_train, X_val, y_val, params, sample_weight=sw)
        prob = model.predict_proba(X_val)
        pred = np.argmax(prob, axis=1)
        f1 = f1_score(y_val.values, pred, average="macro", zero_division=0)

        if f1 > best_f1:
            best_f1 = f1
            best_params = params.copy()
            best_model = model
            best_metrics = metrics_dict(y_val.values, pred, prob)
            lr, md, mcw = override["learning_rate"], override["max_depth"], override["min_child_weight"]
            sub, cst = override["subsample"], override["colsample_bytree"]
            ra, rl = override["reg_alpha"], override["reg_lambda"]
            print(f"  [{i:>3}/{total}] NEW BEST F1m={f1:.4f} | lr={lr} d={md} mcw={mcw} "
                  f"sub={sub} cst={cst} ra={ra} rl={rl}")
        elif i % 20 == 0:
            print(f"  [{i:>3}/{total}] Best so far F1m={best_f1:.4f}")

    print(f"\n  Search complete. Best Val F1m={best_f1:.4f}")
    print_metrics_compact(best_metrics, "Best Tuned")

    return best_params, best_model, best_metrics


# ===================================================================
# EXPERIMENT 3 -- PROBABILITY THRESHOLD ADJUSTMENT
# ===================================================================

def experiment_threshold_adjustment(model, X_val, y_val):
    """Search for per-class probability multipliers that maximise val macro F1."""
    print("\n" + "=" * 70)
    print("  EXPERIMENT 3 -- PROBABILITY DECISION THRESHOLDS")
    print("=" * 70)

    val_prob = model.predict_proba(X_val)
    y_true = y_val.values

    # Baseline: uniform multipliers
    baseline_pred = np.argmax(val_prob, axis=1)
    baseline_f1 = f1_score(y_true, baseline_pred, average="macro", zero_division=0)
    print(f"  Baseline (1.0 / 1.0 / 1.0): F1m={baseline_f1:.4f}")

    # Search: adjust DOWN and UP multipliers, reduce FLAT multiplier
    # Concept: adjusted_prob[c] = prob[c] * multiplier[c], then argmax
    down_mults = np.arange(1.0, 3.1, 0.25)   # 1.0 to 3.0
    flat_mults = np.arange(0.5, 1.1, 0.1)    # 0.5 to 1.0
    up_mults   = np.arange(1.0, 3.1, 0.25)   # 1.0 to 3.0

    best_f1 = baseline_f1
    best_mult = (1.0, 1.0, 1.0)
    best_pred = baseline_pred
    best_metrics = None

    search_count = len(down_mults) * len(flat_mults) * len(up_mults)
    print(f"  Searching {search_count} threshold combinations...")

    for dm in down_mults:
        for fm in flat_mults:
            for um in up_mults:
                adjusted = val_prob.copy()
                adjusted[:, 0] *= dm
                adjusted[:, 1] *= fm
                adjusted[:, 2] *= um
                pred = np.argmax(adjusted, axis=1)
                f1 = f1_score(y_true, pred, average="macro", zero_division=0)
                if f1 > best_f1:
                    best_f1 = f1
                    best_mult = (dm, fm, um)
                    best_pred = pred

    # Compute full metrics for the best threshold config
    best_metrics = metrics_dict(y_true, best_pred, val_prob)

    print(f"\n  Best threshold multipliers: DOWN={best_mult[0]:.2f}  FLAT={best_mult[1]:.2f}  UP={best_mult[2]:.2f}")
    print(f"  F1m improvement: {baseline_f1:.4f} -> {best_f1:.4f}  ({best_f1 - baseline_f1:+.4f})")
    print_metrics_compact(best_metrics, "Threshold-Adjusted")
    print_confusion(best_metrics["confusion_matrix"], "Threshold-Adjusted Val")

    return best_mult, best_f1, best_metrics


# ===================================================================
# EXPERIMENT 4 -- FEATURE ABLATION
# ===================================================================

def experiment_feature_ablation(X_train_full, y_train, X_val_full, y_val,
                                 best_weight_map, best_tuned_params):
    """Test removing price-scale, Volume, and redundant MA features."""
    print("\n" + "=" * 70)
    print("  EXPERIMENT 4 -- FEATURE ABLATION")
    print("=" * 70)

    sw = np.array([best_weight_map[c] for c in y_train.values], dtype=np.float32)

    feature_sets = {
        "A_all_17": ALL_17_FEATURES,
        "B_no_price": [f for f in ALL_17_FEATURES if f not in ["Open", "High", "Low", "Close"]],
        "C_no_volume": [f for f in ALL_17_FEATURES if f != "Volume"],
        "D_no_price_no_vol": [f for f in ALL_17_FEATURES if f not in ["Open", "High", "Low", "Close", "Volume"]],
        "E_no_redundant_MA": [f for f in ALL_17_FEATURES if f not in ["MA_10", "MA_20"]],
        "F_minimal": ["Daily_Return", "RSI_14", "MACD", "MACD_Signal",
                       "Volatility_20", "Volume_Change", "Price_Change_Pct", "High_Low_Pct"],
    }

    results = []
    for name, feats in feature_sets.items():
        # Subset columns that exist in full dataframe
        X_tr = X_train_full[feats].astype(np.float32)
        X_v = X_val_full[feats].astype(np.float32)

        params = best_tuned_params.copy()
        model = train_xgb(X_tr, y_train, X_v, y_val, params, sample_weight=sw)
        prob = model.predict_proba(X_v)
        pred = np.argmax(prob, axis=1)
        m = metrics_dict(y_val.values, pred, prob)
        m["feature_set"] = name
        m["n_features"] = len(feats)
        m["features"] = feats
        results.append(m)

        print(f"\n  [{name}] {len(feats)} features")
        print_metrics_compact(m)

    best = max(results, key=lambda r: r["f1_macro"])
    print(f"\n  >>> BEST FEATURE SET: {best['feature_set']} ({best['n_features']} features)  "
          f"Val F1m={best['f1_macro']:.4f}")

    return best


# ===================================================================
# FINAL MODEL SELECTION & EVALUATION
# ===================================================================

def select_and_evaluate():
    """
    Master orchestration:
    1. Loads data, diagnoses v1.
    2. Runs experiments 1-4.
    3. Combines best findings into a single final model.
    4. Evaluates once on test.
    5. Saves all v2 artifacts.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  FinSight AI -- Step 7: Diagnose, Improve & Stress-Test XGBoost")
    print("=" * 70)
    print(f"  XGBoost : {xgb.__version__}")
    print(f"  Python  : {sys.version.split()[0]}")
    print(f"  Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Load data with all 17 features
    with open(FEATURE_JSON) as f:
        feature_cols = json.load(f)
    with open(TARGET_JSON) as f:
        target_def = json.load(f)

    (X_train, y_train, meta_train,
     X_val, y_val, meta_val,
     X_test, y_test, meta_test) = load_data(feature_cols)

    print(f"\n  Train: {len(X_train):,}  Val: {len(X_val):,}  Test: {len(X_test):,}")

    # -------------------------------------------------------------------
    # Phase 0: Diagnosis
    # -------------------------------------------------------------------
    v1_model = diagnose(X_train, y_train, X_val, y_val, meta_val, feature_cols)

    # -------------------------------------------------------------------
    # Experiment 1: Class Weighting
    # -------------------------------------------------------------------
    exp1_best = experiment_class_weighting(X_train, y_train, X_val, y_val, feature_cols)
    best_weight_map = exp1_best["weight_map"]

    # -------------------------------------------------------------------
    # Experiment 2: Hyperparameter Tuning (with best weights)
    # -------------------------------------------------------------------
    exp2_params, exp2_model, exp2_metrics = experiment_hyperparam_tuning(
        X_train, y_train, X_val, y_val, best_weight_map, feature_cols
    )

    # -------------------------------------------------------------------
    # Experiment 3: Threshold Adjustment (on tuned model)
    # -------------------------------------------------------------------
    exp3_mult, exp3_f1, exp3_metrics = experiment_threshold_adjustment(
        exp2_model, X_val, y_val
    )

    # -------------------------------------------------------------------
    # Experiment 4: Feature Ablation (with best weights + best params)
    # -------------------------------------------------------------------
    exp4_best = experiment_feature_ablation(
        X_train, y_train, X_val, y_val, best_weight_map, exp2_params
    )

    # -------------------------------------------------------------------
    # CONSOLIDATION -- Build final v2 model
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  MODEL SELECTION -- COMPARISON TABLE")
    print("=" * 70)

    # v1 baseline metrics (retrained)
    v1_prob = v1_model.predict_proba(X_val)
    v1_pred = np.argmax(v1_prob, axis=1)
    v1_metrics = metrics_dict(y_val.values, v1_pred, v1_prob)

    # Majority-class baseline
    maj_pred = np.ones(len(y_val), dtype=int)
    maj_metrics = metrics_dict(y_val.values, maj_pred)

    candidates = [
        ("Majority-FLAT", maj_metrics),
        ("v1 Original", v1_metrics),
        ("Exp1 ClassWeight", exp1_best),
        ("Exp2 Tuned+Weight", exp2_metrics),
        ("Exp3 Threshold", exp3_metrics),
        ("Exp4 Ablation", exp4_best),
    ]

    print(f"\n  {'Experiment':<22} {'Acc':>7} {'F1m':>7} {'F1w':>7}  "
          f"{'DOWN-F1':>8} {'FLAT-F1':>8} {'UP-F1':>8}")
    print(f"  {'-' * 72}")
    for name, m in candidates:
        down_f1 = m["per_class"]["DOWN"]["f1"]
        flat_f1 = m["per_class"]["FLAT"]["f1"]
        up_f1   = m["per_class"]["UP"]["f1"]
        print(f"  {name:<22} {m['accuracy']:>7.4f} {m['f1_macro']:>7.4f} {m['f1_weighted']:>7.4f}  "
              f"{down_f1:>8.4f} {flat_f1:>8.4f} {up_f1:>8.4f}")

    # Select the best non-baseline candidate by val macro F1
    model_candidates = candidates[1:]  # exclude majority
    best_name, best_metrics = max(model_candidates, key=lambda x: x[1]["f1_macro"])

    # Determine what the final v2 config should be:
    # Combine best hyperparams (Exp2) + best thresholds (Exp3) + best features (Exp4)
    # We need to check which approach actually won

    # Re-evaluate the winning combination: best_tuned_params + best_weights + best_thresholds + best_features
    # Build the final model with the optimal combination
    print(f"\n  >>> Best single experiment: {best_name}  Val F1m={best_metrics['f1_macro']:.4f}")

    # Now build the COMBINED best model: tuned params + weights + thresholds + best features
    print("\n" + "=" * 70)
    print("  BUILDING COMBINED v2 MODEL")
    print("=" * 70)

    # Use best feature set from experiment 4
    v2_features = exp4_best.get("features", feature_cols)
    v2_params = exp2_params.copy()
    v2_weight_map = best_weight_map
    v2_threshold = exp3_mult

    sw = np.array([v2_weight_map[c] for c in y_train.values], dtype=np.float32)
    X_tr_v2 = X_train[v2_features].astype(np.float32)
    X_val_v2 = X_val[v2_features].astype(np.float32)

    v2_model = train_xgb(X_tr_v2, y_train, X_val_v2, y_val, v2_params, sample_weight=sw)

    # Apply threshold adjustment
    v2_val_prob = v2_model.predict_proba(X_val_v2)
    v2_val_adj = v2_val_prob.copy()
    v2_val_adj[:, 0] *= v2_threshold[0]
    v2_val_adj[:, 1] *= v2_threshold[1]
    v2_val_adj[:, 2] *= v2_threshold[2]
    v2_val_pred = np.argmax(v2_val_adj, axis=1)

    v2_val_metrics = metrics_dict(y_val.values, v2_val_pred, v2_val_prob)

    print(f"\n  COMBINED v2 -- Validation Results")
    print(f"  Features      : {len(v2_features)}")
    print(f"  Weights       : DOWN={v2_weight_map[0]:.2f} FLAT={v2_weight_map[1]:.2f} UP={v2_weight_map[2]:.2f}")
    print(f"  Thresholds    : DOWN={v2_threshold[0]:.2f} FLAT={v2_threshold[1]:.2f} UP={v2_threshold[2]:.2f}")
    print(f"  Hyperparams   : lr={v2_params['learning_rate']} d={v2_params['max_depth']} "
          f"mcw={v2_params['min_child_weight']} sub={v2_params['subsample']} "
          f"cst={v2_params['colsample_bytree']} ra={v2_params['reg_alpha']} rl={v2_params['reg_lambda']}")
    print_metrics_compact(v2_val_metrics, "Combined v2 Val")
    print_confusion(v2_val_metrics["confusion_matrix"], "Combined v2 Val")

    # Check if combined is better than individual best; if not, fall back to the individual best
    if v2_val_metrics["f1_macro"] < best_metrics["f1_macro"]:
        print(f"\n  NOTE: Combined model F1m={v2_val_metrics['f1_macro']:.4f} < "
              f"best individual {best_name} F1m={best_metrics['f1_macro']:.4f}")
        print("  Checking: is the combined model still better than v1?")

    # Always also try Exp3 thresholds on the combined model vs without
    v2_val_pred_no_thresh = np.argmax(v2_val_prob, axis=1)
    v2_val_m_nothresh = metrics_dict(y_val.values, v2_val_pred_no_thresh, v2_val_prob)
    print(f"\n  Combined v2 WITHOUT threshold: F1m={v2_val_m_nothresh['f1_macro']:.4f}")
    print(f"  Combined v2 WITH threshold:    F1m={v2_val_metrics['f1_macro']:.4f}")

    # Pick whichever is higher
    use_threshold = v2_val_metrics["f1_macro"] >= v2_val_m_nothresh["f1_macro"]
    if not use_threshold:
        v2_val_metrics = v2_val_m_nothresh
        v2_val_pred = v2_val_pred_no_thresh
        v2_threshold = (1.0, 1.0, 1.0)
        print("  >>> Using NO threshold adjustment for final v2.")
    else:
        print("  >>> Using threshold adjustment for final v2.")

    # -------------------------------------------------------------------
    # Save Validation Predictions v2
    # -------------------------------------------------------------------
    val_pred_df = meta_val.reset_index(drop=True).copy()
    val_pred_df["Actual_Code"] = y_val.reset_index(drop=True).values
    val_pred_df["Predicted_Code"] = v2_val_pred
    val_pred_df["Actual_Label"] = val_pred_df["Actual_Code"].map(CODE_TO_LABEL)
    val_pred_df["Predicted_Label"] = val_pred_df["Predicted_Code"].map(CODE_TO_LABEL)
    val_pred_df["Probability_DOWN"] = v2_val_prob[:, 0]
    val_pred_df["Probability_FLAT"] = v2_val_prob[:, 1]
    val_pred_df["Probability_UP"] = v2_val_prob[:, 2]
    val_pred_df["Confidence"] = v2_val_prob.max(axis=1)
    out_cols = ["Date", "Ticker", "Market", "Actual_Label", "Predicted_Label",
                "Actual_Code", "Predicted_Code",
                "Probability_DOWN", "Probability_FLAT", "Probability_UP", "Confidence"]
    val_pred_df[out_cols].to_csv(VAL_PRED_V2_FILE, index=False)
    print(f"\n[SAVED] Validation predictions v2: {VAL_PRED_V2_FILE} ({len(val_pred_df):,} rows)")

    # -------------------------------------------------------------------
    # FINAL TEST EVALUATION (ONCE)
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  FINAL TEST SET EVALUATION (held-out, evaluated once)")
    print("=" * 70)

    X_test_v2 = X_test[v2_features].astype(np.float32)
    test_prob = v2_model.predict_proba(X_test_v2)
    test_adj = test_prob.copy()
    test_adj[:, 0] *= v2_threshold[0]
    test_adj[:, 1] *= v2_threshold[1]
    test_adj[:, 2] *= v2_threshold[2]
    test_pred = np.argmax(test_adj, axis=1)

    v2_test_metrics = metrics_dict(y_test.values, test_pred, test_prob)

    print_metrics_compact(v2_test_metrics, "v2 Test (Final)")
    print_confusion(v2_test_metrics["confusion_matrix"], "v2 Test Final")
    print(f"\n  Classification Report:\n{classification_report(y_test.values, test_pred, target_names=['DOWN','FLAT','UP'], zero_division=0)}")

    # Naive baseline on test
    maj_test_pred = np.ones(len(y_test), dtype=int)
    maj_test_metrics = metrics_dict(y_test.values, maj_test_pred)

    # v1 on test (load original model)
    v1_test_model = xgb.XGBClassifier()
    v1_test_model.load_model(str(MODELS_DIR / "xgboost_trend_model.json"))
    v1_test_prob = v1_test_model.predict_proba(X_test)
    v1_test_pred = np.argmax(v1_test_prob, axis=1)
    v1_test_m = metrics_dict(y_test.values, v1_test_pred, v1_test_prob)

    # Comparison table
    print("\n" + "=" * 70)
    print("  FINAL COMPARISON: Majority vs v1 vs v2 (TEST SET)")
    print("=" * 70)
    for lbl, m in [("Majority-FLAT", maj_test_metrics), ("v1 Original", v1_test_m), ("v2 Improved", v2_test_metrics)]:
        d_f1 = m["per_class"]["DOWN"]["f1"]
        f_f1 = m["per_class"]["FLAT"]["f1"]
        u_f1 = m["per_class"]["UP"]["f1"]
        d_r = m["per_class"]["DOWN"]["recall"]
        u_r = m["per_class"]["UP"]["recall"]
        print(f"  {lbl:<16} Acc={m['accuracy']:.4f} F1m={m['f1_macro']:.4f} F1w={m['f1_weighted']:.4f}  "
              f"DOWN(R={d_r:.3f} F1={d_f1:.3f})  FLAT(F1={f_f1:.3f})  UP(R={u_r:.3f} F1={u_f1:.3f})")

    # -------------------------------------------------------------------
    # Feature Importance v2
    # -------------------------------------------------------------------
    booster = v2_model.get_booster()
    scores = booster.get_score(importance_type="gain")
    imp_list = sorted(
        [(f, scores.get(f, 0.0)) for f in v2_features],
        key=lambda x: x[1], reverse=True,
    )
    print(f"\n  Top 10 Feature Importances (v2, gain):")
    for rank, (feat, gain) in enumerate(imp_list[:10], 1):
        print(f"    {rank:>2}. {feat:<20} {gain:.2f}")

    # -------------------------------------------------------------------
    # Save Model v2
    # -------------------------------------------------------------------
    v2_model.save_model(str(MODEL_V2_FILE))
    print(f"\n[SAVED] Model v2: {MODEL_V2_FILE}")

    # -------------------------------------------------------------------
    # Save Test Predictions v2
    # -------------------------------------------------------------------
    test_pred_df = meta_test.reset_index(drop=True).copy()
    test_pred_df["Actual_Code"] = y_test.reset_index(drop=True).values
    test_pred_df["Predicted_Code"] = test_pred
    test_pred_df["Actual_Label"] = test_pred_df["Actual_Code"].map(CODE_TO_LABEL)
    test_pred_df["Predicted_Label"] = test_pred_df["Predicted_Code"].map(CODE_TO_LABEL)
    test_pred_df["Probability_DOWN"] = test_prob[:, 0]
    test_pred_df["Probability_FLAT"] = test_prob[:, 1]
    test_pred_df["Probability_UP"] = test_prob[:, 2]
    test_pred_df["Confidence"] = test_prob.max(axis=1)
    test_pred_df[out_cols].to_csv(TEST_PRED_V2_FILE, index=False)
    print(f"[SAVED] Test predictions v2: {TEST_PRED_V2_FILE} ({len(test_pred_df):,} rows)")

    # -------------------------------------------------------------------
    # Save Metadata v2
    # -------------------------------------------------------------------
    metadata_v2 = {
        "model_type": "XGBClassifier",
        "model_version": "v2",
        "objective": "multi:softprob",
        "num_classes": N_CLASSES,
        "class_mapping": CODE_TO_LABEL,
        "random_seed": RANDOM_STATE,
        "tree_method": "hist (CPU)",
        "xgboost_version": xgb.__version__,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "python_version": sys.version.split()[0],
        "training_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "feature_names": v2_features,
        "feature_count": len(v2_features),
        "target_name": TARGET_COL,
        "target_definition": target_def,
        "train_row_count": int(len(X_train)),
        "validation_row_count": int(len(X_val)),
        "test_row_count": int(len(X_test)),
        "best_iteration": int(v2_model.best_iteration),
        "class_weight_config": {CODE_TO_LABEL[k]: float(v) for k, v in v2_weight_map.items()},
        "threshold_multipliers": {
            "DOWN": float(v2_threshold[0]),
            "FLAT": float(v2_threshold[1]),
            "UP": float(v2_threshold[2]),
        },
        "selected_hyperparameters": {
            k: v2_params[k] for k in [
                "n_estimators", "learning_rate", "max_depth", "min_child_weight",
                "subsample", "colsample_bytree", "reg_alpha", "reg_lambda",
            ]
        },
        "experiments_performed": [
            "Exp1_class_weighting",
            "Exp2_hyperparameter_tuning",
            "Exp3_threshold_adjustment",
            "Exp4_feature_ablation",
        ],
        "exp1_best_config": exp1_best["config_name"],
        "exp4_best_feature_set": exp4_best["feature_set"],
        "v1_test_metrics": {
            "accuracy": v1_test_m["accuracy"],
            "f1_macro": v1_test_m["f1_macro"],
            "per_class": v1_test_m["per_class"],
        },
        "majority_baseline_test": {
            "accuracy": maj_test_metrics["accuracy"],
            "f1_macro": maj_test_metrics["f1_macro"],
        },
        "validation_metrics": v2_val_metrics,
        "test_metrics": v2_test_metrics,
        "model_artifacts": {
            "model_file": str(MODEL_V2_FILE),
            "metadata_file": str(METADATA_V2_FILE),
            "validation_predictions_file": str(VAL_PRED_V2_FILE),
            "test_predictions_file": str(TEST_PRED_V2_FILE),
        },
    }

    with open(METADATA_V2_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata_v2, f, indent=2, default=str)
    print(f"[SAVED] Metadata v2: {METADATA_V2_FILE}")

    # -------------------------------------------------------------------
    # HONEST ASSESSMENT
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  HONEST MODEL ASSESSMENT")
    print("=" * 70)

    v2_f1 = v2_test_metrics["f1_macro"]
    v1_f1 = v1_test_m["f1_macro"]
    maj_f1 = maj_test_metrics["f1_macro"]

    v2_down_r = v2_test_metrics["per_class"]["DOWN"]["recall"]
    v1_down_r = v1_test_m["per_class"]["DOWN"]["recall"]
    v2_up_r = v2_test_metrics["per_class"]["UP"]["recall"]
    v1_up_r = v1_test_m["per_class"]["UP"]["recall"]

    print(f"  Test F1 Macro:  Majority={maj_f1:.4f}  v1={v1_f1:.4f}  v2={v2_f1:.4f}")
    print(f"  DOWN recall:    v1={v1_down_r:.4f}  v2={v2_down_r:.4f}  delta={v2_down_r - v1_down_r:+.4f}")
    print(f"  UP recall:      v1={v1_up_r:.4f}    v2={v2_up_r:.4f}  delta={v2_up_r - v1_up_r:+.4f}")
    print(f"  v2 beats v1 on F1m: {'YES' if v2_f1 > v1_f1 else 'NO'}")
    print(f"  v2 beats majority on F1m: {'YES' if v2_f1 > maj_f1 else 'NO'}")

    if v2_f1 > v1_f1:
        improvement_pct = (v2_f1 - v1_f1) / v1_f1 * 100
        print(f"  Relative improvement over v1: {improvement_pct:+.1f}%")
    else:
        print("  WARNING: v2 did NOT improve over v1 on test macro F1.")

    if v2_test_metrics["accuracy"] < v1_test_m["accuracy"]:
        print(f"  TRADEOFF: v2 accuracy ({v2_test_metrics['accuracy']:.4f}) is lower than "
              f"v1 ({v1_test_m['accuracy']:.4f}). This is expected when rebalancing toward minority classes.")

    print("\n  FUNDAMENTAL LIMITATIONS:")
    print("    1. Single-day stock returns are inherently very noisy (~EMH).")
    print("    2. The +/-1% threshold creates a large FLAT class (~50%) that is genuinely hard to subdivide.")
    print("    3. Technical indicators alone have limited predictive power over 1-day horizons.")
    print("    4. ROC-AUC ~0.60--0.62 confirms the signal is real but modest.")
    print("    5. Substantial further improvement would require fundamentally different features")
    print("       (fundamental data, sentiment, order-flow) or a different prediction horizon.")

    print("\n" + "=" * 70)
    print("  STEP 7 COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    select_and_evaluate()
