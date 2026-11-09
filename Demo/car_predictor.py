import os
import re
import json
import warnings
import joblib
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore", category=UserWarning)

class CarPricePredictor:
    def __init__(self, model_path, preprocessor_path, feature_names_path=None, current_year=2026):
        self.current_year = current_year
        self.model = joblib.load(model_path)
        self.preprocessor = joblib.load(preprocessor_path)
        
        self.feature_names = None
        if feature_names_path and os.path.exists(feature_names_path):
            with open(feature_names_path, "r", encoding="utf-8") as f:
                self.feature_names = json.load(f)
                
        cat_transformer = self.preprocessor.named_transformers_["cat"]
        self.known_brands = set(cat_transformer.categories_[0])
        self.known_models = set(cat_transformer.categories_[1])
        self.known_regions = set(cat_transformer.categories_[2])

    def _extract_text_flags(self, text):
        if not text:
            return 0, 0
        clean_text = str(text).lower()
        pat_chinh_chu = r"ch[ií]nh\s*ch[uủ]|1\s*ch[uủ]|m[oộ]t\s*ch[uủ]|gia\s*[dđ][iì]nh|9\s*ch[uủ]"
        pat_zin = r"\bzin\b|nguy[eê]n\s*zin|bao\s*zin|s[oơ]n\s*zin|m[aá]y\s*zin|keo\s*ch[iỉ]\s*zin|c[oò]n\s*zin"
        
        flag_chinh_chu = 1 if re.search(pat_chinh_chu, clean_text) else 0
        flag_zin = 1 if re.search(pat_zin, clean_text) else 0
        return flag_chinh_chu, flag_zin

    def prepare_features(self, car_input):
        year = car_input.get("mfdate")
        if year is not None:
            car_age = max(0, self.current_year - int(year))
        else:
            car_age = max(0, int(car_input.get("car_age", 1)))

        odo_km = float(car_input.get("odo_km", 0.0))
        km_per_year = round(odo_km / max(car_age, 1), 1)

        raw_brand = str(car_input.get("carbrand_name", car_input.get("carbrand_grouped", "Khác")))
        brand_grouped = raw_brand if raw_brand in self.known_brands else "Khác"

        raw_model = str(car_input.get("carmodel_name", car_input.get("carmodel_grouped", "Khác")))
        model_grouped = raw_model if raw_model in self.known_models else "Khác"

        raw_region = str(car_input.get("region_name", car_input.get("region_grouped", "Khác")))
        region_grouped = raw_region if raw_region in self.known_regions else "Khác"

        subject = car_input.get("subject", "")
        extracted_chinh_chu, extracted_zin = self._extract_text_flags(subject)

        flag_chinh_chu = int(car_input.get("flag_chinh_chu", extracted_chinh_chu))
        flag_zin = int(car_input.get("flag_zin", extracted_zin))
        flag_bao_duong_hang = int(car_input.get("flag_bao_duong_hang", 0))

        row = {
            "carbrand_grouped": brand_grouped,
            "carmodel_grouped": model_grouped,
            "region_grouped": region_grouped,
            "gearbox": str(car_input.get("gearbox", "Số tự động")),
            "fuel": str(car_input.get("fuel", "Xăng")),
            "cartype": str(car_input.get("cartype", "Sedan")),
            "carorigin": str(car_input.get("carorigin", "Lắp ráp trong nước")),
            "car_age": float(car_age),
            "odo_km": odo_km,
            "km_per_year": float(km_per_year),
            "flag_chinh_chu": flag_chinh_chu,
            "flag_zin": flag_zin,
            "flag_bao_duong_hang": flag_bao_duong_hang
        }
        return pd.DataFrame([row])

    def predict(self, car_input):
        df_row = self.prepare_features(car_input)
        matrix = self.preprocessor.transform(df_row)
        
        if self.feature_names:
            matrix = pd.DataFrame(matrix, columns=self.feature_names)
            
        pred_value = float(self.model.predict(matrix)[0])
        pred_price = max(10.0, round(pred_value, 1))

        return {
            "predicted_price_million": pred_price,
            "predicted_price_vnd": f"{int(pred_price * 1_000_000):,} VND".replace(",", "."),
            "features_used": df_row.iloc[0].to_dict()
        }

