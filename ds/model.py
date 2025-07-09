from typing import Dict, List

import numpy as np
import polars as pl
import xgboost as xgb
from sklearn.metrics import accuracy_score, f1_score, r2_score, roc_auc_score
from sklearn.preprocessing import LabelEncoder, StandardScaler

xgb_params_regression = {
    "n_estimators": 100,
    "max_depth": 6,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 0.1,
    "random_state": 42,
    "n_jobs": -1,
    "verbosity": 0,
    "objective": "reg:squarederror",
    "eval_metric": "rmse",
}
xgb_params_binary = {
    "n_estimators": 100,
    "max_depth": 6,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 0.1,
    "random_state": 42,
    "n_jobs": -1,
    "verbosity": 0,
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "use_label_encoder": False,
}
xgb_params_mutliclass = {
    "n_estimators": 100,
    "max_depth": 6,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 0.1,
    "random_state": 42,
    "n_jobs": -1,
    "verbosity": 0,
    "objective": "multi:softprob",
    "eval_metric": "mlogloss",
    "use_label_encoder": False,
}

single_xgb_params_binary = {
    "n_estimators": 50,
    "max_depth": 4,
    "learning_rate": 0.15,
    "random_state": 42,
    "n_jobs": 1,
    "verbosity": 0,
    "objective": "binary:logistic",
    "use_label_encoder": False,
}

single_xgb_params_regression = {
    "n_estimators": 50,
    "max_depth": 4,
    "learning_rate": 0.15,
    "random_state": 42,
    "n_jobs": 1,
    "verbosity": 0,
    "objective": "reg:squarederror",
}

single_xgb_params_mutliclass = {
    "n_estimators": 50,
    "max_depth": 4,
    "learning_rate": 0.15,
    "random_state": 42,
    "n_jobs": 1,
    "verbosity": 0,
    "objective": "multi:softprob",
    "use_label_encoder": False,
}


class CustomXGB:
    def __init__(
        self,
        train_data: pl.DataFrame,
        test_data: pl.DataFrame,
        feature_cols: List[str],
        target_col: str,
    ) -> None:
        self.task_type = None
        self.train_data = train_data
        self.test_data = test_data
        self.feature_cols = feature_cols
        self.target_col = target_col

    def _preprocess_y_for_task_type(
        self, y_train: np.ndarray, y_test: np.ndarray
    ) -> List[np.ndarray]:
        if len(np.unique(y_train)) == 2:
            self.task_type = "binary"
        elif len(np.unique(y_train)) > 2:
            self.task_type = "multiclass"
        else:
            self.task_type = "regression"

        if self.task_type == "binary":
            self.xgb_params = xgb_params_binary
            self.single_xgb_params = single_xgb_params_binary
            if not set(np.unique(y_train)).issubset({0, 1}):
                label_encoder = LabelEncoder()
                y_train = label_encoder.fit_transform(y_train)
                y_test = label_encoder.transform(y_test)
        elif self.task_type == "multiclass":
            self.xgb_params = xgb_params_mutliclass
            self.single_xgb_params = single_xgb_params_mutliclass
            self.xgb_params["num_class"] = len(
                np.unique(y_train)
            )  # dangerous.... but whatev
            self.single_xgb_params["num_class"] = len(np.unique(y_train))
            label_encoder = LabelEncoder()
            y_train = label_encoder.fit_transform(y_train)
            y_test = label_encoder.transform(y_test)
        else:
            self.xgb_params = xgb_params_regression
            self.single_xgb_params = single_xgb_params_regression
        return y_train, y_test

    def fit(self) -> None:
        X_train = self.train_data.select(self.feature_cols).to_numpy()
        y_train = self.train_data.select(self.target_col).to_numpy().ravel()
        X_test = self.test_data.select(self.feature_cols).to_numpy()
        y_test = self.test_data.select(self.target_col).to_numpy().ravel()

        X_train = np.nan_to_num(X_train)
        X_test = np.nan_to_num(X_test)
        y_train = np.nan_to_num(y_train)
        y_test = np.nan_to_num(y_test)

        y_train, y_test = self._preprocess_y_for_task_type(y_train, y_test)

        # scaling for the peace of mind
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        if self.task_type in ["binary", "multiclass"]:
            self.model = xgb.XGBClassifier(**self.xgb_params)
        else:
            self.model = xgb.XGBRegressor(**self.xgb_params)
        self.model.fit(
            X_train_scaled, y_train, eval_set=[(X_test_scaled, y_test)], verbose=False
        )
        feature_importance = dict(
            zip(self.feature_cols, self.model.feature_importances_)
        )
        feature_performance = {}

        for i, feature in enumerate(self.feature_cols):
            try:
                if self.task_type in ["binary", "multiclass"]:
                    single_xgb = xgb.XGBClassifier(**self.single_xgb_params)
                else:
                    single_xgb = xgb.XGBRegressor(**self.single_xgb_params)
                single_xgb.fit(X_train_scaled[:, i : i + 1], y_train, verbose=False)

                if self.task_type == "binary":
                    y_pred_proba = single_xgb.predict_proba(
                        X_test_scaled[:, i : i + 1]
                    )[:, 1]
                    y_pred = single_xgb.predict(X_test_scaled[:, i : i + 1])
                    try:
                        auc = roc_auc_score(y_test, y_pred_proba)
                    except ValueError:
                        print(f"Failed to calculate AUC for feature {feature}")
                        auc = 0.5
                    accuracy = accuracy_score(y_test, y_pred)
                    f1 = f1_score(y_test, y_pred)
                    primary_score = auc
                    r2 = None
                elif self.task_type == "multiclass":
                    y_pred = single_xgb.predict(X_test_scaled[:, i : i + 1])
                    accuracy = accuracy_score(y_test, y_pred)
                    f1 = f1_score(y_test, y_pred, average="weighted")
                    primary_score = f1
                    r2 = None
                    auc = None
                else:
                    y_pred = single_xgb.predict(X_test_scaled[:, i : i + 1])
                    r2 = r2_score(y_test, y_pred)
                    primary_score = r2
                    accuracy = None
                    auc = None
                    f1 = None
                feature_performance[feature] = {
                    "primary_score": primary_score,
                    "accuracy": accuracy,
                    "auc": auc,
                    "r2": r2,
                    "importance": feature_importance[feature],
                    "task_type": self.task_type,
                    "f1": f1,
                }
            except Exception as e:
                print(f"Failed to evaluate feature {feature}: {str(e)}")
                if self.task_type == "binary":
                    fallback_score = 0.5
                elif self.task_type == "multiclass":
                    fallback_score = 1.0 / len(np.unique(y_train))
                else:
                    fallback_score = 0.0

                feature_performance[feature] = {
                    "primary_score": fallback_score,
                    "r2_score": 0.0 if self.task_type == "regression" else None,
                    "auc_score": (0.5 if self.task_type == "binary" else None),
                    "accuracy": (
                        fallback_score
                        if self.task_type in ["binary", "multiclass"]
                        else None
                    ),
                    "f1_score": (
                        fallback_score
                        if self.task_type in ["binary", "multiclass"]
                        else None
                    ),
                    "importance": feature_importance.get(feature, 0.0),
                    "task_type": self.task_type,
                }
        return feature_performance
