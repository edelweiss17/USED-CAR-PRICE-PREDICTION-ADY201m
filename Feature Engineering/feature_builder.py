import re
import pandas as pd


def extract_flag_chinh_chu(subject_series: pd.Series) -> pd.Series:
    pattern = r'ch[ií]nh\s*ch[uủ]|1\s*ch[uủ]|m[oộ]t\s*ch[uủ]|gia\s*[dđ][iì]nh|9\s*ch[uủ]'
    cleaned = subject_series.fillna('').astype(str).str.lower()
    return cleaned.str.contains(pattern, regex=True).astype(int)


def extract_flag_zin(subject_series: pd.Series) -> pd.Series:
    pattern = r'\bzin\b|nguy[eê]n\s*zin|bao\s*zin|s[oơ]n\s*zin|m[aá]y\s*zin|keo\s*ch[iỉ]\s*zin|c[oò]n\s*zin'
    cleaned = subject_series.fillna('').astype(str).str.lower()
    return cleaned.str.contains(pattern, regex=True).astype(int)


def calculate_usage_metrics(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    car_age_clipped = result['car_age'].clip(lower=1)
    result['km_per_year'] = (result['odo_km'] / car_age_clipped).round(1)
    return result


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data['flag_chinh_chu'] = extract_flag_chinh_chu(data['subject'])
    data['flag_zin'] = extract_flag_zin(data['subject'])
    data = calculate_usage_metrics(data)
    return data
