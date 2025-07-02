from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.compose import ColumnTransformer
from sklearn.feature_selection import RFECV, VarianceThreshold
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def run_experiment(
    features_fp: Path,
    target_fp: Path,
    y_col: str,
    is_classification: bool,
    sample_size: int = None,
    chunk_size: int = 100000,
):

    print(f"\n{'='*60}")
    print(f"FEATURE SELECTION EXPERIMENT")
    print(f"{'='*60}")
    print(f"Features file: {features_fp}")
    print(f"Target file: {target_fp}")
    print(f"Target column: {y_col}")
    print(f"Task type: {'Classification' if is_classification else 'Regression'}")
    print(f"Sample size: {sample_size if sample_size else 'Full dataset'}")

    # 0. load & align
    print(f"\n{'='*40}")
    print("LOADING DATA...")
    print(f"{'='*40}")

    if sample_size:
        print(f"Sampling {sample_size:,} rows for testing...")
        target_df = pl.read_parquet(target_fp)
        total_rows = len(target_df)
        print(f"Total rows in target: {total_rows:,}")

        random_indices = np.random.choice(
            total_rows, size=min(sample_size, total_rows), replace=False
        )
        random_indices = sorted(random_indices)  # Sort for efficient reading

        target_pandas = target_df.to_pandas()
        sampled_target = target_pandas.iloc[random_indices]

        features_df = pl.read_parquet(features_fp)
        features_pandas = features_df.to_pandas()
        sampled_features = features_pandas.iloc[random_indices]

        X = sampled_features
        y = sampled_target[y_col]
    else:
        X = pl.read_parquet(features_fp).to_pandas()
        y = pl.read_parquet(target_fp).to_pandas()[y_col]

    print(f"Final dataset shape: {X.shape}")
    print(f"Target shape: {y.shape}")

    # Print target statistics
    print(f"\nTARGET STATISTICS:")
    print(f"  Count: {len(y):,}")
    print(f"  Null values: {y.isnull().sum()}")

    if is_classification:
        print(f"  Class distribution:")
        for class_val, count in y.value_counts().items():
            print(f"    Class {class_val}: {count:,} ({count/len(y)*100:.2f}%)")

    # Print feature statistics
    print(f"\nFEATURE STATISTICS:")
    print(f"  Total features: {X.shape[1]}")
    print(f"  Features with nulls: {X.isnull().sum().sum()}")
    print(f"  Features with zero variance: {(X.var() == 0).sum()}")
    print(f"  Features with low variance (< 1e-6): {(X.var() < 1e-6).sum()}")

    # Clean data - remove rows with NaN values
    print(f"\n{'='*40}")
    print("CLEANING DATA...")
    print(f"{'='*40}")

    # Check for NaN values
    target_nulls = y.isnull().sum()
    feature_nulls = X.isnull().sum().sum()

    print(f"Target nulls: {target_nulls}")
    print(f"Feature nulls: {feature_nulls}")

    if target_nulls > 0 or feature_nulls > 0:
        valid_mask = ~(y.isnull() | X.isnull().any(axis=1))
        X = X[valid_mask]
        y = y[valid_mask]
        print(f"Removed {len(valid_mask) - valid_mask.sum()} rows with NaN values")
        print(f"Clean dataset shape: {X.shape}")
        print(f"Clean target shape: {y.shape}")
    else:
        print("No NaN values found - data is clean!")

    # 1. split - reduced folds to save memory
    print(f"\n{'='*40}")
    print("SETTING UP CROSS-VALIDATION...")
    print(f"{'='*40}")
    tscv = TimeSeriesSplit(n_splits=3)
    print(f"Time series cross-validation with {tscv.n_splits} folds")

    # 2. preprocessing + stage-0/1
    print(f"\n{'='*40}")
    print("SETTING UP PREPROCESSING PIPELINE...")
    print(f"{'='*40}")
    pre = Pipeline(
        [
            ("var", VarianceThreshold(0.0)),
            ("sc", StandardScaler()),
        ]
    )
    print("Pipeline: VarianceThreshold -> StandardScaler")

    # 3. model - memory optimized parameters
    print(f"\n{'='*40}")
    print("CONFIGURING LIGHTGBM MODEL...")
    print(f"{'='*40}")
    if is_classification:
        est = LGBMClassifier(
            objective="multiclass",
            num_class=3,
            num_leaves=31,
            max_depth=6,
            feature_fraction=0.8,
            bagging_fraction=0.8,
            bagging_freq=5,
            min_data_in_leaf=20,
            verbose=-1,
            n_jobs=1,
        )
    else:
        est = LGBMRegressor(
            objective="regression",
            num_leaves=31,
            max_depth=6,
            feature_fraction=0.8,
            bagging_fraction=0.8,
            bagging_freq=5,
            min_data_in_leaf=20,
            verbose=-1,
            n_jobs=1,
        )

    print(f"Model type: {type(est).__name__}")
    print(f"Parameters: num_leaves={est.num_leaves}, max_depth={est.max_depth}")
    print(
        f"Feature fraction: {est.feature_fraction}, Bagging fraction: {est.bagging_fraction}"
    )

    print(f"\n{'='*40}")
    print("SETTING UP FEATURE SELECTION...")
    print(f"{'='*40}")
    sel = RFECV(
        estimator=est,
        cv=tscv,
        scoring="roc_auc_ovr" if is_classification else "neg_mean_absolute_error",
        step=10,
        min_features_to_select=50,
    )

    print(
        f"Feature selection: RFECV with step={sel.step}, min_features={sel.min_features_to_select}"
    )
    print(f"Scoring metric: {sel.scoring}")

    pipe = Pipeline([("pre", pre), ("sel", sel), ("est", est)])

    print(f"\n{'='*40}")
    print("TRAINING MODEL AND ANALYZING FEATURES...")
    print(f"{'='*40}")

    print("Fitting pipeline...")
    pipe.fit(X, y)

    selected_features = X.columns[sel.support_].tolist()
    removed_features = X.columns[~sel.support_].tolist()

    print(f"\nFEATURE SELECTION RESULTS:")
    print(f"  Original features: {X.shape[1]}")
    print(f"  Selected features: {len(selected_features)}")
    print(f"  Removed features: {len(removed_features)}")
    print(f"  Reduction: {len(removed_features)/X.shape[1]*100:.1f}%")

    final_estimator = pipe.named_steps["est"]
    if hasattr(final_estimator, "feature_importances_"):
        feature_importance = final_estimator.feature_importances_
        feature_names = selected_features

        importance_df = pd.DataFrame(
            {"feature": feature_names, "importance": feature_importance}
        ).sort_values("importance", ascending=False)

        print(f"\nTOP 20 MOST IMPORTANT FEATURES:")
        print(f"{'='*50}")
        for i, (_, row) in enumerate(importance_df.head(20).iterrows()):
            print(f"{i+1:2d}. {row['feature']:<30} {row['importance']:.6f}")

        print(f"\nBOTTOM 20 LEAST IMPORTANT FEATURES:")
        print(f"{'='*50}")
        for i, (_, row) in enumerate(importance_df.tail(20).iterrows()):
            print(
                f"{len(importance_df)-19+i:2d}. {row['feature']:<30} {row['importance']:.6f}"
            )

        importance_file = f"feature_importance_{y_col}_{sample_size or 'full'}.csv"
        importance_df.to_csv(importance_file, index=False)
        print(f"\nFeature importance saved to: {importance_file}")

        removed_file = f"removed_features_{y_col}_{sample_size or 'full'}.txt"
        with open(removed_file, "w") as f:
            for feature in removed_features:
                f.write(f"{feature}\n")
        print(f"Removed features saved to: {removed_file}")

    print(f"\n{'='*40}")
    print("CROSS-VALIDATION RESULTS...")
    print(f"{'='*40}")
    cv_score = cross_val_score(
        pipe,
        X,
        y,
        cv=tscv,
        scoring=("roc_auc_ovr" if is_classification else "neg_mean_absolute_error"),
        n_jobs=1,
    )

    print(f"CV scores: {cv_score}")
    print(f"Mean CV score: {cv_score.mean():.6f}")
    print(f"CV score std: {cv_score.std():.6f}")

    print(f"\nRFECV DETAILS:")
    print(f"  Best number of features: {sel.n_features_}")
    print(f"  Grid scores: {sel.grid_scores_}")

    return pipe, selected_features, cv_score.mean()


features_fp = Path("data/signals/coinbase_btc_usdc_config_v1.parquet")
target_fp = Path("data/targets/coinbase_btc_usdc_config_y_v1_1_0.0007.parquet")


# run_experiment(
#     features_fp,
#     target_fp,
#     y_col="vwap_ret",
#     is_classification=False,
#     sample_size=500000,
# )

run_experiment(features_fp, target_fp, y_col="vwap_ret", is_classification=False)
