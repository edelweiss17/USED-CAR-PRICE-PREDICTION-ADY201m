import os
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, RobustScaler, StandardScaler


def group_low_frequency_categories(
    series: pd.Series,
    min_count: int = 50,
    other_label: str = 'Khác'
) -> pd.Series:
    counts = series.value_counts()
    valid_categories = counts[counts >= min_count].index
    return series.apply(lambda val: val if val in valid_categories else other_label)


def group_top_n_categories(
    series: pd.Series,
    top_n: int = 10,
    other_label: str = 'Khác'
) -> pd.Series:
    top_categories = series.value_counts().head(top_n).index
    return series.apply(lambda val: val if val in top_categories else other_label)


def build_column_transformer(
    categorical_cols: list,
    numerical_cols: list,
    binary_cols: list,
    scaler_type: str = 'standard'
) -> ColumnTransformer:
    if scaler_type == 'robust':
        scaler = RobustScaler()
    else:
        scaler = StandardScaler()

    encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)

    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', encoder, categorical_cols),
            ('num', scaler, numerical_cols),
            ('bin', 'passthrough', binary_cols)
        ]
    )
    return preprocessor


def fit_transform_features(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    preprocessor: ColumnTransformer
):
    preprocessor.fit(X_train)
    train_transformed = preprocessor.transform(X_train)
    test_transformed = preprocessor.transform(X_test)

    feature_names = preprocessor.get_feature_names_out()
    clean_feature_names = [name.replace('cat__', '').replace('num__', '').replace('bin__', '') for name in feature_names]

    X_train_df = pd.DataFrame(train_transformed, columns=clean_feature_names, index=X_train.index)
    X_test_df = pd.DataFrame(test_transformed, columns=clean_feature_names, index=X_test.index)

    return X_train_df, X_test_df, preprocessor


def save_artifacts(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    preprocessor: ColumnTransformer,
    output_dir: str
):
    os.makedirs(output_dir, exist_ok=True)
    X_train.to_csv(os.path.join(output_dir, 'X_train.csv'), index=False)
    X_test.to_csv(os.path.join(output_dir, 'X_test.csv'), index=False)
    y_train.to_csv(os.path.join(output_dir, 'y_train.csv'), index=False)
    y_test.to_csv(os.path.join(output_dir, 'y_test.csv'), index=False)
    joblib.dump(preprocessor, os.path.join(output_dir, 'preprocessor.joblib'))
