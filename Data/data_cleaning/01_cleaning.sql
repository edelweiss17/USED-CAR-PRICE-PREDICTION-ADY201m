/* =====================================================================
   01_cleaning.sql  -  T02 Cleaning (phan SQL, chay trong SSMS)
   Dau vao : bang cars_raw (import tu cars.csv, 15.000 dong)
   Dau ra  : bang cars_clean
   SQL lam : bo trung list_id, bo dong thieu gia/nam sx, doi gia sang trieu,
             tinh tuoi xe, loc tin spam, tao co van ban, doi ma so sang chu,
             chuan hoa ten tinh, bo ODO = 0 / thieu, bo trung xe.
   Chay ca file bang F5 (nho chon database UsedCars).
   ===================================================================== */
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'UsedCars')
BEGIN
    CREATE DATABASE UsedCars;
END;
GO
USE UsedCars;
GO

/* ---------- BUOC 1: tao cars_clean ---------- */
DROP TABLE IF EXISTS cars_clean;

WITH dedup AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY list_id ORDER BY list_id) AS rn
    FROM cars_raw
),
base AS (
    SELECT
        list_id, subject,
        CAST(price AS FLOAT) / 1000000.0 AS price_million,
        TRY_CAST(mfdate AS INT) AS mfdate,
        CASE WHEN 2026 - TRY_CAST(mfdate AS INT) < 0 THEN 0
             ELSE 2026 - TRY_CAST(mfdate AS INT) END AS car_age,
        TRY_CAST(mileage_v2 AS FLOAT) AS odo_km,
        LTRIM(RTRIM(carbrand_name)) AS carbrand_name,
        LTRIM(RTRIM(carmodel_name)) AS carmodel_name,
        region_name_v3, area_name, ward_name, list_time,
        CASE
            WHEN region_name IS NULL THEN N'Không xác định'
            WHEN LTRIM(RTRIM(region_name)) LIKE N'Tp. %'       THEN LTRIM(SUBSTRING(LTRIM(RTRIM(region_name)), 5, 100))
            WHEN LTRIM(RTRIM(region_name)) LIKE N'Tp %'        THEN LTRIM(SUBSTRING(LTRIM(RTRIM(region_name)), 4, 100))
            WHEN LTRIM(RTRIM(region_name)) LIKE N'Thành phố %' THEN LTRIM(SUBSTRING(LTRIM(RTRIM(region_name)), 10, 100))
            WHEN LTRIM(RTRIM(region_name)) LIKE N'Tỉnh %'      THEN LTRIM(SUBSTRING(LTRIM(RTRIM(region_name)), 6, 100))
            ELSE LTRIM(RTRIM(region_name))
        END AS region_name,
        CASE WHEN subject LIKE N'%chính chủ%' OR subject LIKE N'%1 chủ%'
               OR subject LIKE N'%một chủ%' OR subject LIKE N'%gia đình%' THEN 1 ELSE 0 END AS flag_chinh_chu,
        CASE WHEN subject LIKE N'%bảo dưỡng hãng%' OR subject LIKE N'%lịch sử hãng%'
               OR subject LIKE N'%full lịch sử%' OR subject LIKE N'%bảo hành%' THEN 1 ELSE 0 END AS flag_bao_duong_hang,
        TRY_CAST(TRY_CAST(gearbox   AS FLOAT) AS INT) AS gearbox_code,
        TRY_CAST(TRY_CAST(fuel      AS FLOAT) AS INT) AS fuel_code,
        TRY_CAST(TRY_CAST(cartype   AS FLOAT) AS INT) AS cartype_code,
        TRY_CAST(TRY_CAST(carcolor  AS FLOAT) AS INT) AS carcolor_code,
        TRY_CAST(TRY_CAST(carorigin AS FLOAT) AS INT) AS carorigin_code,
        TRY_CAST(TRY_CAST(carseats  AS FLOAT) AS INT) AS carseats_code
    FROM dedup
    WHERE rn = 1
      AND price IS NOT NULL
      AND CAST(price AS FLOAT) >= 20000000
      AND TRY_CAST(mfdate AS INT) IS NOT NULL
      AND NOT (subject LIKE N'%cho thuê%' OR subject LIKE N'%thuê xe%' OR subject LIKE N'%tìm mua%'
            OR subject LIKE N'%cần mua%'  OR subject LIKE N'%thu mua%' OR subject LIKE N'%góp xe%'
            OR subject LIKE N'%đặt cọc%')
)
SELECT
    list_id, subject, price_million, mfdate, car_age, odo_km,
    carbrand_name, carmodel_name, region_name, region_name_v3, area_name, ward_name, list_time,
    flag_chinh_chu, flag_bao_duong_hang,
    CASE gearbox_code WHEN 1 THEN N'Số tự động' WHEN 2 THEN N'Số sàn' WHEN 3 THEN N'Bán tự động' ELSE N'Unknown' END AS gearbox,
    CASE fuel_code WHEN 1 THEN N'Xăng' WHEN 2 THEN N'Dầu' WHEN 3 THEN N'Hybrid' WHEN 4 THEN N'Điện' ELSE N'Unknown' END AS fuel,
    CASE cartype_code WHEN 1 THEN N'Sedan' WHEN 2 THEN N'Coupe' WHEN 3 THEN N'SUV / Crossover' WHEN 4 THEN N'Hatchback'
         WHEN 5 THEN N'Minibus / Xe chuyên dụng' WHEN 6 THEN N'Bán tải' WHEN 7 THEN N'Mui trần'
         WHEN 8 THEN N'MPV' WHEN 9 THEN N'Van / Minivan' ELSE N'Unknown' END AS cartype,
    CASE carcolor_code WHEN 1 THEN N'Đen' WHEN 2 THEN N'Trắng' WHEN 3 THEN N'Bạc' WHEN 4 THEN N'Xám' WHEN 5 THEN N'Đỏ'
         WHEN 6 THEN N'Xanh dương' WHEN 7 THEN N'Vàng' WHEN 8 THEN N'Cam' WHEN 9 THEN N'Nâu'
         WHEN 10 THEN N'Xanh lá' WHEN 11 THEN N'Hồng' WHEN 12 THEN N'Màu khác' ELSE N'Unknown' END AS carcolor,
    CASE carorigin_code WHEN 1 THEN N'Lắp ráp trong nước' WHEN 2 THEN N'Nhập khẩu Ấn Độ' WHEN 3 THEN N'Nhập khẩu Hàn Quốc'
         WHEN 4 THEN N'Nhập khẩu Thái Lan' WHEN 5 THEN N'Nhập khẩu Nhật Bản' WHEN 6 THEN N'Nhập khẩu Trung Quốc'
         WHEN 7 THEN N'Nhập khẩu Indonesia' WHEN 8 THEN N'Nhập khẩu Mỹ' WHEN 9 THEN N'Nhập khẩu Đức'
         WHEN 10 THEN N'Nhập khẩu Đài Loan' ELSE N'Unknown' END AS carorigin,
    /* carseats: chi gan nhan cho ma da doi chieu voi tieu de tin (1,2,3). Ma khac giu dang 'Ma n' */
    CASE WHEN carseats_code IS NULL THEN N'Unknown'
         WHEN carseats_code = 1 THEN N'4 chỗ'
         WHEN carseats_code = 2 THEN N'5 chỗ'
         WHEN carseats_code = 3 THEN N'7 chỗ'
         ELSE N'Mã ' + CAST(carseats_code AS NVARCHAR(10)) END AS carseats
INTO cars_clean
FROM base;

/* ---------- BUOC 2: chuan hoa ten tinh ---------- */
UPDATE cars_clean
SET region_name = CASE region_name
    WHEN N'Hcm' THEN N'Hồ Chí Minh'
    WHEN N'Hn' THEN N'Hà Nội'
    WHEN N'Bria - Vũng Tàu' THEN N'Bà Rịa - Vũng Tàu'
    WHEN N'Thừa Thiên Huế' THEN N'Thừa Thiên - Huế'
    ELSE region_name END;

/* ---------- BUOC 3: bo ODO = 0 hoac thieu (khong dien, tranh nhieu du lieu) ---------- */
DELETE FROM cars_clean WHERE odo_km IS NULL OR odo_km = 0;

/* ---------- BUOC 4: bo trung xe: cung hang, dong, nam, ODO, tinh, gia -> giu tin moi nhat ---------- */
DECLARE @truoc INT = (SELECT COUNT(*) FROM cars_clean);

WITH d AS (
    SELECT ROW_NUMBER() OVER (
               PARTITION BY carbrand_name, carmodel_name, mfdate, odo_km, region_name, price_million
               ORDER BY list_id DESC) AS rn
    FROM cars_clean
)
DELETE FROM d WHERE rn > 1;

DECLARE @sau INT = (SELECT COUNT(*) FROM cars_clean);
PRINT N'Truoc khi bo trung xe: ' + CAST(@truoc AS NVARCHAR(20))
    + N' | Sau: ' + CAST(@sau AS NVARCHAR(20))
    + N' | Da xoa: ' + CAST(@truoc - @sau AS NVARCHAR(20));

/* ---------- BUOC 5: kiem tra ---------- */
SELECT COUNT(*) AS so_dong, MIN(odo_km) AS odo_min, MIN(price_million) AS gia_min,
       MAX(price_million) AS gia_max, MAX(car_age) AS tuoi_max
FROM cars_clean;
SELECT carseats, COUNT(*) AS n FROM cars_clean GROUP BY carseats ORDER BY n DESC;
SELECT gearbox, COUNT(*) AS n FROM cars_clean GROUP BY gearbox;
SELECT region_name, COUNT(*) AS n FROM cars_clean GROUP BY region_name ORDER BY n DESC;
