// import type { CrudConfig } from './components/CrudResource'

// // ---- کالا ----
// interface Kala {
//   id_kala: number
//   name_kala: string
//   unite: string | null
// }
// const kala: CrudConfig<Kala> = {
//   route: '/kala',
//   path: '/items',
//   queryKey: 'kala',
//   title: 'کالاها',
//   entity: 'کالا',
//   pkField: 'id_kala',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_kala' },
//     { key: 'name', label: 'نام کالا', field: 'name_kala' },
//     { key: 'unite', label: 'واحد', field: 'unite' },
//   ],
//   fields: [
//     { key: 'name_kala', label: 'نام کالا', required: true },
//     { key: 'unite', label: 'واحد' },
//   ],
// }

// // ---- انبار ----
// interface Anbar {
//   id_anbar: number
//   name_anbar: string
//   address: string | null
//   responsible: string | null
//   phone: string | null
// }
// const anbar: CrudConfig<Anbar> = {
//   route: '/anbar',
//   path: '/anbar',
//   queryKey: 'anbar',
//   title: 'انبارها',
//   entity: 'انبار',
//   pkField: 'id_anbar',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_anbar' },
//     { key: 'name', label: 'نام انبار', field: 'name_anbar' },
//     { key: 'address', label: 'آدرس', field: 'address' },
//     { key: 'masol', label: 'مسئول انبار', field: 'responsible' },
//     { key: 'phone', label: 'شماره همراه', field: 'phone' },
//   ],
//   fields: [
//     { key: 'name_anbar', label: 'نام انبار', required: true },
//     { key: 'address', label: 'آدرس' },
//     { key: 'responsible', label: 'مسئول انبار' },
//     { key: 'phone', label: 'شماره همراه' },
//   ],
// }
// // ---- مالکین کالا (no audit columns) ----
// interface Owner {
//   id_owner: number; name: string | null; family: string | null
//   national_code: string | null; type: string | null; address: string | null
//   mobile_force: string | null; mobile: string | null
// }
// const owners: CrudConfig<Owner> = {
//   route: '/owners', path: '/owners', queryKey: 'owners',
//   title: 'مالکین کالا', entity: 'مالک', pkField: 'id_owner',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_owner' },
//     { key: 'name', label: 'نام', field: 'name' },
//     { key: 'family', label: 'نام خانوادگی', field: 'family' },
//     { key: 'national_code', label: 'کد ملی', field: 'national_code' },
//     { key: 'mobile', label: 'موبایل', field: 'mobile' },
//   ],
//   fields: [
//     { key: 'name', label: 'نام' },
//     { key: 'family', label: 'نام خانوادگی' },
//     { key: 'national_code', label: 'کد ملی' },
//     { key: 'type', label: 'نوع' },
//     { key: 'address', label: 'آدرس' },
//     { key: 'mobile_force', label: 'تلفن ثابت' },
//     { key: 'mobile', label: 'موبایل' },
//   ],
// }

// // ---- دسته‌بندی کدینگ (prefixed audit cols; clean field names via overrides) ----
// interface TermCategory {
//   sys_term_category_id: number; key: string | null; title: string | null
//   parent_id: number | null; status: string | null; language: string | null
// }
// const termCategories: CrudConfig<TermCategory> = {
//   route: '/term-categories', path: '/term-categories', queryKey: 'term_categories',
//   title: 'دسته‌بندی کدینگ', entity: 'دسته', pkField: 'sys_term_category_id',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'sys_term_category_id' },
//     { key: 'key', label: 'کلید', field: 'key' },
//     { key: 'title', label: 'عنوان', field: 'title' },
//     { key: 'status', label: 'وضعیت', field: 'status' },
//   ],
//   fields: [
//     { key: 'key', label: 'کلید' },
//     { key: 'title', label: 'عنوان' },
//     { key: 'parent_id', label: 'شناسه والد', type: 'number' },
//     { key: 'status', label: 'وضعیت' },
//     { key: 'language', label: 'زبان' },
//   ],
// }

// // ---- قیمت کالا (lowercase table, mixed-case cols, FK id_kala, CODE required) ----
// interface KalaPrice {
//   id_kala_price: number; id_kala: number | null; code: string | null
//   goods_group: string | null; storage_price: number | null
//   price_30_day: number | null; price_60_day: number | null; price_90_day: number | null
//   price_unloding: number | null; is_dangerous: string | null; description: string | null
// }
// const kalaPrice: CrudConfig<KalaPrice> = {
//   route: '/kala-price', path: '/kala-price', queryKey: 'kala_price',
//   title: 'قیمت کالا', entity: 'ردیف قیمت', pkField: 'id_kala_price',
//   // Table-1 tariff view: code · goods group · storage (انبارداری) · handling (تخلیه و بارگیری)
//   columns: [
//     { key: 'code', label: 'کد', field: 'code' },
//     { key: 'goods_group', label: 'گروه کالا', field: 'goods_group' },
//     { key: 'storage_price', label: 'انبارداری', field: 'storage_price' },
//     { key: 'price_unloding', label: 'تخلیه و بارگیری', field: 'price_unloding' },
//   ],
//   fields: [
//     { key: 'code', label: 'کد', required: true },
//     { key: 'goods_group', label: 'گروه کالا' },
//     { key: 'storage_price', label: 'انبارداری', type: 'number' },
//     { key: 'price_unloding', label: 'تخلیه و بارگیری', type: 'number' },
//     // kept editable for the (deferred) invoice tiers + existing data; not shown in the list
//     { key: 'price_30_day', label: 'قیمت ۳۰ روز', type: 'number' },
//     { key: 'price_60_day', label: 'قیمت ۶۰ روز', type: 'number' },
//     { key: 'price_90_day', label: 'قیمت ۹۰ روز', type: 'number' },
//     { key: 'id_kala', label: 'شناسه کالا', type: 'number' },
//     { key: 'is_dangerous', label: 'خطرناک؟' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }
// // ---- شرکت‌های نماینده ----
// interface Company {
//   id_repre_company: number; company: string | null; name: string | null
//   family: string | null; national_code: string | null; mobile: string | null; address: string | null
// }
// const companies: CrudConfig<Company> = {
//   route: '/companies', path: '/companies', queryKey: 'companies',
//   title: 'شرکت‌های نماینده', entity: 'شرکت', pkField: 'id_repre_company',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_repre_company' },
//     { key: 'company', label: 'شرکت', field: 'company' },
//     { key: 'name', label: 'نام', field: 'name' },
//     { key: 'family', label: 'نام خانوادگی', field: 'family' },
//     { key: 'mobile', label: 'موبایل', field: 'mobile' },
//   ],
//   fields: [
//     { key: 'company', label: 'نام شرکت' },
//     { key: 'name', label: 'نام نماینده' },
//     { key: 'family', label: 'نام خانوادگی' },
//     { key: 'national_code', label: 'کد ملی' },
//     { key: 'mobile', label: 'موبایل' },
//     { key: 'address', label: 'آدرس' },
//   ],
// }

// // ---- طاق‌ها ----
// interface Tagh {
//   id_tagh: number; name_tagh: string; id_anbar: number | null; description: string | null
// }
// const tagh: CrudConfig<Tagh> = {
//   route: '/tagh', path: '/tagh', queryKey: 'tagh',
//   title: 'طاق‌ها', entity: 'طاق', pkField: 'id_tagh',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_tagh' },
//     { key: 'name', label: 'نام طاق', field: 'name_tagh' },
//     { key: 'anbar', label: 'شناسه انبار', field: 'id_anbar' },
//   ],
//   fields: [
//     { key: 'name_tagh', label: 'نام طاق', required: true },
//     { key: 'id_anbar', label: 'شناسه انبار', type: 'number' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }

// // ---- کدینگ ----
// interface Term {
//   sys_term_id: number; category_id: number | null; key: string | null; value: string | null
//   parent_id: number | null; status: string | null; order_no: number | null; description: string | null
// }
// const terms: CrudConfig<Term> = {
//   route: '/terms', path: '/terms', queryKey: 'terms',
//   title: 'کدینگ', entity: 'کد', pkField: 'sys_term_id',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'sys_term_id' },
//     { key: 'key', label: 'کلید', field: 'key' },
//     { key: 'value', label: 'مقدار', field: 'value' },
//     { key: 'status', label: 'وضعیت', field: 'status' },
//   ],
//   fields: [
//     { key: 'category_id', label: 'شناسه دسته', type: 'number' },
//     { key: 'key', label: 'کلید' },
//     { key: 'value', label: 'مقدار' },
//     { key: 'parent_id', label: 'شناسه والد', type: 'number' },
//     { key: 'status', label: 'وضعیت' },
//     { key: 'order_no', label: 'ترتیب', type: 'number' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }

// // ---- نرخ کالای خطرناک ----
// interface KalaDangerous {
//   id_kala_dangerous: number; code: string | null; title: string | null
//   price_30_day: number | null; price_60_day: number | null; price_90_day: number | null
//   price_unloding: number | null; description: string | null
// }
// const kalaDangerous: CrudConfig<KalaDangerous> = {
//   route: '/kala-dangerous', path: '/kala-dangerous', queryKey: 'kala_dangerous',
//   title: 'نرخ کالای خطرناک', entity: 'ردیف', pkField: 'id_kala_dangerous',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_kala_dangerous' },
//     { key: 'code', label: 'کد', field: 'code' },
//     { key: 'title', label: 'عنوان', field: 'title' },
//     { key: 'p30', label: 'قیمت ۳۰ روز', field: 'price_30_day' },
//   ],
//   fields: [
//     { key: 'code', label: 'کد' },
//     { key: 'title', label: 'عنوان' },
//     { key: 'price_30_day', label: 'قیمت ۳۰ روز', type: 'number' },
//     { key: 'price_60_day', label: 'قیمت ۶۰ روز', type: 'number' },
//     { key: 'price_90_day', label: 'قیمت ۹۰ روز', type: 'number' },
//     { key: 'price_unloding', label: 'هزینه تخلیه', type: 'number' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }

// // ---- نرخ دیماند ----
// interface KalaDiamound {
//   id_kala_diamound: number; code: string | null; title: string | null
//   price_gher_edari: string | null; price_holiday: string | null; description: string | null
// }
// const kalaDiamound: CrudConfig<KalaDiamound> = {
//   route: '/kala-diamound', path: '/kala-diamound', queryKey: 'kala_diamound',
//   title: 'نرخ دیماند', entity: 'ردیف', pkField: 'id_kala_diamound',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_kala_diamound' },
//     { key: 'code', label: 'کد', field: 'code' },
//     { key: 'title', label: 'عنوان', field: 'title' },
//   ],
//   fields: [
//     { key: 'code', label: 'کد' },
//     { key: 'title', label: 'عنوان' },
//     { key: 'price_gher_edari', label: 'نرخ غیر اداری' },
//     { key: 'price_holiday', label: 'نرخ تعطیلات' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }

// // ---- نرخ خدمات دیگر ----
// interface KalaOtherService {
//   id_kala_other_service: number; code: string | null; title: string | null
//   price: string | null; description: string | null
// }
// const kalaOtherService: CrudConfig<KalaOtherService> = {
//   route: '/kala-other-service', path: '/kala-other-service', queryKey: 'kala_other_service',
//   title: 'نرخ خدمات دیگر', entity: 'ردیف', pkField: 'id_kala_other_service',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_kala_other_service' },
//     { key: 'code', label: 'کد', field: 'code' },
//     { key: 'title', label: 'عنوان', field: 'title' },
//     { key: 'price', label: 'قیمت', field: 'price' },
//   ],
//   fields: [
//     { key: 'code', label: 'کد' },
//     { key: 'title', label: 'عنوان' },
//     { key: 'price', label: 'قیمت' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }

// // ---- نرخ استریپ ----
// interface KalaStrip {
//   id_kala_strip: number; code: string | null; title: string | null
//   normal: string | null; non_standard: string | null; dangerous: string | null
//   description: string | null
// }
// const kalaStrip: CrudConfig<KalaStrip> = {
//   route: '/kala-strip', path: '/kala-strip', queryKey: 'kala_strip',
//   title: 'نرخ استریپ', entity: 'ردیف', pkField: 'id_kala_strip',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_kala_strip' },
//     { key: 'code', label: 'کد', field: 'code' },
//     { key: 'title', label: 'عنوان', field: 'title' },
//     { key: 'normal', label: 'عادی', field: 'normal' },
//     { key: 'non_standard', label: 'غیراستاندارد', field: 'non_standard' },
//     { key: 'dangerous', label: 'خطرناک', field: 'dangerous' },
//   ],
//   fields: [
//     { key: 'code', label: 'کد' },
//     { key: 'title', label: 'عنوان' },
//     { key: 'normal', label: 'عادی' },
//     { key: 'non_standard', label: 'غیراستاندارد' },
//     { key: 'dangerous', label: 'خطرناک' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }

// // ---- نرخ توقف شبانه ----
// interface KalaTimeStop {
//   id_kala_time_stop_vehicle: number; code: string | null; title: string | null
//   price: string | null; description: string | null
// }
// const kalaTimeStop: CrudConfig<KalaTimeStop> = {
//   route: '/kala-time-stop', path: '/kala-time-stop', queryKey: 'kala_time_stop',
//   title: 'نرخ توقف شبانه', entity: 'ردیف', pkField: 'id_kala_time_stop_vehicle',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_kala_time_stop_vehicle' },
//     { key: 'code', label: 'کد', field: 'code' },
//     { key: 'title', label: 'عنوان', field: 'title' },
//     { key: 'price', label: 'قیمت', field: 'price' },
//   ],
//   fields: [
//     { key: 'code', label: 'کد' },
//     { key: 'title', label: 'عنوان' },
//     { key: 'price', label: 'قیمت' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }

// // ---- نرخ ورود خودرو ----
// interface KalaVehicleEnter {
//   id_kala_vehicle_enter_price: number; code: string | null; title: string | null
//   price: string | null; description: string | null
// }
// const kalaVehicleEnter: CrudConfig<KalaVehicleEnter> = {
//   route: '/kala-vehicle-enter', path: '/kala-vehicle-enter', queryKey: 'kala_vehicle_enter',
//   title: 'نرخ ورود خودرو', entity: 'ردیف', pkField: 'id_kala_vehicle_enter_price',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_kala_vehicle_enter_price' },
//     { key: 'code', label: 'کد', field: 'code' },
//     { key: 'title', label: 'عنوان', field: 'title' },
//     { key: 'price', label: 'قیمت', field: 'price' },
//   ],
//   fields: [
//     { key: 'code', label: 'کد' },
//     { key: 'title', label: 'عنوان' },
//     { key: 'price', label: 'قیمت' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }
// export const resources: CrudConfig<any>[] = [
//   kala, anbar, owners, termCategories, kalaPrice,
//   companies, tagh, terms,
//   kalaDangerous, kalaDiamound, kalaOtherService, kalaStrip, kalaTimeStop, kalaVehicleEnter,
// ]


//2
// import type { CrudConfig } from './components/CrudResource'

// // ---- کالا ----
// interface Kala {
//   id_kala: number
//   name_kala: string
//   unite: string | null
// }
// const kala: CrudConfig<Kala> = {
//   route: '/kala',
//   path: '/items',
//   queryKey: 'kala',
//   title: 'کالاها',
//   entity: 'کالا',
//   pkField: 'id_kala',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_kala' },
//     { key: 'name', label: 'نام کالا', field: 'name_kala' },
//     { key: 'unite', label: 'واحد', field: 'unite' },
//   ],
//   fields: [
//     { key: 'name_kala', label: 'نام کالا', required: true },
//     { key: 'unite', label: 'واحد' },
//   ],
// }

// // ---- انبار ----
// interface Anbar {
//   id_anbar: number
//   name_anbar: string
//   address: string | null
//   responsible: string | null
//   phone: string | null
// }
// const anbar: CrudConfig<Anbar> = {
//   route: '/anbar',
//   path: '/anbar',
//   queryKey: 'anbar',
//   title: 'انبارها',
//   entity: 'انبار',
//   pkField: 'id_anbar',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_anbar' },
//     { key: 'name', label: 'نام انبار', field: 'name_anbar' },
//     { key: 'address', label: 'آدرس', field: 'address' },
//     { key: 'masol', label: 'مسئول انبار', field: 'responsible' },
//     { key: 'phone', label: 'شماره همراه', field: 'phone' },
//   ],
//   fields: [
//     { key: 'name_anbar', label: 'نام انبار', required: true },
//     { key: 'address', label: 'آدرس' },
//     { key: 'responsible', label: 'مسئول انبار' },
//     { key: 'phone', label: 'شماره همراه' },
//   ],
// }
// // ---- مالکین کالا (no audit columns) ----
// interface Owner {
//   id_owner: number; name: string | null; family: string | null
//   national_code: string | null; type: string | null; address: string | null
//   mobile_force: string | null; mobile: string | null
// }
// const owners: CrudConfig<Owner> = {
//   route: '/owners', path: '/owners', queryKey: 'owners',
//   title: 'مالکین کالا', entity: 'مالک', pkField: 'id_owner',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_owner' },
//     { key: 'name', label: 'نام', field: 'name' },
//     { key: 'family', label: 'نام خانوادگی', field: 'family' },
//     { key: 'national_code', label: 'کد ملی', field: 'national_code' },
//     { key: 'mobile', label: 'موبایل', field: 'mobile' },
//   ],
//   fields: [
//     { key: 'name', label: 'نام' },
//     { key: 'family', label: 'نام خانوادگی' },
//     { key: 'national_code', label: 'کد ملی' },
//     { key: 'type', label: 'نوع' },
//     { key: 'address', label: 'آدرس' },
//     { key: 'mobile_force', label: 'تلفن ثابت' },
//     { key: 'mobile', label: 'موبایل' },
//   ],
// }

// // ---- دسته‌بندی کدینگ (prefixed audit cols; clean field names via overrides) ----
// interface TermCategory {
//   sys_term_category_id: number; key: string | null; title: string | null
//   parent_id: number | null; status: string | null; language: string | null
// }
// const termCategories: CrudConfig<TermCategory> = {
//   route: '/term-categories', path: '/term-categories', queryKey: 'term_categories',
//   title: 'دسته‌بندی کدینگ', entity: 'دسته', pkField: 'sys_term_category_id',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'sys_term_category_id' },
//     { key: 'key', label: 'کلید', field: 'key' },
//     { key: 'title', label: 'عنوان', field: 'title' },
//     { key: 'status', label: 'وضعیت', field: 'status' },
//   ],
//   fields: [
//     { key: 'key', label: 'کلید' },
//     { key: 'title', label: 'عنوان' },
//     { key: 'parent_id', label: 'شناسه والد', type: 'number' },
//     { key: 'status', label: 'وضعیت' },
//     { key: 'language', label: 'زبان' },
//   ],
// }

// // ---- قیمت کالا (lowercase table, mixed-case cols, FK id_kala, CODE required) ----
// interface KalaPrice {
//   id_kala_price: number; id_kala: number | null; code: string | null
//   goods_group: string | null; storage_price: number | null
//   price_30_day: number | null; price_60_day: number | null; price_90_day: number | null
//   price_unloding: number | null; is_dangerous: string | null; description: string | null
// }
// const kalaPrice: CrudConfig<KalaPrice> = {
//   route: '/kala-price', path: '/kala-price', queryKey: 'kala_price',
//   title: 'قیمت کالا', entity: 'ردیف قیمت', pkField: 'id_kala_price',
//   // Table-1 tariff view: code · goods group · storage (انبارداری) · handling (تخلیه و بارگیری)
//   columns: [
//     { key: 'code', label: 'کد', field: 'code' },
//     { key: 'goods_group', label: 'گروه کالا', field: 'goods_group' },
//     { key: 'storage_price', label: 'انبارداری', field: 'storage_price' },
//     { key: 'price_unloding', label: 'تخلیه و بارگیری', field: 'price_unloding' },
//   ],
//   fields: [
//     { key: 'code', label: 'کد', required: true },
//     { key: 'goods_group', label: 'گروه کالا' },
//     { key: 'storage_price', label: 'انبارداری', type: 'number' },
//     { key: 'price_unloding', label: 'تخلیه و بارگیری', type: 'number' },
//     // kept editable for the (deferred) invoice tiers + existing data; not shown in the list
//     { key: 'price_30_day', label: 'قیمت ۳۰ روز', type: 'number' },
//     { key: 'price_60_day', label: 'قیمت ۶۰ روز', type: 'number' },
//     { key: 'price_90_day', label: 'قیمت ۹۰ روز', type: 'number' },
//     { key: 'id_kala', label: 'شناسه کالا', type: 'number' },
//     { key: 'is_dangerous', label: 'خطرناک؟' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }
// // ---- شرکت‌های نماینده ----
// interface Company {
//   id_repre_company: number; company: string | null; name: string | null
//   family: string | null; national_code: string | null; mobile: string | null; address: string | null
// }
// const companies: CrudConfig<Company> = {
//   route: '/companies', path: '/companies', queryKey: 'companies',
//   title: 'شرکت‌های نماینده', entity: 'شرکت', pkField: 'id_repre_company',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_repre_company' },
//     { key: 'company', label: 'شرکت', field: 'company' },
//     { key: 'name', label: 'نام', field: 'name' },
//     { key: 'family', label: 'نام خانوادگی', field: 'family' },
//     { key: 'mobile', label: 'موبایل', field: 'mobile' },
//   ],
//   fields: [
//     { key: 'company', label: 'نام شرکت' },
//     { key: 'name', label: 'نام نماینده' },
//     { key: 'family', label: 'نام خانوادگی' },
//     { key: 'national_code', label: 'کد ملی' },
//     { key: 'mobile', label: 'موبایل' },
//     { key: 'address', label: 'آدرس' },
//   ],
// }

// // ---- طاق‌ها ----
// interface Tagh {
//   id_tagh: number; name_tagh: string; id_anbar: number | null; description: string | null
// }
// const tagh: CrudConfig<Tagh> = {
//   route: '/tagh', path: '/tagh', queryKey: 'tagh',
//   title: 'طاق‌ها', entity: 'طاق', pkField: 'id_tagh',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_tagh' },
//     { key: 'name', label: 'نام طاق', field: 'name_tagh' },
//     { key: 'anbar', label: 'شناسه انبار', field: 'id_anbar' },
//   ],
//   fields: [
//     { key: 'name_tagh', label: 'نام طاق', required: true },
//     { key: 'id_anbar', label: 'شناسه انبار', type: 'number' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }

// // ---- کدینگ ----
// interface Term {
//   sys_term_id: number; category_id: number | null; key: string | null; value: string | null
//   parent_id: number | null; status: string | null; order_no: number | null; description: string | null
// }
// const terms: CrudConfig<Term> = {
//   route: '/terms', path: '/terms', queryKey: 'terms',
//   title: 'کدینگ', entity: 'کد', pkField: 'sys_term_id',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'sys_term_id' },
//     { key: 'key', label: 'کلید', field: 'key' },
//     { key: 'value', label: 'مقدار', field: 'value' },
//     { key: 'status', label: 'وضعیت', field: 'status' },
//   ],
//   fields: [
//     { key: 'category_id', label: 'شناسه دسته', type: 'number' },
//     { key: 'key', label: 'کلید' },
//     { key: 'value', label: 'مقدار' },
//     { key: 'parent_id', label: 'شناسه والد', type: 'number' },
//     { key: 'status', label: 'وضعیت' },
//     { key: 'order_no', label: 'ترتیب', type: 'number' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }

// // ---- نرخ کالای خطرناک ----
// interface KalaDangerous {
//   id_kala_dangerous: number; code: string | null; title: string | null
//   storage_price: number | null
//   price_30_day: number | null; price_60_day: number | null; price_90_day: number | null
//   price_unloding: number | null; description: string | null
// }
// const kalaDangerous: CrudConfig<KalaDangerous> = {
//   route: '/kala-dangerous', path: '/kala-dangerous', queryKey: 'kala_dangerous',
//   title: 'نرخ کالای خطرناک', entity: 'ردیف', pkField: 'id_kala_dangerous',
//   // Tariff view: code · عنوان · انبارداری (storage) · تخلیه و بارگیری (handling)
//   columns: [
//     { key: 'code', label: 'کد', field: 'code' },
//     { key: 'title', label: 'عنوان', field: 'title' },
//     { key: 'storage_price', label: 'انبارداری', field: 'storage_price' },
//     { key: 'price_unloding', label: 'تخلیه و بارگیری', field: 'price_unloding' },
//   ],
//   fields: [
//     { key: 'code', label: 'کد' },
//     { key: 'title', label: 'عنوان' },
//     { key: 'storage_price', label: 'انبارداری', type: 'number' },
//     { key: 'price_unloding', label: 'تخلیه و بارگیری', type: 'number' },
//     // kept editable; not shown in the list
//     { key: 'price_30_day', label: 'قیمت ۳۰ روز', type: 'number' },
//     { key: 'price_60_day', label: 'قیمت ۶۰ روز', type: 'number' },
//     { key: 'price_90_day', label: 'قیمت ۹۰ روز', type: 'number' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }

// // ---- نرخ دیماند ----
// interface KalaDiamound {
//   id_kala_diamound: number; code: string | null; title: string | null
//   price_gher_edari: string | null; price_holiday: string | null; description: string | null
// }
// const kalaDiamound: CrudConfig<KalaDiamound> = {
//   route: '/kala-diamound', path: '/kala-diamound', queryKey: 'kala_diamound',
//   title: 'نرخ دیماند', entity: 'ردیف', pkField: 'id_kala_diamound',
//   columns: [
//     { key: 'code', label: 'کد', field: 'code' },
//     { key: 'title', label: 'عنوان', field: 'title' },
//     { key: 'price_gher_edari', label: 'نرخ غیر اداری', field: 'price_gher_edari' },
//     { key: 'price_holiday', label: 'نرخ تعطیلات', field: 'price_holiday' },
//   ],
//   fields: [
//     { key: 'code', label: 'کد' },
//     { key: 'title', label: 'عنوان' },
//     { key: 'price_gher_edari', label: 'نرخ غیر اداری' },
//     { key: 'price_holiday', label: 'نرخ تعطیلات' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }

// // ---- نرخ خدمات دیگر ----
// interface KalaOtherService {
//   id_kala_other_service: number; code: string | null; title: string | null
//   price: string | null; description: string | null
// }
// const kalaOtherService: CrudConfig<KalaOtherService> = {
//   route: '/kala-other-service', path: '/kala-other-service', queryKey: 'kala_other_service',
//   title: 'نرخ خدمات دیگر', entity: 'ردیف', pkField: 'id_kala_other_service',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_kala_other_service' },
//     { key: 'code', label: 'کد', field: 'code' },
//     { key: 'title', label: 'عنوان', field: 'title' },
//     { key: 'price', label: 'قیمت', field: 'price' },
//   ],
//   fields: [
//     { key: 'code', label: 'کد' },
//     { key: 'title', label: 'عنوان' },
//     { key: 'price', label: 'قیمت' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }

// // ---- نرخ استریپ ----
// interface KalaStrip {
//   id_kala_strip: number; code: string | null; title: string | null
//   normal: string | null; non_standard: string | null; dangerous: string | null
//   description: string | null
// }
// const kalaStrip: CrudConfig<KalaStrip> = {
//   route: '/kala-strip', path: '/kala-strip', queryKey: 'kala_strip',
//   title: 'نرخ استریپ', entity: 'ردیف', pkField: 'id_kala_strip',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_kala_strip' },
//     { key: 'code', label: 'کد', field: 'code' },
//     { key: 'title', label: 'عنوان', field: 'title' },
//     { key: 'normal', label: 'عادی', field: 'normal' },
//     { key: 'non_standard', label: 'غیراستاندارد', field: 'non_standard' },
//     { key: 'dangerous', label: 'خطرناک', field: 'dangerous' },
//   ],
//   fields: [
//     { key: 'code', label: 'کد' },
//     { key: 'title', label: 'عنوان' },
//     { key: 'normal', label: 'عادی' },
//     { key: 'non_standard', label: 'غیراستاندارد' },
//     { key: 'dangerous', label: 'خطرناک' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }

// // ---- نرخ توقف شبانه ----
// interface KalaTimeStop {
//   id_kala_time_stop_vehicle: number; code: string | null; title: string | null
//   price: string | null; description: string | null
// }
// const kalaTimeStop: CrudConfig<KalaTimeStop> = {
//   route: '/kala-time-stop', path: '/kala-time-stop', queryKey: 'kala_time_stop',
//   title: 'نرخ توقف شبانه', entity: 'ردیف', pkField: 'id_kala_time_stop_vehicle',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_kala_time_stop_vehicle' },
//     { key: 'code', label: 'کد', field: 'code' },
//     { key: 'title', label: 'عنوان', field: 'title' },
//     { key: 'price', label: 'قیمت', field: 'price' },
//   ],
//   fields: [
//     { key: 'code', label: 'کد' },
//     { key: 'title', label: 'عنوان' },
//     { key: 'price', label: 'قیمت' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }

// // ---- نرخ ورود خودرو ----
// interface KalaVehicleEnter {
//   id_kala_vehicle_enter_price: number; code: string | null; title: string | null
//   price: string | null; description: string | null
// }
// const kalaVehicleEnter: CrudConfig<KalaVehicleEnter> = {
//   route: '/kala-vehicle-enter', path: '/kala-vehicle-enter', queryKey: 'kala_vehicle_enter',
//   title: 'نرخ ورود خودرو', entity: 'ردیف', pkField: 'id_kala_vehicle_enter_price',
//   columns: [
//     { key: 'id', label: 'شناسه', field: 'id_kala_vehicle_enter_price' },
//     { key: 'code', label: 'کد', field: 'code' },
//     { key: 'title', label: 'عنوان', field: 'title' },
//     { key: 'price', label: 'قیمت', field: 'price' },
//   ],
//   fields: [
//     { key: 'code', label: 'کد' },
//     { key: 'title', label: 'عنوان' },
//     { key: 'price', label: 'قیمت' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }
// export const resources: CrudConfig<any>[] = [
//   kala, anbar, owners, termCategories, kalaPrice,
//   companies, tagh, terms,
//   kalaDangerous, kalaDiamound, kalaOtherService, kalaStrip, kalaTimeStop, kalaVehicleEnter,
// ]

import type { CrudConfig } from './components/CrudResource'

// ---- کالا ----
interface Kala {
  id_kala: number
  name_kala: string
  unite: string | null
}
const kala: CrudConfig<Kala> = {
  route: '/kala',
  path: '/items',
  queryKey: 'kala',
  title: 'کالاها',
  entity: 'کالا',
  pkField: 'id_kala',
  columns: [
    { key: 'name', label: 'نام کالا', field: 'name_kala' },
    { key: 'unite', label: 'واحد', field: 'unite' },
  ],
  fields: [
    { key: 'name_kala', label: 'نام کالا', required: true },
    { key: 'unite', label: 'واحد' },
  ],
}

// ---- انبار ----
interface Anbar {
  id_anbar: number
  name_anbar: string
  address: string | null
  responsible: string | null
  phone: string | null
}
const anbar: CrudConfig<Anbar> = {
  route: '/anbar',
  path: '/anbar',
  queryKey: 'anbar',
  title: 'انبارها',
  entity: 'انبار',
  pkField: 'id_anbar',
  columns: [
    { key: 'name', label: 'نام انبار', field: 'name_anbar' },
    { key: 'address', label: 'آدرس', field: 'address' },
    { key: 'masol', label: 'مسئول انبار', field: 'responsible' },
    { key: 'phone', label: 'شماره همراه', field: 'phone' },
  ],
  fields: [
    { key: 'name_anbar', label: 'نام انبار', required: true },
    { key: 'address', label: 'آدرس' },
    { key: 'responsible', label: 'مسئول انبار' },
    { key: 'phone', label: 'شماره همراه' },
  ],
}
// ---- مالکین کالا (no audit columns) ----
interface Owner {
  id_owner: number; name: string | null; family: string | null
  national_code: string | null; type: string | null; address: string | null
  mobile_force: string | null; mobile: string | null
}
const owners: CrudConfig<Owner> = {
  route: '/owners', path: '/owners', queryKey: 'owners',
  title: 'مالکین کالا', entity: 'مالک', pkField: 'id_owner',
  columns: [
    { key: 'name', label: 'نام', field: 'name' },
    { key: 'family', label: 'نام خانوادگی', field: 'family' },
    { key: 'national_code', label: 'کد ملی', field: 'national_code' },
    { key: 'mobile', label: 'موبایل', field: 'mobile' },
  ],
  fields: [
    { key: 'name', label: 'نام' },
    { key: 'family', label: 'نام خانوادگی' },
    { key: 'national_code', label: 'کد ملی' },
    { key: 'type', label: 'نوع' },
    { key: 'address', label: 'آدرس' },
    { key: 'mobile_force', label: 'تلفن ثابت' },
    { key: 'mobile', label: 'موبایل' },
  ],
}

// ---- دسته‌بندی کدینگ (prefixed audit cols; clean field names via overrides) ----
interface TermCategory {
  sys_term_category_id: number; key: string | null; title: string | null
  parent_id: number | null; status: string | null; language: string | null
}
const termCategories: CrudConfig<TermCategory> = {
  route: '/term-categories', path: '/term-categories', queryKey: 'term_categories',
  title: 'دسته‌بندی کدینگ', entity: 'دسته', pkField: 'sys_term_category_id',
  columns: [
    { key: 'key', label: 'کلید', field: 'key' },
    { key: 'title', label: 'عنوان', field: 'title' },
    { key: 'status', label: 'وضعیت', field: 'status' },
  ],
  fields: [
    { key: 'key', label: 'کلید' },
    { key: 'title', label: 'عنوان' },
    { key: 'parent_id', label: 'شناسه والد', type: 'number' },
    { key: 'status', label: 'وضعیت' },
    { key: 'language', label: 'زبان' },
  ],
}

// ---- قیمت کالا (lowercase table, mixed-case cols, FK id_kala, CODE required) ----
interface KalaPrice {
  id_kala_price: number; id_kala: number | null; code: string | null
  goods_group: string | null; storage_price: number | null
  price_30_day: number | null; price_60_day: number | null; price_90_day: number | null
  price_unloding: number | null; is_dangerous: string | null; description: string | null
}
const kalaPrice: CrudConfig<KalaPrice> = {
  route: '/kala-price', path: '/kala-price', queryKey: 'kala_price',
  title: 'قیمت کالا', entity: 'ردیف قیمت', pkField: 'id_kala_price',
  // Table-1 tariff view: code · goods group · storage (انبارداری) · handling (تخلیه و بارگیری)
  columns: [
    { key: 'code', label: 'کد', field: 'code' },
    { key: 'goods_group', label: 'گروه کالا', field: 'goods_group' },
    { key: 'storage_price', label: 'انبارداری', field: 'storage_price' },
    { key: 'price_unloding', label: 'تخلیه و بارگیری', field: 'price_unloding' },
  ],
  fields: [
    { key: 'code', label: 'کد', required: true },
    { key: 'goods_group', label: 'گروه کالا' },
    { key: 'storage_price', label: 'انبارداری', type: 'number' },
    { key: 'price_unloding', label: 'تخلیه و بارگیری', type: 'number' },
    // kept editable for the (deferred) invoice tiers + existing data; not shown in the list
    { key: 'price_30_day', label: 'قیمت ۳۰ روز', type: 'number' },
    { key: 'price_60_day', label: 'قیمت ۶۰ روز', type: 'number' },
    { key: 'price_90_day', label: 'قیمت ۹۰ روز', type: 'number' },
    { key: 'id_kala', label: 'شناسه کالا', type: 'number' },
    { key: 'is_dangerous', label: 'خطرناک؟' },
    { key: 'description', label: 'توضیحات' },
  ],
}
// ---- شرکت‌های نماینده ----
interface Company {
  id_repre_company: number; company: string | null; name: string | null
  family: string | null; national_code: string | null; mobile: string | null; address: string | null
}
const companies: CrudConfig<Company> = {
  route: '/companies', path: '/companies', queryKey: 'companies',
  title: 'شرکت‌های نماینده', entity: 'شرکت', pkField: 'id_repre_company',
  columns: [
    { key: 'company', label: 'شرکت', field: 'company' },
    { key: 'name', label: 'نام', field: 'name' },
    { key: 'family', label: 'نام خانوادگی', field: 'family' },
    { key: 'mobile', label: 'موبایل', field: 'mobile' },
  ],
  fields: [
    { key: 'company', label: 'نام شرکت' },
    { key: 'name', label: 'نام نماینده' },
    { key: 'family', label: 'نام خانوادگی' },
    { key: 'national_code', label: 'کد ملی' },
    { key: 'mobile', label: 'موبایل' },
    { key: 'address', label: 'آدرس' },
  ],
}

// ---- طاق‌ها ----
interface Tagh {
  id_tagh: number; name_tagh: string; id_anbar: number | null; description: string | null
}
const tagh: CrudConfig<Tagh> = {
  route: '/tagh', path: '/tagh', queryKey: 'tagh',
  title: 'طاق‌ها', entity: 'طاق', pkField: 'id_tagh',
  columns: [
    { key: 'name', label: 'نام طاق', field: 'name_tagh' },
  ],
  fields: [
    { key: 'name_tagh', label: 'نام طاق', required: true },
    { key: 'id_anbar', label: 'شناسه انبار', type: 'number' },
    { key: 'description', label: 'توضیحات' },
  ],
}

// ---- کدینگ ----
interface Term {
  sys_term_id: number; category_id: number | null; key: string | null; value: string | null
  parent_id: number | null; status: string | null; order_no: number | null; description: string | null
}
const terms: CrudConfig<Term> = {
  route: '/terms', path: '/terms', queryKey: 'terms',
  title: 'کدینگ', entity: 'کد', pkField: 'sys_term_id',
  columns: [
    { key: 'key', label: 'کلید', field: 'key' },
    { key: 'value', label: 'مقدار', field: 'value' },
    { key: 'status', label: 'وضعیت', field: 'status' },
  ],
  fields: [
    { key: 'category_id', label: 'شناسه دسته', type: 'number' },
    { key: 'key', label: 'کلید' },
    { key: 'value', label: 'مقدار' },
    { key: 'parent_id', label: 'شناسه والد', type: 'number' },
    { key: 'status', label: 'وضعیت' },
    { key: 'order_no', label: 'ترتیب', type: 'number' },
    { key: 'description', label: 'توضیحات' },
  ],
}

// ---- نرخ کالای خطرناک ----
interface KalaDangerous {
  id_kala_dangerous: number; code: string | null; title: string | null
  storage_price: number | null
  price_30_day: number | null; price_60_day: number | null; price_90_day: number | null
  price_unloding: number | null; description: string | null
}
const kalaDangerous: CrudConfig<KalaDangerous> = {
  route: '/kala-dangerous', path: '/kala-dangerous', queryKey: 'kala_dangerous',
  title: 'نرخ کالای خطرناک', entity: 'ردیف', pkField: 'id_kala_dangerous',
  // Tariff view: code · عنوان · انبارداری (storage) · تخلیه و بارگیری (handling)
  columns: [
    { key: 'code', label: 'کد', field: 'code' },
    { key: 'title', label: 'عنوان', field: 'title' },
    { key: 'storage_price', label: 'انبارداری', field: 'storage_price' },
    { key: 'price_unloding', label: 'تخلیه و بارگیری', field: 'price_unloding' },
  ],
  fields: [
    { key: 'code', label: 'کد' },
    { key: 'title', label: 'عنوان' },
    { key: 'storage_price', label: 'انبارداری', type: 'number' },
    { key: 'price_unloding', label: 'تخلیه و بارگیری', type: 'number' },
    // kept editable; not shown in the list
    { key: 'price_30_day', label: 'قیمت ۳۰ روز', type: 'number' },
    { key: 'price_60_day', label: 'قیمت ۶۰ روز', type: 'number' },
    { key: 'price_90_day', label: 'قیمت ۹۰ روز', type: 'number' },
    { key: 'description', label: 'توضیحات' },
  ],
}

// ---- نرخ دیماند ----
interface KalaDiamound {
  id_kala_diamound: number; code: string | null; title: string | null
  price_gher_edari: string | null; price_holiday: string | null; description: string | null
}
const kalaDiamound: CrudConfig<KalaDiamound> = {
  route: '/kala-diamound', path: '/kala-diamound', queryKey: 'kala_diamound',
  title: 'نرخ دیماند', entity: 'ردیف', pkField: 'id_kala_diamound',
  columns: [
    { key: 'code', label: 'کد', field: 'code' },
    { key: 'title', label: 'عنوان', field: 'title' },
    { key: 'price_gher_edari', label: 'نرخ غیر اداری', field: 'price_gher_edari' },
    { key: 'price_holiday', label: 'نرخ تعطیلات', field: 'price_holiday' },
  ],
  fields: [
    { key: 'code', label: 'کد' },
    { key: 'title', label: 'عنوان' },
    { key: 'price_gher_edari', label: 'نرخ غیر اداری' },
    { key: 'price_holiday', label: 'نرخ تعطیلات' },
    { key: 'description', label: 'توضیحات' },
  ],
}

// ---- نرخ خدمات دیگر ----
interface KalaOtherService {
  id_kala_other_service: number; code: string | null; title: string | null
  price: string | null; description: string | null
}
const kalaOtherService: CrudConfig<KalaOtherService> = {
  route: '/kala-other-service', path: '/kala-other-service', queryKey: 'kala_other_service',
  title: 'نرخ خدمات دیگر', entity: 'ردیف', pkField: 'id_kala_other_service',
  columns: [
    { key: 'code', label: 'کد', field: 'code' },
    { key: 'title', label: 'عنوان', field: 'title' },
    { key: 'price', label: 'قیمت', field: 'price' },
  ],
  fields: [
    { key: 'code', label: 'کد' },
    { key: 'title', label: 'عنوان' },
    { key: 'price', label: 'قیمت' },
    { key: 'description', label: 'توضیحات' },
  ],
}

// ---- نرخ استریپ ----
interface KalaStrip {
  id_kala_strip: number; code: string | null; title: string | null
  normal: string | null; non_standard: string | null; dangerous: string | null
  description: string | null
}
const kalaStrip: CrudConfig<KalaStrip> = {
  route: '/kala-strip', path: '/kala-strip', queryKey: 'kala_strip',
  title: 'نرخ استریپ', entity: 'ردیف', pkField: 'id_kala_strip',
  columns: [
    { key: 'code', label: 'کد', field: 'code' },
    { key: 'title', label: 'عنوان', field: 'title' },
    { key: 'normal', label: 'عادی', field: 'normal' },
    { key: 'non_standard', label: 'غیراستاندارد', field: 'non_standard' },
    { key: 'dangerous', label: 'خطرناک', field: 'dangerous' },
  ],
  fields: [
    { key: 'code', label: 'کد' },
    { key: 'title', label: 'عنوان' },
    { key: 'normal', label: 'عادی' },
    { key: 'non_standard', label: 'غیراستاندارد' },
    { key: 'dangerous', label: 'خطرناک' },
    { key: 'description', label: 'توضیحات' },
  ],
}

// ---- نرخ توقف شبانه ----
interface KalaTimeStop {
  id_kala_time_stop_vehicle: number; code: string | null; title: string | null
  price: string | null; description: string | null
}
const kalaTimeStop: CrudConfig<KalaTimeStop> = {
  route: '/kala-time-stop', path: '/kala-time-stop', queryKey: 'kala_time_stop',
  title: 'نرخ توقف شبانه', entity: 'ردیف', pkField: 'id_kala_time_stop_vehicle',
  columns: [
    { key: 'code', label: 'کد', field: 'code' },
    { key: 'title', label: 'عنوان', field: 'title' },
    { key: 'price', label: 'قیمت', field: 'price' },
  ],
  fields: [
    { key: 'code', label: 'کد' },
    { key: 'title', label: 'عنوان' },
    { key: 'price', label: 'قیمت' },
    { key: 'description', label: 'توضیحات' },
  ],
}

// ---- نرخ ورود خودرو ----
interface KalaVehicleEnter {
  id_kala_vehicle_enter_price: number; code: string | null; title: string | null
  price: string | null; description: string | null
}
const kalaVehicleEnter: CrudConfig<KalaVehicleEnter> = {
  route: '/kala-vehicle-enter', path: '/kala-vehicle-enter', queryKey: 'kala_vehicle_enter',
  title: 'نرخ ورود خودرو', entity: 'ردیف', pkField: 'id_kala_vehicle_enter_price',
  columns: [
    { key: 'code', label: 'کد', field: 'code' },
    { key: 'title', label: 'عنوان', field: 'title' },
    { key: 'price', label: 'قیمت', field: 'price' },
  ],
  fields: [
    { key: 'code', label: 'کد' },
    { key: 'title', label: 'عنوان' },
    { key: 'price', label: 'قیمت' },
    { key: 'description', label: 'توضیحات' },
  ],
}
export const resources: CrudConfig<any>[] = [
  kala, anbar, owners, termCategories, kalaPrice,
  companies, tagh, terms,
  kalaDangerous, kalaDiamound, kalaOtherService, kalaStrip, kalaTimeStop, kalaVehicleEnter,
]