# """One model + one make_crud_router() call per table.

# To add a simple table:
#   1. DESC the table (or read the column dump) - note pk + writable columns + their EXACT case.
#   2. Add a Pydantic model with the writable columns (lowercase field names = JSON keys).
#   3. Add a make_crud_router(...) call below and append the result to `crud_routers`.

# Casing rule: pk and audit names are passed EXACTLY as stored (UPPERCASE for the
# upper-named FA_ tables). For fields, the column defaults to FIELD.upper(); list any
# column whose stored name isn't that (lowercase/mixed-case, or a rename) in
# column_overrides with its exact spelling.
# """
# from pydantic import BaseModel, Field

# from app.crud.factory import make_crud_router, Audit


# # ----- FA_KALA : goods (standard uppercase table) -----
# class KalaInput(BaseModel):
#     name_kala: str = Field(min_length=1)
#     unite: str | None = None


# # ----- FA_ANBAR : warehouses (rename responsible -> NAME_MASOL) -----
# class AnbarInput(BaseModel):
#     name_anbar: str = Field(min_length=1)
#     address: str | None = None
#     responsible: str | None = None
#     phone: str | None = None


# # ----- FA_PRODUCT_OWNER : cargo owners (NO audit / soft-delete columns) -----
# class OwnerInput(BaseModel):
#     name: str | None = None
#     family: str | None = None
#     national_code: str | None = None
#     type: str | None = None
#     address: str | None = None
#     mobile_force: str | None = None
#     mobile: str | None = None


# # ----- FA_SYS_TERM_CATEGORIES : coding categories (prefixed audit column names) -----
# class TermCategoryInput(BaseModel):
#     key: str | None = None
#     title: str | None = None
#     parent_id: int | None = None
#     status: str | None = None
#     language: str | None = None


# # ----- fa_kala_price : storage price rows (lowercase table, mixed-case cols, FK id_kala) -----
# class KalaPriceInput(BaseModel):
#     id_kala: int | None = None            # FK -> FA_KALA (plain number for now)
#     goods_group: str | None = None        # گروه کالا (Table 1 row label, unit embedded)
#     storage_price: float | None = None    # انبارداری (Table 1 storage rate)
#     price_30_day: float | None = None
#     price_60_day: float | None = None
#     price_90_day: float | None = None
#     price_unloding: float | None = None   # تخلیه و بارگیری (Table 1 handling rate)
#     description: str | None = None
#     code: str = Field(min_length=1)       # CODE is NOT NULL in the DB
#     is_dangerous: str | None = None

# # ----- FA_REPRESENTATIVE_COMPANY : representative companies (standard) -----
# class CompanyInput(BaseModel):
#     company: str | None = None
#     name: str | None = None
#     family: str | None = None
#     national_code: str | None = None
#     mobile: str | None = None
#     address: str | None = None


# # ----- FA_TAGH_ANBAR : racks (standard + FK id_anbar) -----
# class TaghInput(BaseModel):
#     name_tagh: str = Field(min_length=1)
#     id_anbar: int | None = None
#     description: str | None = None


# # ----- FA_SYS_TERMS : coding terms (prefixed audit, like categories) -----
# class TermInput(BaseModel):
#     category_id: int | None = None
#     key: str | None = None
#     value: str | None = None
#     parent_id: int | None = None
#     status: str | None = None
#     order_no: int | None = None
#     description: str | None = None


# # ----- fa_kala_dangerous : dangerous-goods rates (numeric prices, no id_kala) -----
# class KalaDangerousInput(BaseModel):
#     code: str | None = None
#     title: str | None = None
#     storage_price: float | None = None    # انبارداری (Table storage rate)
#     price_30_day: float | None = None
#     price_60_day: float | None = None
#     price_90_day: float | None = None
#     price_unloding: float | None = None   # تخلیه و بارگیری (Table handling rate)
#     description: str | None = None


# # ----- fa_kala_diamound : demand rates (string prices; renamed columns) -----
# class KalaDiamoundInput(BaseModel):
#     code: str | None = None
#     title: str | None = None
#     price_gher_edari: str | None = None
#     price_holiday: str | None = None
#     description: str | None = None


# # ----- fa_kala_other_service : other-service rates (string price) -----
# class KalaOtherServiceInput(BaseModel):
#     code: str | None = None
#     title: str | None = None
#     price: str | None = None
#     description: str | None = None


# # ----- fa_kala_strip : strip/stuffing rates (normal/non-standard/dangerous strings) -----
# class KalaStripInput(BaseModel):
#     code: str | None = None
#     title: str | None = None
#     normal: str | None = None
#     non_standard: str | None = None
#     dangerous: str | None = None
#     description: str | None = None


# # ----- fa_kala_time_stop_vehicle : night-stop rates (string price) -----
# class KalaTimeStopInput(BaseModel):
#     code: str | None = None
#     title: str | None = None
#     price: str | None = None
#     description: str | None = None


# # ----- fa_kala_vehicle_enter_price : entry/yard fee (string price) -----
# class KalaVehicleEnterInput(BaseModel):
#     code: str | None = None
#     title: str | None = None
#     price: str | None = None
#     description: str | None = None


# # ----- FA_TALI_HEADER : tally shipment header -----
# # BLOB (UPLOAD_DOCUMENT) and CLOB (DESCRIPTION) are deferred to a later pass —
# # they don't serialize to JSON via SELECT *, so they're excluded from this model.
# class TaliHeaderInput(BaseModel):
#     number_karaneh: str | None = None       # شماره کارنه / ترانزیت
#     radef_marze: int | None = None          # ردیف مرزی
#     date_enter_marze: str | None = None     # تاریخ ورود به مرز (ISO date string)
#     date_unloading: str | None = None       # تاریخ تخلیه (ISO date string)
#     id_marze: int | None = None             # نام مرز ورودی → terms cat 1
#     id_company: int | None = None           # نام شرکت حمل → companies
#     id_respons_company: int | None = None   # نام نماینده شرکت حمل → companies
#     id_product_ownear: int | None = None    # صاحب کالا → owners (note: DB spelling)
#     id_country: int | None = None           # مبدا حمل (کشور) → terms cat 2
#     number_bimeh: str | None = None         # شماره بیمه نامه
#     tali_number: int | None = None          # شماره تالی
#     number_ghabz: int | None = None         # قبض الکترونیک
#     name_arzyab: str | None = None          # نام ارزیاب
#     number_barnameh: str | None = None      # شماره بارنامه
#     is_bimeh: str | None = None             # آیا بیمه دارد؟ (بله/خیر)
#     name_anbardar: str | None = None        # نام انبار دار
#     accepted_gomrok: str | None = None      # تایید گمرک
#     company_bimeh: str | None = None        # شرکت بیمه گر

# # ----- FA_TALI_DETAILES : tally goods-lines (master-detail under a header) -----
# class TaliDetailInput(BaseModel):
#     id_headers_tali: int                      # link to FA_TALI_HEADER.ID_TALI (required)
#     id_anbar: int | None = None               # انبار → FA_ANBAR
#     id_tagh_anbar: int | None = None          # طاق → FA_TAGH_ANBAR
#     number_ghabze_anbar: int | None = None    # قبض انبار
#     code_groupe_kala: int = Field(...)        # کد گروه کالا (NOT NULL)
#     description_kala: str | None = None       # شرح کالا
#     hscode: str | None = None                 # Hscode
#     type_bastem: str | None = None            # نوع بسته‌بندی
#     number_kala: int = Field(...)             # تعداد (NOT NULL)
#     weighte: float = Field(...)               # وزن (NOT NULL)
#     type_number_kantiner: str | None = None   # نوع و شماره حامل
#     number_ghabze_bskol: int | None = None    # ش قبض باسکول
#     weighte_baskol: float = Field(...)        # وزن باسکول (NOT NULL)
#     number_hamel: str | None = None           # شماره حامل
#     zarib_mahal: float | None = None          # ضریب محل
#     container_type: str | None = None         # نوع کانتینر
#     container_number: str | None = None       # شماره کانتینر

# # ----- fa_tali_kala_diamound : demand-rate junction (tally ↔ diamound catalog) -----
# class TaliKalaDiamoundInput(BaseModel):
#     tali_id: int
#     kala_diamound_id: int | None = None
#     code: str | None = None
#     description: str | None = None

# # ----- fa_tali_kala_price -----
# class TaliKalaPriceInput(BaseModel):
#     tali_id: int
#     kala_price_id: int | None = None
#     code: str | None = None
#     description: str | None = None

# # ----- fa_tali_kala_dangerous -----
# class TaliKalaDangerousInput(BaseModel):
#     tali_id: int
#     kala_dangerous_id: int | None = None
#     code: str | None = None
#     description: str | None = None

# # ----- fa_tali_kala_other_service (has a count) -----
# class TaliKalaOtherServiceInput(BaseModel):
#     tali_id: int
#     kala_other_service_id: int | None = None
#     code: str | None = None
#     number_service: int | None = None
#     description: str | None = None

# # ----- fa_tali_kala_strip -----
# class TaliKalaStripInput(BaseModel):
#     tali_id: int
#     kala_strip_id: int | None = None
#     code: str | None = None
#     pricing_type: str | None = None   # normal | non_standard | dangerous (which rate column to bill)
#     description: str | None = None

# # ----- fa_tali_kala_time_stop_vehicle -----
# class TaliKalaTimeStopInput(BaseModel):
#     tali_id: int
#     kala_time_stop_vehicle_id: int | None = None
#     code: str | None = None
#     description: str | None = None

# # ----- fa_tali_kala_vehicle_enter_price -----
# class TaliKalaVehicleEnterInput(BaseModel):
#     tali_id: int
#     kala_vehicle_enter_price_id: int | None = None
#     code: str | None = None
#     description: str | None = None


# # ----- fa_ghabz_anbar_header : warehouse receipt header (BLOB/CLOB deferred) -----
# class GhabzHeaderInput(BaseModel):
#     number_ghabz: int | None = None
#     number_ghabz_uniqe: int | None = None
#     number_karaneh: str | None = None
#     number_tali: int | None = None
#     number_royea: str | None = None
#     number_kantiner: int | None = None
#     number_mantaghe_azad: int | None = None
#     date_unloading: str | None = None
#     number_mojavez_uuloading: int | None = None
#     id_marze: int | None = None
#     number_marze: int | None = None
#     date_enter_marze: str | None = None
#     id_country: int | None = None
#     weight: str | None = None
#     number_sanad: str | None = None
#     date_sanad: str | None = None
#     number_pigiri_anbar: int | None = None
#     status_bimeh: str | None = None
#     number_bimeh: str | None = None
#     id_company_bimeh: int | None = None
#     id_anbar: int | None = None
#     id_tagh_anbara: int | None = None
#     id_anbar_response: int | None = None
#     id_company: int | None = None
#     id_product_ownear: int | None = None
#     asnad_rasmi: str | None = None
#     name_anbardar: str | None = None
#     name_maneger: str | None = None
#     company_bimeh: str | None = None
#     tali_id: int | None = None


# # ----- FA_ghabz_anbar_DETAILES : receipt line items -----
# class GhabzDetailInput(BaseModel):
#     id_ghabz_anbar_headar: int
#     code_kala: int = Field(...)
#     code_kala_kantiner: int | None = None
#     description_kala: str | None = None
#     type_basteh: str | None = None
#     number_kala: int = Field(...)
#     number_kantiner: int | None = None
#     weighte_asnad: float = Field(...)
#     weighte_baskol: float = Field(...)
#     number_hamel: str | None = None
#     id_tagh_anbar: int | None = None
    
# crud_routers = [
#     make_crud_router(
#         prefix="/items", table="FA_KALA", pk="ID_KALA",
#         model=KalaInput, tag="kala", not_found="کالا یافت نشد",
#     ),
#     make_crud_router(
#         prefix="/anbar", table="FA_ANBAR", pk="ID_ANBAR",
#         model=AnbarInput, tag="anbar", not_found="انبار یافت نشد",
#         column_overrides={"responsible": "NAME_MASOL"},
#         order_by="SORT_ORDER",            # explicit display order, not the pk
#     ),
#     make_crud_router(
#         prefix="/owners", table="FA_PRODUCT_OWNER", pk="ID_OWNER",
#         model=OwnerInput, tag="owners", not_found="مالک یافت نشد",
#         audit=None,                       # this table has no audit/soft-delete columns
#     ),
#     make_crud_router(
#         prefix="/term-categories", table="FA_SYS_TERM_CATEGORIES", pk="SYS_TERM_CATEGORY_ID",
#         model=TermCategoryInput, tag="term_categories", not_found="دسته یافت نشد",
#         column_overrides={
#             "key": "SYS_TERM_CATEGORY_KEY",
#             "title": "SYS_TERM_CATEGORY_TITLE",
#             "parent_id": "SYS_TERM_CATEGORY_PARENT_ID",
#             "status": "SYS_TERM_CATEGORY_STATUS",
#             # language -> LANGUAGE (already FIELD.upper(), no override needed)
#         },
#         audit=Audit(
#             is_deleted="SYS_TERM_CATEGORY_IS_DELETED",
#             create_at="SYS_TERM_CATEGORY_CREATED_AT",
#             create_by="SYS_TERM_CATEGORY_CREATED_BY",
#             modify_at="SYS_TERM_CATEGORY_MODIFIED_AT",
#             modify_by="SYS_TERM_CATEGORY_MODIFIED_BY",
#         ),
#     ),
#     make_crud_router(
#         prefix="/kala-price", table="fa_kala_price", pk="id_kala_price",
#         model=KalaPriceInput, tag="kala_price", not_found="ردیف قیمت یافت نشد",
#         column_overrides={
#             # columns the original devs stored lowercase -> quote them exactly as-is
#             "id_kala": "id_kala",
#             "goods_group": "goods_group",
#             "storage_price": "storage_price",
#             "price_30_day": "price_30_day",
#             "price_60_day": "price_60_day",
#             "price_90_day": "price_90_day",
#             "price_unloding": "price_unloding",
#             # code/description/is_dangerous are UPPERCASE in the DB -> default handles them
#         },
#     ),
#     make_crud_router(
#         prefix="/companies", table="FA_REPRESENTATIVE_COMPANY", pk="ID_REPRE_COMPANY",
#         model=CompanyInput, tag="companies", not_found="شرکت یافت نشد",
#     ),
#     make_crud_router(
#         prefix="/tagh", table="FA_TAGH_ANBAR", pk="ID_TAGH",
#         model=TaghInput, tag="tagh", not_found="طاق یافت نشد",
#     ),
#     make_crud_router(
#         prefix="/terms", table="FA_SYS_TERMS", pk="SYS_TERM_ID",
#         model=TermInput, tag="terms", not_found="ترم یافت نشد",
#         column_overrides={
#             "category_id": "SYS_TERM_CATEGORY_ID",
#             "key": "SYS_TERM_KEY",
#             "value": "SYS_TERM_VALUE",
#             "parent_id": "SYS_TERM_PARENT_ID",
#             "status": "SYS_TERM_STATUS",
#             "order_no": "SYS_TERM_ORDER",
#             "description": "SYS_TERM_DESCRIPTION",
#         },
#         audit=Audit(
#             is_deleted="SYS_TERM_IS_DELETED",
#             create_at="SYS_TERM_CREATED_AT",
#             create_by="SYS_TERM_CREATED_BY",
#             modify_at="SYS_TERM_MODIFIED_AT",
#             modify_by="SYS_TERM_MODIFIED_BY",
#         ),
#     ),
#     make_crud_router(
#         prefix="/kala-dangerous", table="fa_kala_dangerous", pk="id_kala_dangerous",
#         model=KalaDangerousInput, tag="kala_dangerous", not_found="ردیف یافت نشد",
#         column_overrides={
#             "code": "code",
#             "storage_price": "storage_price",
#             "price_30_day": "price_30_day", "price_60_day": "price_60_day",
#             "price_90_day": "price_90_day", "price_unloding": "price_unloding",
#         },
#     ),
#     make_crud_router(
#         prefix="/kala-diamound", table="fa_kala_diamound", pk="id_kala_diamound",
#         model=KalaDiamoundInput, tag="kala_diamound", not_found="ردیف یافت نشد",
#         column_overrides={
#             "code": "code", "title": "title",
#             "price_gher_edari": "price_gher_edari", "price_holiday": "price_holiday",
#         },
#     ),
#     make_crud_router(
#         prefix="/kala-other-service", table="fa_kala_other_service", pk="id_kala_other_service",
#         model=KalaOtherServiceInput, tag="kala_other_service", not_found="ردیف یافت نشد",
#         column_overrides={"code": "code", "title": "title", "price": "price"},
#     ),
#     make_crud_router(
#         prefix="/kala-strip", table="fa_kala_strip", pk="id_kala_strip",
#         model=KalaStripInput, tag="kala_strip", not_found="ردیف یافت نشد",
#         column_overrides={
#             "code": "code", "title": "title", "normal": "normal",
#             "non_standard": "non_standard", "dangerous": "dangerous",
#         },
#     ),
#     make_crud_router(
#         prefix="/kala-time-stop", table="fa_kala_time_stop_vehicle", pk="id_kala_time_stop_vehicle",
#         model=KalaTimeStopInput, tag="kala_time_stop", not_found="ردیف یافت نشد",
#         column_overrides={"code": "code", "title": "title", "price": "price"},
#     ),
#     make_crud_router(
#         prefix="/kala-vehicle-enter", table="fa_kala_vehicle_enter_price", pk="id_kala_vehicle_enter_price",
#         model=KalaVehicleEnterInput, tag="kala_vehicle_enter", not_found="ردیف یافت نشد",
#         column_overrides={"code": "code", "title": "title", "price": "price"},
#     ),
#     make_crud_router(
#         prefix="/tally-header", table="FA_TALI_HEADER", pk="ID_TALI",
#         model=TaliHeaderInput, tag="tally_header", not_found="تالی یافت نشد",
#     ),
#     make_crud_router(
#         prefix="/tally-details", table="FA_TALI_DETAILES", pk="ID_TALI_DETAILS",
#         model=TaliDetailInput, tag="tally_details", not_found="ردیف تالی یافت نشد",
#     ),
#     make_crud_router(
#         prefix="/tali-kala-diamound", table="fa_tali_kala_diamound", pk="id_tali_kala_diamound",
#         model=TaliKalaDiamoundInput, tag="tali_kala_diamound", not_found="ردیف دیماند یافت نشد",
#         column_overrides={
#             "tali_id": "tali_id",
#             "kala_diamound_id": "kala_diamound_id",
#             "code": "code",
#         },
#     ),

#     make_crud_router(
#         prefix="/tali-kala-price", table="fa_tali_kala_price", pk="id_tali_kala_price",
#         model=TaliKalaPriceInput, tag="tali_kala_price", not_found="ردیف قیمت یافت نشد",
#         column_overrides={"tali_id": "tali_id", "kala_price_id": "kala_price_id", "code": "code"},
#     ),
#     make_crud_router(
#         prefix="/tali-kala-dangerous", table="fa_tali_kala_dangerous", pk="id_tali_kala_dangerous",
#         model=TaliKalaDangerousInput, tag="tali_kala_dangerous", not_found="ردیف خطرناک یافت نشد",
#         column_overrides={"tali_id": "tali_id", "kala_dangerous_id": "kala_dangerous_id", "code": "code"},
#     ),
#     make_crud_router(
#         prefix="/tali-kala-other-service", table="fa_tali_kala_other_service", pk="id_tali_kala_other_service",
#         model=TaliKalaOtherServiceInput, tag="tali_kala_other_service", not_found="ردیف خدمات یافت نشد",
#         column_overrides={
#             "tali_id": "tali_id", "kala_other_service_id": "kala_other_service_id", "code": "code",
#             "number_service": "NUMBER_SERVICE",
#         },
#     ),
#     make_crud_router(
#         prefix="/tali-kala-strip", table="fa_tali_kala_strip", pk="id_tali_kala_strip",
#         model=TaliKalaStripInput, tag="tali_kala_strip", not_found="ردیف استریپ یافت نشد",
#         column_overrides={
#             "tali_id": "tali_id", "kala_strip_id": "kala_strip_id",
#             "code": "code", "pricing_type": "pricing_type",
#         },
#     ),
#     make_crud_router(
#         prefix="/tali-kala-time-stop", table="fa_tali_kala_time_stop_vehicle", pk="id_tali_kala_time_stop_vehicle",
#         model=TaliKalaTimeStopInput, tag="tali_kala_time_stop", not_found="ردیف توقف شبانه یافت نشد",
#         column_overrides={"tali_id": "tali_id", "kala_time_stop_vehicle_id": "kala_time_stop_vehicle_id", "code": "code"},
#     ),
#     make_crud_router(
#         prefix="/tali-kala-vehicle-enter", table="fa_tali_kala_vehicle_enter_price", pk="id_tali_kala_vehicle_enter_price",
#         model=TaliKalaVehicleEnterInput, tag="tali_kala_vehicle_enter", not_found="ردیف ورود خودرو یافت نشد",
#         column_overrides={"tali_id": "tali_id", "kala_vehicle_enter_price_id": "kala_vehicle_enter_price_id", "code": "code"},
#     ),
#     make_crud_router(
#         prefix="/ghabz-header", table="fa_ghabz_anbar_header", pk="ID_ghabz",
#         model=GhabzHeaderInput, tag="ghabz_header", not_found="قبض یافت نشد",
#         column_overrides={
#             "number_ghabz": "number_ghabz", "number_ghabz_uniqe": "number_ghabz_uniqe",
#             "number_tali": "NUMBER_tali", "number_royea": "number_royea",
#             "number_kantiner": "number_kantiner", "number_mantaghe_azad": "number_mantaghe_azad",
#             "number_mojavez_uuloading": "number_mojavez_uuloading", "number_marze": "number_MARZE",
#             "weight": "weight", "number_sanad": "number_sanad", "date_sanad": "date_sanad",
#             "number_pigiri_anbar": "number_pigiri_anbar", "status_bimeh": "status_BIMEH",
#             "id_company_bimeh": "ID_COMPANY_bimeh", "id_anbar": "ID_anbar",
#             "id_tagh_anbara": "ID_tagh_anbara", "id_anbar_response": "ID_anbar_response",
#             "asnad_rasmi": "asnad_rasmi", "name_maneger": "NAME_maneger",
#         },
#     ),
#     make_crud_router(
#         prefix="/ghabz-details", table="FA_ghabz_anbar_DETAILES", pk="ID_ghabz_anbar_DETAILS",
#         model=GhabzDetailInput, tag="ghabz_details", not_found="ردیف قبض یافت نشد",
#         column_overrides={
#             "code_kala": "code_kala", "code_kala_kantiner": "code_kala_kantiner",
#             "type_basteh": "TYPE_BASTEh", "number_kantiner": "NUMBER_KAntiner",
#             "weighte_asnad": "WEIGHTE_asnad",
#         },
#     ),
# ]

# """One model + one make_crud_router() call per table.

# To add a simple table:
#   1. DESC the table (or read the column dump) - note pk + writable columns + their EXACT case.
#   2. Add a Pydantic model with the writable columns (lowercase field names = JSON keys).
#   3. Add a make_crud_router(...) call below and append the result to `crud_routers`.

# Casing rule: pk and audit names are passed EXACTLY as stored (UPPERCASE for the
# upper-named FA_ tables). For fields, the column defaults to FIELD.upper(); list any
# column whose stored name isn't that (lowercase/mixed-case, or a rename) in
# column_overrides with its exact spelling.
# """
# from pydantic import BaseModel, Field

# from app.crud.factory import make_crud_router, Audit


# # ----- FA_KALA : goods (standard uppercase table) -----
# class KalaInput(BaseModel):
#     name_kala: str = Field(min_length=1)
#     unite: str | None = None


# # ----- FA_ANBAR : warehouses (rename responsible -> NAME_MASOL) -----
# class AnbarInput(BaseModel):
#     name_anbar: str = Field(min_length=1)
#     address: str | None = None
#     responsible: str | None = None
#     phone: str | None = None


# # ----- FA_PRODUCT_OWNER : cargo owners (NO audit / soft-delete columns) -----
# class OwnerInput(BaseModel):
#     name: str | None = None
#     family: str | None = None
#     national_code: str | None = None
#     type: str | None = None
#     address: str | None = None
#     mobile_force: str | None = None
#     mobile: str | None = None


# # ----- FA_SYS_TERM_CATEGORIES : coding categories (prefixed audit column names) -----
# class TermCategoryInput(BaseModel):
#     key: str | None = None
#     title: str | None = None
#     parent_id: int | None = None
#     status: str | None = None
#     language: str | None = None


# # ----- fa_kala_price : storage price rows (lowercase table, mixed-case cols, FK id_kala) -----
# class KalaPriceInput(BaseModel):
#     id_kala: int | None = None            # FK -> FA_KALA (plain number for now)
#     goods_group: str | None = None        # گروه کالا (Table 1 row label, unit embedded)
#     storage_price: float | None = None    # انبارداری (Table 1 storage rate)
#     price_30_day: float | None = None
#     price_60_day: float | None = None
#     price_90_day: float | None = None
#     price_unloding: float | None = None   # تخلیه و بارگیری (Table 1 handling rate)
#     description: str | None = None
#     code: str = Field(min_length=1)       # CODE is NOT NULL in the DB
#     is_dangerous: str | None = None

# # ----- FA_REPRESENTATIVE_COMPANY : representative companies (standard) -----
# class CompanyInput(BaseModel):
#     company: str | None = None
#     name: str | None = None
#     family: str | None = None
#     national_code: str | None = None
#     mobile: str | None = None
#     address: str | None = None


# # ----- FA_TAGH_ANBAR : racks (standard + FK id_anbar) -----
# class TaghInput(BaseModel):
#     name_tagh: str = Field(min_length=1)
#     id_anbar: int | None = None
#     description: str | None = None


# # ----- FA_SYS_TERMS : coding terms (prefixed audit, like categories) -----
# class TermInput(BaseModel):
#     category_id: int | None = None
#     key: str | None = None
#     value: str | None = None
#     parent_id: int | None = None
#     status: str | None = None
#     order_no: int | None = None
#     description: str | None = None


# # ----- fa_kala_dangerous : dangerous-goods rates (numeric prices, no id_kala) -----
# class KalaDangerousInput(BaseModel):
#     code: str | None = None
#     title: str | None = None
#     price_30_day: float | None = None
#     price_60_day: float | None = None
#     price_90_day: float | None = None
#     price_unloding: float | None = None
#     description: str | None = None


# # ----- fa_kala_diamound : demand rates (string prices; renamed columns) -----
# class KalaDiamoundInput(BaseModel):
#     code: str | None = None
#     title: str | None = None
#     price_gher_edari: str | None = None
#     price_holiday: str | None = None
#     description: str | None = None


# # ----- fa_kala_other_service : other-service rates (string price) -----
# class KalaOtherServiceInput(BaseModel):
#     code: str | None = None
#     title: str | None = None
#     price: str | None = None
#     description: str | None = None


# # ----- fa_kala_strip : strip/stuffing rates (normal/non-standard/dangerous strings) -----
# class KalaStripInput(BaseModel):
#     code: str | None = None
#     title: str | None = None
#     normal: str | None = None
#     non_standard: str | None = None
#     dangerous: str | None = None
#     description: str | None = None


# # ----- fa_kala_time_stop_vehicle : night-stop rates (string price) -----
# class KalaTimeStopInput(BaseModel):
#     code: str | None = None
#     title: str | None = None
#     price: str | None = None
#     description: str | None = None


# # ----- fa_kala_vehicle_enter_price : entry/yard fee (string price) -----
# class KalaVehicleEnterInput(BaseModel):
#     code: str | None = None
#     title: str | None = None
#     price: str | None = None
#     description: str | None = None


# # ----- FA_TALI_HEADER : tally shipment header -----
# # BLOB (UPLOAD_DOCUMENT) and CLOB (DESCRIPTION) are deferred to a later pass —
# # they don't serialize to JSON via SELECT *, so they're excluded from this model.
# class TaliHeaderInput(BaseModel):
#     number_karaneh: str | None = None       # شماره کارنه / ترانزیت
#     radef_marze: int | None = None          # ردیف مرزی
#     date_enter_marze: str | None = None     # تاریخ ورود به مرز (ISO date string)
#     date_unloading: str | None = None       # تاریخ تخلیه (ISO date string)
#     id_marze: int | None = None             # نام مرز ورودی → terms cat 1
#     id_company: int | None = None           # نام شرکت حمل → companies
#     id_respons_company: int | None = None   # نام نماینده شرکت حمل → companies
#     id_product_ownear: int | None = None    # صاحب کالا → owners (note: DB spelling)
#     id_country: int | None = None           # مبدا حمل (کشور) → terms cat 2
#     number_bimeh: str | None = None         # شماره بیمه نامه
#     tali_number: int | None = None          # شماره تالی
#     number_ghabz: int | None = None         # قبض الکترونیک
#     name_arzyab: str | None = None          # نام ارزیاب
#     number_barnameh: str | None = None      # شماره بارنامه
#     is_bimeh: str | None = None             # آیا بیمه دارد؟ (بله/خیر)
#     name_anbardar: str | None = None        # نام انبار دار
#     accepted_gomrok: str | None = None      # تایید گمرک
#     company_bimeh: str | None = None        # شرکت بیمه گر

# # ----- FA_TALI_DETAILES : tally goods-lines (master-detail under a header) -----
# class TaliDetailInput(BaseModel):
#     id_headers_tali: int                      # link to FA_TALI_HEADER.ID_TALI (required)
#     id_anbar: int | None = None               # انبار → FA_ANBAR
#     id_tagh_anbar: int | None = None          # طاق → FA_TAGH_ANBAR
#     number_ghabze_anbar: int | None = None    # قبض انبار
#     code_groupe_kala: int = Field(...)        # کد گروه کالا (NOT NULL)
#     description_kala: str | None = None       # شرح کالا
#     hscode: str | None = None                 # Hscode
#     type_bastem: str | None = None            # نوع بسته‌بندی
#     number_kala: int = Field(...)             # تعداد (NOT NULL)
#     weighte: float = Field(...)               # وزن (NOT NULL)
#     type_number_kantiner: str | None = None   # نوع و شماره حامل
#     number_ghabze_bskol: int | None = None    # ش قبض باسکول
#     weighte_baskol: float = Field(...)        # وزن باسکول (NOT NULL)
#     number_hamel: str | None = None           # شماره حامل
#     zarib_mahal: float | None = None          # ضریب محل
#     container_type: str | None = None         # نوع کانتینر
#     container_number: str | None = None       # شماره کانتینر

# # ----- fa_tali_kala_diamound : demand-rate junction (tally ↔ diamound catalog) -----
# class TaliKalaDiamoundInput(BaseModel):
#     tali_id: int
#     kala_diamound_id: int | None = None
#     code: str | None = None
#     description: str | None = None

# # ----- fa_tali_kala_price -----
# class TaliKalaPriceInput(BaseModel):
#     tali_id: int
#     kala_price_id: int | None = None
#     code: str | None = None
#     description: str | None = None

# # ----- fa_tali_kala_dangerous -----
# class TaliKalaDangerousInput(BaseModel):
#     tali_id: int
#     kala_dangerous_id: int | None = None
#     code: str | None = None
#     description: str | None = None

# # ----- fa_tali_kala_other_service (has a count) -----
# class TaliKalaOtherServiceInput(BaseModel):
#     tali_id: int
#     kala_other_service_id: int | None = None
#     code: str | None = None
#     number_service: int | None = None
#     description: str | None = None

# # ----- fa_tali_kala_strip -----
# class TaliKalaStripInput(BaseModel):
#     tali_id: int
#     kala_strip_id: int | None = None
#     code: str | None = None
#     pricing_type: str | None = None   # normal | non_standard | dangerous (which rate column to bill)
#     description: str | None = None

# # ----- fa_tali_kala_time_stop_vehicle -----
# class TaliKalaTimeStopInput(BaseModel):
#     tali_id: int
#     kala_time_stop_vehicle_id: int | None = None
#     code: str | None = None
#     description: str | None = None

# # ----- fa_tali_kala_vehicle_enter_price -----
# class TaliKalaVehicleEnterInput(BaseModel):
#     tali_id: int
#     kala_vehicle_enter_price_id: int | None = None
#     code: str | None = None
#     description: str | None = None


# # ----- fa_ghabz_anbar_header : warehouse receipt header (BLOB/CLOB deferred) -----
# class GhabzHeaderInput(BaseModel):
#     number_ghabz: int | None = None
#     number_ghabz_uniqe: int | None = None
#     number_karaneh: str | None = None
#     number_tali: int | None = None
#     number_royea: str | None = None
#     number_kantiner: int | None = None
#     number_mantaghe_azad: int | None = None
#     date_unloading: str | None = None
#     number_mojavez_uuloading: int | None = None
#     id_marze: int | None = None
#     number_marze: int | None = None
#     date_enter_marze: str | None = None
#     id_country: int | None = None
#     weight: str | None = None
#     number_sanad: str | None = None
#     date_sanad: str | None = None
#     number_pigiri_anbar: int | None = None
#     status_bimeh: str | None = None
#     number_bimeh: str | None = None
#     id_company_bimeh: int | None = None
#     id_anbar: int | None = None
#     id_tagh_anbara: int | None = None
#     id_anbar_response: int | None = None
#     id_company: int | None = None
#     id_product_ownear: int | None = None
#     asnad_rasmi: str | None = None
#     name_anbardar: str | None = None
#     name_maneger: str | None = None
#     company_bimeh: str | None = None
#     tali_id: int | None = None


# # ----- FA_ghabz_anbar_DETAILES : receipt line items -----
# class GhabzDetailInput(BaseModel):
#     id_ghabz_anbar_headar: int
#     code_kala: int = Field(...)
#     code_kala_kantiner: int | None = None
#     description_kala: str | None = None
#     type_basteh: str | None = None
#     number_kala: int = Field(...)
#     number_kantiner: int | None = None
#     weighte_asnad: float = Field(...)
#     weighte_baskol: float = Field(...)
#     number_hamel: str | None = None
#     id_tagh_anbar: int | None = None
    
# crud_routers = [
#     make_crud_router(
#         prefix="/items", table="FA_KALA", pk="ID_KALA",
#         model=KalaInput, tag="kala", not_found="کالا یافت نشد",
#     ),
#     make_crud_router(
#         prefix="/anbar", table="FA_ANBAR", pk="ID_ANBAR",
#         model=AnbarInput, tag="anbar", not_found="انبار یافت نشد",
#         column_overrides={"responsible": "NAME_MASOL"},
#         order_by="SORT_ORDER",            # explicit display order, not the pk
#     ),
#     make_crud_router(
#         prefix="/owners", table="FA_PRODUCT_OWNER", pk="ID_OWNER",
#         model=OwnerInput, tag="owners", not_found="مالک یافت نشد",
#         audit=None,                       # this table has no audit/soft-delete columns
#     ),
#     make_crud_router(
#         prefix="/term-categories", table="FA_SYS_TERM_CATEGORIES", pk="SYS_TERM_CATEGORY_ID",
#         model=TermCategoryInput, tag="term_categories", not_found="دسته یافت نشد",
#         column_overrides={
#             "key": "SYS_TERM_CATEGORY_KEY",
#             "title": "SYS_TERM_CATEGORY_TITLE",
#             "parent_id": "SYS_TERM_CATEGORY_PARENT_ID",
#             "status": "SYS_TERM_CATEGORY_STATUS",
#             # language -> LANGUAGE (already FIELD.upper(), no override needed)
#         },
#         audit=Audit(
#             is_deleted="SYS_TERM_CATEGORY_IS_DELETED",
#             create_at="SYS_TERM_CATEGORY_CREATED_AT",
#             create_by="SYS_TERM_CATEGORY_CREATED_BY",
#             modify_at="SYS_TERM_CATEGORY_MODIFIED_AT",
#             modify_by="SYS_TERM_CATEGORY_MODIFIED_BY",
#         ),
#     ),
#     make_crud_router(
#         prefix="/kala-price", table="fa_kala_price", pk="id_kala_price",
#         model=KalaPriceInput, tag="kala_price", not_found="ردیف قیمت یافت نشد",
#         column_overrides={
#             # columns the original devs stored lowercase -> quote them exactly as-is
#             "id_kala": "id_kala",
#             "goods_group": "goods_group",
#             "storage_price": "storage_price",
#             "price_30_day": "price_30_day",
#             "price_60_day": "price_60_day",
#             "price_90_day": "price_90_day",
#             "price_unloding": "price_unloding",
#             # code/description/is_dangerous are UPPERCASE in the DB -> default handles them
#         },
#     ),
#     make_crud_router(
#         prefix="/companies", table="FA_REPRESENTATIVE_COMPANY", pk="ID_REPRE_COMPANY",
#         model=CompanyInput, tag="companies", not_found="شرکت یافت نشد",
#     ),
#     make_crud_router(
#         prefix="/tagh", table="FA_TAGH_ANBAR", pk="ID_TAGH",
#         model=TaghInput, tag="tagh", not_found="طاق یافت نشد",
#     ),
#     make_crud_router(
#         prefix="/terms", table="FA_SYS_TERMS", pk="SYS_TERM_ID",
#         model=TermInput, tag="terms", not_found="ترم یافت نشد",
#         column_overrides={
#             "category_id": "SYS_TERM_CATEGORY_ID",
#             "key": "SYS_TERM_KEY",
#             "value": "SYS_TERM_VALUE",
#             "parent_id": "SYS_TERM_PARENT_ID",
#             "status": "SYS_TERM_STATUS",
#             "order_no": "SYS_TERM_ORDER",
#             "description": "SYS_TERM_DESCRIPTION",
#         },
#         audit=Audit(
#             is_deleted="SYS_TERM_IS_DELETED",
#             create_at="SYS_TERM_CREATED_AT",
#             create_by="SYS_TERM_CREATED_BY",
#             modify_at="SYS_TERM_MODIFIED_AT",
#             modify_by="SYS_TERM_MODIFIED_BY",
#         ),
#     ),
#     make_crud_router(
#         prefix="/kala-dangerous", table="fa_kala_dangerous", pk="id_kala_dangerous",
#         model=KalaDangerousInput, tag="kala_dangerous", not_found="ردیف یافت نشد",
#         column_overrides={
#             "code": "code",
#             "price_30_day": "price_30_day", "price_60_day": "price_60_day",
#             "price_90_day": "price_90_day", "price_unloding": "price_unloding",
#         },
#     ),
#     make_crud_router(
#         prefix="/kala-diamound", table="fa_kala_diamound", pk="id_kala_diamound",
#         model=KalaDiamoundInput, tag="kala_diamound", not_found="ردیف یافت نشد",
#         column_overrides={
#             "code": "code", "title": "title",
#             "price_gher_edari": "price_gher_edari", "price_holiday": "price_holiday",
#         },
#     ),
#     make_crud_router(
#         prefix="/kala-other-service", table="fa_kala_other_service", pk="id_kala_other_service",
#         model=KalaOtherServiceInput, tag="kala_other_service", not_found="ردیف یافت نشد",
#         column_overrides={"code": "code", "title": "title", "price": "price"},
#     ),
#     make_crud_router(
#         prefix="/kala-strip", table="fa_kala_strip", pk="id_kala_strip",
#         model=KalaStripInput, tag="kala_strip", not_found="ردیف یافت نشد",
#         column_overrides={
#             "code": "code", "title": "title", "normal": "normal",
#             "non_standard": "non_standard", "dangerous": "dangerous",
#         },
#     ),
#     make_crud_router(
#         prefix="/kala-time-stop", table="fa_kala_time_stop_vehicle", pk="id_kala_time_stop_vehicle",
#         model=KalaTimeStopInput, tag="kala_time_stop", not_found="ردیف یافت نشد",
#         column_overrides={"code": "code", "title": "title", "price": "price"},
#     ),
#     make_crud_router(
#         prefix="/kala-vehicle-enter", table="fa_kala_vehicle_enter_price", pk="id_kala_vehicle_enter_price",
#         model=KalaVehicleEnterInput, tag="kala_vehicle_enter", not_found="ردیف یافت نشد",
#         column_overrides={"code": "code", "title": "title", "price": "price"},
#     ),
#     make_crud_router(
#         prefix="/tally-header", table="FA_TALI_HEADER", pk="ID_TALI",
#         model=TaliHeaderInput, tag="tally_header", not_found="تالی یافت نشد",
#     ),
#     make_crud_router(
#         prefix="/tally-details", table="FA_TALI_DETAILES", pk="ID_TALI_DETAILS",
#         model=TaliDetailInput, tag="tally_details", not_found="ردیف تالی یافت نشد",
#     ),
#     make_crud_router(
#         prefix="/tali-kala-diamound", table="fa_tali_kala_diamound", pk="id_tali_kala_diamound",
#         model=TaliKalaDiamoundInput, tag="tali_kala_diamound", not_found="ردیف دیماند یافت نشد",
#         column_overrides={
#             "tali_id": "tali_id",
#             "kala_diamound_id": "kala_diamound_id",
#             "code": "code",
#         },
#     ),

#     make_crud_router(
#         prefix="/tali-kala-price", table="fa_tali_kala_price", pk="id_tali_kala_price",
#         model=TaliKalaPriceInput, tag="tali_kala_price", not_found="ردیف قیمت یافت نشد",
#         column_overrides={"tali_id": "tali_id", "kala_price_id": "kala_price_id", "code": "code"},
#     ),
#     make_crud_router(
#         prefix="/tali-kala-dangerous", table="fa_tali_kala_dangerous", pk="id_tali_kala_dangerous",
#         model=TaliKalaDangerousInput, tag="tali_kala_dangerous", not_found="ردیف خطرناک یافت نشد",
#         column_overrides={"tali_id": "tali_id", "kala_dangerous_id": "kala_dangerous_id", "code": "code"},
#     ),
#     make_crud_router(
#         prefix="/tali-kala-other-service", table="fa_tali_kala_other_service", pk="id_tali_kala_other_service",
#         model=TaliKalaOtherServiceInput, tag="tali_kala_other_service", not_found="ردیف خدمات یافت نشد",
#         column_overrides={
#             "tali_id": "tali_id", "kala_other_service_id": "kala_other_service_id", "code": "code",
#             "number_service": "NUMBER_SERVICE",
#         },
#     ),
#     make_crud_router(
#         prefix="/tali-kala-strip", table="fa_tali_kala_strip", pk="id_tali_kala_strip",
#         model=TaliKalaStripInput, tag="tali_kala_strip", not_found="ردیف استریپ یافت نشد",
#         column_overrides={
#             "tali_id": "tali_id", "kala_strip_id": "kala_strip_id",
#             "code": "code", "pricing_type": "pricing_type",
#         },
#     ),
#     make_crud_router(
#         prefix="/tali-kala-time-stop", table="fa_tali_kala_time_stop_vehicle", pk="id_tali_kala_time_stop_vehicle",
#         model=TaliKalaTimeStopInput, tag="tali_kala_time_stop", not_found="ردیف توقف شبانه یافت نشد",
#         column_overrides={"tali_id": "tali_id", "kala_time_stop_vehicle_id": "kala_time_stop_vehicle_id", "code": "code"},
#     ),
#     make_crud_router(
#         prefix="/tali-kala-vehicle-enter", table="fa_tali_kala_vehicle_enter_price", pk="id_tali_kala_vehicle_enter_price",
#         model=TaliKalaVehicleEnterInput, tag="tali_kala_vehicle_enter", not_found="ردیف ورود خودرو یافت نشد",
#         column_overrides={"tali_id": "tali_id", "kala_vehicle_enter_price_id": "kala_vehicle_enter_price_id", "code": "code"},
#     ),
#     make_crud_router(
#         prefix="/ghabz-header", table="fa_ghabz_anbar_header", pk="ID_ghabz",
#         model=GhabzHeaderInput, tag="ghabz_header", not_found="قبض یافت نشد",
#         column_overrides={
#             "number_ghabz": "number_ghabz", "number_ghabz_uniqe": "number_ghabz_uniqe",
#             "number_tali": "NUMBER_tali", "number_royea": "number_royea",
#             "number_kantiner": "number_kantiner", "number_mantaghe_azad": "number_mantaghe_azad",
#             "number_mojavez_uuloading": "number_mojavez_uuloading", "number_marze": "number_MARZE",
#             "weight": "weight", "number_sanad": "number_sanad", "date_sanad": "date_sanad",
#             "number_pigiri_anbar": "number_pigiri_anbar", "status_bimeh": "status_BIMEH",
#             "id_company_bimeh": "ID_COMPANY_bimeh", "id_anbar": "ID_anbar",
#             "id_tagh_anbara": "ID_tagh_anbara", "id_anbar_response": "ID_anbar_response",
#             "asnad_rasmi": "asnad_rasmi", "name_maneger": "NAME_maneger",
#         },
#     ),
#     make_crud_router(
#         prefix="/ghabz-details", table="FA_ghabz_anbar_DETAILES", pk="ID_ghabz_anbar_DETAILS",
#         model=GhabzDetailInput, tag="ghabz_details", not_found="ردیف قبض یافت نشد",
#         column_overrides={
#             "code_kala": "code_kala", "code_kala_kantiner": "code_kala_kantiner",
#             "type_basteh": "TYPE_BASTEh", "number_kantiner": "NUMBER_KAntiner",
#             "weighte_asnad": "WEIGHTE_asnad",
#         },
#     ),
# ]

"""One model + one make_crud_router() call per table.

To add a simple table:
  1. DESC the table (or read the column dump) - note pk + writable columns + their EXACT case.
  2. Add a Pydantic model with the writable columns (lowercase field names = JSON keys).
  3. Add a make_crud_router(...) call below and append the result to `crud_routers`.

Casing rule: pk and audit names are passed EXACTLY as stored (UPPERCASE for the
upper-named FA_ tables). For fields, the column defaults to FIELD.upper(); list any
column whose stored name isn't that (lowercase/mixed-case, or a rename) in
column_overrides with its exact spelling.
"""
from pydantic import BaseModel, Field

from app.crud.factory import make_crud_router, Audit


# ----- FA_KALA : goods (standard uppercase table) -----
class KalaInput(BaseModel):
    name_kala: str = Field(min_length=1)
    unite: str | None = None


# ----- FA_ANBAR : warehouses (rename responsible -> NAME_MASOL) -----
class AnbarInput(BaseModel):
    name_anbar: str = Field(min_length=1)
    address: str | None = None
    responsible: str | None = None
    phone: str | None = None


# ----- FA_PRODUCT_OWNER : cargo owners (NO audit / soft-delete columns) -----
class OwnerInput(BaseModel):
    name: str | None = None
    family: str | None = None
    national_code: str | None = None
    type: str | None = None
    address: str | None = None
    mobile_force: str | None = None
    mobile: str | None = None


# ----- FA_SYS_TERM_CATEGORIES : coding categories (prefixed audit column names) -----
class TermCategoryInput(BaseModel):
    key: str | None = None
    title: str | None = None
    parent_id: int | None = None
    status: str | None = None
    language: str | None = None


# ----- fa_kala_price : storage price rows (lowercase table, mixed-case cols, FK id_kala) -----
class KalaPriceInput(BaseModel):
    id_kala: int | None = None            # FK -> FA_KALA (plain number for now)
    goods_group: str | None = None        # گروه کالا (Table 1 row label, unit embedded)
    storage_price: float | None = None    # انبارداری (Table 1 storage rate)
    price_30_day: float | None = None
    price_60_day: float | None = None
    price_90_day: float | None = None
    price_unloding: float | None = None   # تخلیه و بارگیری (Table 1 handling rate)
    description: str | None = None
    code: str = Field(min_length=1)       # CODE is NOT NULL in the DB
    is_dangerous: str | None = None

# ----- FA_REPRESENTATIVE_COMPANY : representative companies (standard) -----
class CompanyInput(BaseModel):
    company: str | None = None
    name: str | None = None
    family: str | None = None
    national_code: str | None = None
    mobile: str | None = None
    address: str | None = None


# ----- FA_TAGH_ANBAR : racks (standard + FK id_anbar) -----
class TaghInput(BaseModel):
    name_tagh: str = Field(min_length=1)
    id_anbar: int | None = None
    description: str | None = None


# ----- FA_SYS_TERMS : coding terms (prefixed audit, like categories) -----
class TermInput(BaseModel):
    category_id: int | None = None
    key: str | None = None
    value: str | None = None
    parent_id: int | None = None
    status: str | None = None
    order_no: int | None = None
    description: str | None = None


# ----- fa_kala_dangerous : dangerous-goods rates (numeric prices, no id_kala) -----
class KalaDangerousInput(BaseModel):
    code: str | None = None
    title: str | None = None
    storage_price: float | None = None    # انبارداری (Table storage rate)
    price_30_day: float | None = None
    price_60_day: float | None = None
    price_90_day: float | None = None
    price_unloding: float | None = None   # تخلیه و بارگیری (Table handling rate)
    description: str | None = None


# ----- fa_kala_diamound : demand rates (string prices; renamed columns) -----
class KalaDiamoundInput(BaseModel):
    code: str | None = None
    title: str | None = None
    price_gher_edari: str | None = None
    price_holiday: str | None = None
    description: str | None = None


# ----- fa_kala_other_service : other-service rates (string price) -----
class KalaOtherServiceInput(BaseModel):
    code: str | None = None
    title: str | None = None
    price: str | None = None
    description: str | None = None


# ----- fa_kala_strip : strip/stuffing rates (normal/non-standard/dangerous strings) -----
class KalaStripInput(BaseModel):
    code: str | None = None
    title: str | None = None
    normal: str | None = None
    non_standard: str | None = None
    dangerous: str | None = None
    description: str | None = None


# ----- fa_kala_time_stop_vehicle : night-stop rates (string price) -----
class KalaTimeStopInput(BaseModel):
    code: str | None = None
    title: str | None = None
    price: str | None = None
    description: str | None = None


# ----- fa_kala_vehicle_enter_price : entry/yard fee (string price) -----
class KalaVehicleEnterInput(BaseModel):
    code: str | None = None
    title: str | None = None
    price: str | None = None
    description: str | None = None


# ----- FA_TALI_HEADER : tally shipment header -----
# BLOB (UPLOAD_DOCUMENT) and CLOB (DESCRIPTION) are deferred to a later pass —
# they don't serialize to JSON via SELECT *, so they're excluded from this model.
class TaliHeaderInput(BaseModel):
    number_karaneh: str | None = None       # شماره کارنه / ترانزیت
    radef_marze: int | None = None          # ردیف مرزی
    date_enter_marze: str | None = None     # تاریخ ورود به مرز (ISO date string)
    date_unloading: str | None = None       # تاریخ تخلیه (ISO date string)
    id_marze: int | None = None             # نام مرز ورودی → terms cat 1
    id_company: int | None = None           # نام شرکت حمل → companies
    id_respons_company: int | None = None   # نام نماینده شرکت حمل → companies
    id_product_ownear: int | None = None    # صاحب کالا → owners (note: DB spelling)
    id_country: int | None = None           # مبدا حمل (کشور) → terms cat 2
    number_bimeh: str | None = None         # شماره بیمه نامه
    tali_number: str | None = None          # شماره تالی خودکار، مانند 1405-1
    number_ghabz: int | None = None         # قبض الکترونیک
    name_arzyab: str | None = None          # نام ارزیاب
    number_barnameh: str | None = None      # شماره بارنامه
    is_bimeh: str | None = None             # آیا بیمه دارد؟ (بله/خیر)
    name_anbardar: str | None = None        # نام انبار دار
    accepted_gomrok: str | None = None      # تایید گمرک
    company_bimeh: str | None = None        # شرکت بیمه گر

# ----- FA_TALI_DETAILES : tally goods-lines (master-detail under a header) -----
class TaliDetailInput(BaseModel):
    id_headers_tali: int                      # link to FA_TALI_HEADER.ID_TALI (required)
    id_anbar: int | None = None               # انبار → FA_ANBAR
    id_tagh_anbar: int | None = None          # طاق → FA_TAGH_ANBAR
    number_ghabze_anbar: int | None = None    # قبض انبار
    code_groupe_kala: int = Field(...)        # کد گروه کالا (NOT NULL)
    description_kala: str | None = None       # شرح کالا
    hscode: str | None = None                 # Hscode
    type_bastem: str | None = None            # نوع بسته‌بندی
    number_kala: int = Field(...)             # تعداد (NOT NULL)
    weighte: float = Field(...)               # وزن (NOT NULL)
    type_number_kantiner: str | None = None   # نوع و شماره حامل
    number_ghabze_bskol: int | None = None    # ش قبض باسکول
    weighte_baskol: float = Field(...)        # وزن باسکول (NOT NULL)
    number_hamel: str | None = None           # شماره حامل
    zarib_mahal: str | None   = None          # ضریب محل
    container_type: str | None = None         # نوع کانتینر
    container_number: str | None = None       # شماره کانتینر

# ----- fa_tali_kala_diamound : demand-rate junction (tally ↔ diamound catalog) -----
class TaliKalaDiamoundInput(BaseModel):
    tali_id: int
    kala_diamound_id: int | None = None
    code: str | None = None
    description: str | None = None

# ----- fa_tali_kala_price -----
class TaliKalaPriceInput(BaseModel):
    tali_id: int
    kala_price_id: int | None = None
    code: str | None = None
    description: str | None = None

# ----- fa_tali_kala_dangerous -----
class TaliKalaDangerousInput(BaseModel):
    tali_id: int
    kala_dangerous_id: int | None = None
    code: str | None = None
    description: str | None = None

# ----- fa_tali_kala_other_service (has a count) -----
class TaliKalaOtherServiceInput(BaseModel):
    tali_id: int
    kala_other_service_id: int | None = None
    code: str | None = None
    number_service: int | None = None
    description: str | None = None

# ----- fa_tali_kala_strip -----
class TaliKalaStripInput(BaseModel):
    tali_id: int
    kala_strip_id: int | None = None
    code: str | None = None
    pricing_type: str | None = None   # normal | non_standard | dangerous (which rate column to bill)
    description: str | None = None

# ----- fa_tali_kala_time_stop_vehicle -----
class TaliKalaTimeStopInput(BaseModel):
    tali_id: int
    kala_time_stop_vehicle_id: int | None = None
    code: str | None = None
    description: str | None = None

# ----- fa_tali_kala_vehicle_enter_price -----
class TaliKalaVehicleEnterInput(BaseModel):
    tali_id: int
    kala_vehicle_enter_price_id: int | None = None
    code: str | None = None
    description: str | None = None


# ----- fa_ghabz_anbar_header : warehouse receipt header (BLOB/CLOB deferred) -----
class GhabzHeaderInput(BaseModel):
    number_ghabz: int | None = None
    number_ghabz_uniqe: int | None = None
    number_karaneh: str | None = None
    number_tali: str | None = None
    number_royea: str | None = None
    number_kantiner: int | None = None
    number_mantaghe_azad: int | None = None
    date_unloading: str | None = None
    number_mojavez_uuloading: int | None = None
    id_marze: int | None = None
    number_marze: int | None = None
    date_enter_marze: str | None = None
    id_country: int | None = None
    weight: str | None = None
    number_sanad: str | None = None
    date_sanad: str | None = None
    number_pigiri_anbar: int | None = None
    status_bimeh: str | None = None
    number_bimeh: str | None = None
    id_company_bimeh: int | None = None
    id_anbar: int | None = None
    id_tagh_anbara: int | None = None
    id_anbar_response: int | None = None
    id_company: int | None = None
    id_product_ownear: int | None = None
    asnad_rasmi: str | None = None
    name_anbardar: str | None = None
    name_maneger: str | None = None
    company_bimeh: str | None = None
    tali_id: int | None = None


# ----- FA_ghabz_anbar_DETAILES : receipt line items -----
class GhabzDetailInput(BaseModel):
    id_ghabz_anbar_headar: int
    code_kala: int = Field(...)
    code_kala_kantiner: int | None = None
    description_kala: str | None = None
    type_basteh: str | None = None
    number_kala: int = Field(...)
    number_kantiner: int | None = None
    weighte_asnad: float = Field(...)
    weighte_baskol: float = Field(...)
    number_hamel: str | None = None
    id_tagh_anbar: int | None = None
    
crud_routers = [
    make_crud_router(
        prefix="/items", table="FA_KALA", pk="ID_KALA",
        model=KalaInput, tag="kala", not_found="کالا یافت نشد",
    ),
    make_crud_router(
        prefix="/anbar", table="FA_ANBAR", pk="ID_ANBAR",
        model=AnbarInput, tag="anbar", not_found="انبار یافت نشد",
        column_overrides={"responsible": "NAME_MASOL"},
        order_by="SORT_ORDER",            # explicit display order, not the pk
    ),
    make_crud_router(
        prefix="/owners", table="FA_PRODUCT_OWNER", pk="ID_OWNER",
        model=OwnerInput, tag="owners", not_found="مالک یافت نشد",
        audit=None,                       # this table has no audit/soft-delete columns
    ),
    make_crud_router(
        prefix="/term-categories", table="FA_SYS_TERM_CATEGORIES", pk="SYS_TERM_CATEGORY_ID",
        model=TermCategoryInput, tag="term_categories", not_found="دسته یافت نشد",
        column_overrides={
            "key": "SYS_TERM_CATEGORY_KEY",
            "title": "SYS_TERM_CATEGORY_TITLE",
            "parent_id": "SYS_TERM_CATEGORY_PARENT_ID",
            "status": "SYS_TERM_CATEGORY_STATUS",
            # language -> LANGUAGE (already FIELD.upper(), no override needed)
        },
        audit=Audit(
            is_deleted="SYS_TERM_CATEGORY_IS_DELETED",
            create_at="SYS_TERM_CATEGORY_CREATED_AT",
            create_by="SYS_TERM_CATEGORY_CREATED_BY",
            modify_at="SYS_TERM_CATEGORY_MODIFIED_AT",
            modify_by="SYS_TERM_CATEGORY_MODIFIED_BY",
        ),
    ),
    make_crud_router(
        prefix="/kala-price", table="fa_kala_price", pk="id_kala_price",
        model=KalaPriceInput, tag="kala_price", not_found="ردیف قیمت یافت نشد",
        column_overrides={
            # columns the original devs stored lowercase -> quote them exactly as-is
            "id_kala": "id_kala",
            "goods_group": "goods_group",
            "storage_price": "storage_price",
            "price_30_day": "price_30_day",
            "price_60_day": "price_60_day",
            "price_90_day": "price_90_day",
            "price_unloding": "price_unloding",
            # code/description/is_dangerous are UPPERCASE in the DB -> default handles them
        },
    ),
    make_crud_router(
        prefix="/companies", table="FA_REPRESENTATIVE_COMPANY", pk="ID_REPRE_COMPANY",
        model=CompanyInput, tag="companies", not_found="شرکت یافت نشد",
    ),
    make_crud_router(
        prefix="/tagh", table="FA_TAGH_ANBAR", pk="ID_TAGH",
        model=TaghInput, tag="tagh", not_found="طاق یافت نشد",
    ),
    make_crud_router(
        prefix="/terms", table="FA_SYS_TERMS", pk="SYS_TERM_ID",
        model=TermInput, tag="terms", not_found="ترم یافت نشد",
        column_overrides={
            "category_id": "SYS_TERM_CATEGORY_ID",
            "key": "SYS_TERM_KEY",
            "value": "SYS_TERM_VALUE",
            "parent_id": "SYS_TERM_PARENT_ID",
            "status": "SYS_TERM_STATUS",
            "order_no": "SYS_TERM_ORDER",
            "description": "SYS_TERM_DESCRIPTION",
        },
        audit=Audit(
            is_deleted="SYS_TERM_IS_DELETED",
            create_at="SYS_TERM_CREATED_AT",
            create_by="SYS_TERM_CREATED_BY",
            modify_at="SYS_TERM_MODIFIED_AT",
            modify_by="SYS_TERM_MODIFIED_BY",
        ),
    ),
    make_crud_router(
        prefix="/kala-dangerous", table="fa_kala_dangerous", pk="id_kala_dangerous",
        model=KalaDangerousInput, tag="kala_dangerous", not_found="ردیف یافت نشد",
        column_overrides={
            "code": "code",
            "storage_price": "storage_price",
            "price_30_day": "price_30_day", "price_60_day": "price_60_day",
            "price_90_day": "price_90_day", "price_unloding": "price_unloding",
        },
    ),
    make_crud_router(
        prefix="/kala-diamound", table="fa_kala_diamound", pk="id_kala_diamound",
        model=KalaDiamoundInput, tag="kala_diamound", not_found="ردیف یافت نشد",
        column_overrides={
            "code": "code", "title": "title",
            "price_gher_edari": "price_gher_edari", "price_holiday": "price_holiday",
        },
    ),
    make_crud_router(
        prefix="/kala-other-service", table="fa_kala_other_service", pk="id_kala_other_service",
        model=KalaOtherServiceInput, tag="kala_other_service", not_found="ردیف یافت نشد",
        column_overrides={"code": "code", "title": "title", "price": "price"},
    ),
    make_crud_router(
        prefix="/kala-strip", table="fa_kala_strip", pk="id_kala_strip",
        model=KalaStripInput, tag="kala_strip", not_found="ردیف یافت نشد",
        column_overrides={
            "code": "code", "title": "title", "normal": "normal",
            "non_standard": "non_standard", "dangerous": "dangerous",
        },
    ),
    make_crud_router(
        prefix="/kala-time-stop", table="fa_kala_time_stop_vehicle", pk="id_kala_time_stop_vehicle",
        model=KalaTimeStopInput, tag="kala_time_stop", not_found="ردیف یافت نشد",
        column_overrides={"code": "code", "title": "title", "price": "price"},
    ),
    make_crud_router(
        prefix="/kala-vehicle-enter", table="fa_kala_vehicle_enter_price", pk="id_kala_vehicle_enter_price",
        model=KalaVehicleEnterInput, tag="kala_vehicle_enter", not_found="ردیف یافت نشد",
        column_overrides={"code": "code", "title": "title", "price": "price"},
    ),
    # /tally-header has a dedicated router because its business number must be
    # allocated atomically by the backend. See app/routers/tally_header.py.
    make_crud_router(
        prefix="/tally-details", table="FA_TALI_DETAILES", pk="ID_TALI_DETAILS",
        model=TaliDetailInput, tag="tally_details", not_found="ردیف تالی یافت نشد",
    ),
    make_crud_router(
        prefix="/tali-kala-diamound", table="fa_tali_kala_diamound", pk="id_tali_kala_diamound",
        model=TaliKalaDiamoundInput, tag="tali_kala_diamound", not_found="ردیف دیماند یافت نشد",
        column_overrides={
            "tali_id": "tali_id",
            "kala_diamound_id": "kala_diamound_id",
            "code": "code",
        },
    ),

    make_crud_router(
        prefix="/tali-kala-price", table="fa_tali_kala_price", pk="id_tali_kala_price",
        model=TaliKalaPriceInput, tag="tali_kala_price", not_found="ردیف قیمت یافت نشد",
        column_overrides={"tali_id": "tali_id", "kala_price_id": "kala_price_id", "code": "code"},
    ),
    make_crud_router(
        prefix="/tali-kala-dangerous", table="fa_tali_kala_dangerous", pk="id_tali_kala_dangerous",
        model=TaliKalaDangerousInput, tag="tali_kala_dangerous", not_found="ردیف خطرناک یافت نشد",
        column_overrides={"tali_id": "tali_id", "kala_dangerous_id": "kala_dangerous_id", "code": "code"},
    ),
    make_crud_router(
        prefix="/tali-kala-other-service", table="fa_tali_kala_other_service", pk="id_tali_kala_other_service",
        model=TaliKalaOtherServiceInput, tag="tali_kala_other_service", not_found="ردیف خدمات یافت نشد",
        column_overrides={
            "tali_id": "tali_id", "kala_other_service_id": "kala_other_service_id", "code": "code",
            "number_service": "NUMBER_SERVICE",
        },
    ),
    make_crud_router(
        prefix="/tali-kala-strip", table="fa_tali_kala_strip", pk="id_tali_kala_strip",
        model=TaliKalaStripInput, tag="tali_kala_strip", not_found="ردیف استریپ یافت نشد",
        column_overrides={
            "tali_id": "tali_id", "kala_strip_id": "kala_strip_id",
            "code": "code", "pricing_type": "pricing_type",
        },
    ),
    make_crud_router(
        prefix="/tali-kala-time-stop", table="fa_tali_kala_time_stop_vehicle", pk="id_tali_kala_time_stop_vehicle",
        model=TaliKalaTimeStopInput, tag="tali_kala_time_stop", not_found="ردیف توقف شبانه یافت نشد",
        column_overrides={"tali_id": "tali_id", "kala_time_stop_vehicle_id": "kala_time_stop_vehicle_id", "code": "code"},
    ),
    make_crud_router(
        prefix="/tali-kala-vehicle-enter", table="fa_tali_kala_vehicle_enter_price", pk="id_tali_kala_vehicle_enter_price",
        model=TaliKalaVehicleEnterInput, tag="tali_kala_vehicle_enter", not_found="ردیف ورود خودرو یافت نشد",
        column_overrides={"tali_id": "tali_id", "kala_vehicle_enter_price_id": "kala_vehicle_enter_price_id", "code": "code"},
    ),
    make_crud_router(
        prefix="/ghabz-header", table="fa_ghabz_anbar_header", pk="ID_ghabz",
        model=GhabzHeaderInput, tag="ghabz_header", not_found="قبض یافت نشد",
        column_overrides={
            "number_ghabz": "number_ghabz", "number_ghabz_uniqe": "number_ghabz_uniqe",
            "number_tali": "NUMBER_tali", "number_royea": "number_royea",
            "number_kantiner": "number_kantiner", "number_mantaghe_azad": "number_mantaghe_azad",
            "number_mojavez_uuloading": "number_mojavez_uuloading", "number_marze": "number_MARZE",
            "weight": "weight", "number_sanad": "number_sanad", "date_sanad": "date_sanad",
            "number_pigiri_anbar": "number_pigiri_anbar", "status_bimeh": "status_BIMEH",
            "id_company_bimeh": "ID_COMPANY_bimeh", "id_anbar": "ID_anbar",
            "id_tagh_anbara": "ID_tagh_anbara", "id_anbar_response": "ID_anbar_response",
            "asnad_rasmi": "asnad_rasmi", "name_maneger": "NAME_maneger",
        },
    ),
    make_crud_router(
        prefix="/ghabz-details", table="FA_ghabz_anbar_DETAILES", pk="ID_ghabz_anbar_DETAILS",
        model=GhabzDetailInput, tag="ghabz_details", not_found="ردیف قبض یافت نشد",
        column_overrides={
            "code_kala": "code_kala", "code_kala_kantiner": "code_kala_kantiner",
            "type_basteh": "TYPE_BASTEh", "number_kantiner": "NUMBER_KAntiner",
            "weighte_asnad": "WEIGHTE_asnad",
        },
    ),
]
