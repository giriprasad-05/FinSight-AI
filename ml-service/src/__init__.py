"""
FinSight AI - ML Service Package
This package provides modules for data fetching, feature engineering,
label creation, dataset preparation, model training, evaluation, and stock market inference using XGBoost.
"""

from .features import (
    calculate_rsi,
    calculate_features,
    clean_missing_values,
    validate_processed_data,
    process_stock_file,
    RAW_COLUMNS,
    FEATURE_COLUMNS as BASE_FEATURE_COLUMNS,
    FINAL_COLUMN_ORDER,
)

from .create_labels import (
    create_trend_labels,
    validate_labels,
    compute_class_distribution,
    process_labeled_file,
    LABEL_TO_CODE,
    CODE_TO_LABEL,
    FINAL_LABELED_COLUMNS,
)

from .prepare_dataset import (
    load_labeled_files,
    validate_stock_dataset,
    combine_datasets,
    create_time_based_split,
    validate_split_boundaries,
    check_feature_target_leakage,
    save_datasets,
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    TARGET_DEFINITION,
    EXPECTED_COLUMNS_ORDER,
)

__all__ = [
    "calculate_rsi",
    "calculate_features",
    "clean_missing_values",
    "validate_processed_data",
    "process_stock_file",
    "RAW_COLUMNS",
    "BASE_FEATURE_COLUMNS",
    "FINAL_COLUMN_ORDER",
    "create_trend_labels",
    "validate_labels",
    "compute_class_distribution",
    "process_labeled_file",
    "LABEL_TO_CODE",
    "CODE_TO_LABEL",
    "FINAL_LABELED_COLUMNS",
    "load_labeled_files",
    "validate_stock_dataset",
    "combine_datasets",
    "create_time_based_split",
    "validate_split_boundaries",
    "check_feature_target_leakage",
    "save_datasets",
    "FEATURE_COLUMNS",
    "TARGET_COLUMN",
    "TARGET_DEFINITION",
    "EXPECTED_COLUMNS_ORDER",
]
