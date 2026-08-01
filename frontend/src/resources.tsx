// import type { CrudConfig } from './components/CrudResource'
// import { useQuery } from '@tanstack/react-query'
// import { apiGet } from './api/client'

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
// // ---- صاحبین کالا (حقیقی / حقوقی) ----
// interface Owner {
//   id_owner: number; name: string | null; family: string | null
//   national_code: string | null; type: 'حقیقی' | 'حقوقی'; company_name: string | null
//   address: string | null; phone: string | null; national_id: string | null
//   economic_code: string | null
// }
// const owners: CrudConfig<Owner> = {
//   route: '/owners', path: '/owners', queryKey: 'owners',
//   title: 'صاحبین کالا', entity: 'صاحب کالا', pkField: 'id_owner',
//   columns: [
//     { key: 'type', label: 'نوع', field: 'type' },
//     {
//       key: 'owner_name', label: 'نام صاحب کالا',
//       render: (row) => row.type === 'حقوقی'
//         ? row.company_name ?? ''
//         : `${row.name ?? ''} ${row.family ?? ''}`.trim(),
//     },
//     {
//       key: 'identifier', label: 'کد ملی / شناسه ملی',
//       render: (row) => row.type === 'حقوقی' ? row.national_id ?? '' : row.national_code ?? '',
//     },
//     { key: 'phone', label: 'تلفن', field: 'phone' },
//     { key: 'address', label: 'آدرس', field: 'address' },
//   ],
//   fields: [
//     {
//       key: 'type', label: 'نوع صاحب کالا', type: 'select', required: true,
//       defaultValue: 'حقیقی',
//       options: [
//         { value: 'حقیقی', label: 'حقیقی' },
//         { value: 'حقوقی', label: 'حقوقی' },
//       ],
//     },
//     { key: 'name', label: 'نام', showWhen: { key: 'type', equals: 'حقیقی' }, required: true },
//     { key: 'family', label: 'نام خانوادگی', showWhen: { key: 'type', equals: 'حقیقی' }, required: true },
//     { key: 'national_code', label: 'کد ملی', showWhen: { key: 'type', equals: 'حقیقی' }, required: true },
//     { key: 'company_name', label: 'نام شرکت', showWhen: { key: 'type', equals: 'حقوقی' }, required: true },
//     { key: 'address', label: 'آدرس', required: true },
//     { key: 'phone', label: 'تلفن', required: true },
//     { key: 'national_id', label: 'شناسه ملی', showWhen: { key: 'type', equals: 'حقوقی' }, required: true },
//     { key: 'economic_code', label: 'کد اقتصادی', showWhen: { key: 'type', equals: 'حقوقی' }, required: true },
//   ],
// }

// // ---- قیمت کالا (lowercase table, mixed-case cols, FK id_kala, CODE required) ----
// interface KalaPrice {
//   id_kala_price: number; id_kala: number | null; code: string | null
//   goods_group: string | null; storage_price: number | null
//   price_30_day: number | null; price_60_day: number | null; price_90_day: number | null
//   price_unloding: number | null; description: string | null
// }
// const kalaPrice: CrudConfig<KalaPrice> = {
//   route: '/kala-price', path: '/kala-price', queryKey: 'kala_price',
//   title: 'کد گروه کالا', entity: 'گروه کالا', pkField: 'id_kala_price',
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
//     { key: 'description', label: 'توضیحات' },
//   ],
// }
// // ---- شرکت حمل و نقل ----
// interface TransportCompany {
//   id_company: number; company_name: string; address: string
//   phone: string; national_id: string; economic_code: string
// }
// const transportCompanies: CrudConfig<TransportCompany> = {
//   route: '/transport-companies', path: '/transport-companies', queryKey: 'transport_companies',
//   title: 'شرکت حمل و نقل', entity: 'شرکت حمل و نقل', pkField: 'id_company',
//   columns: [
//     { key: 'company_name', label: 'اسم شرکت', field: 'company_name' },
//     { key: 'national_id', label: 'شناسه ملی', field: 'national_id' },
//     { key: 'economic_code', label: 'کد اقتصادی', field: 'economic_code' },
//     { key: 'phone', label: 'تلفن', field: 'phone' },
//     { key: 'address', label: 'آدرس', field: 'address' },
//   ],
//   fields: [
//     { key: 'company_name', label: 'اسم شرکت', required: true },
//     { key: 'address', label: 'آدرس', required: true },
//     { key: 'phone', label: 'تلفن', required: true },
//     { key: 'national_id', label: 'شناسه ملی', required: true },
//     { key: 'economic_code', label: 'کد اقتصادی', required: true },
//   ],
// }

// interface CompanyRepresentative {
//   id_repre_company: number; id_company: number; name: string
//   family: string; national_code: string; mobile: string
// }

// function TransportCompanyName({ id }: { id: number }) {
//   const { data } = useQuery({
//     queryKey: ['transport-companies-for-labels'],
//     queryFn: () => apiGet<TransportCompany[]>('/transport-companies'),
//     staleTime: 5 * 60 * 1000,
//   })
//   return data?.find((row) => row.id_company === id)?.company_name ?? '—'
// }

// const companyRepresentatives: CrudConfig<CompanyRepresentative> = {
//   route: '/company-representatives', path: '/company-representatives',
//   queryKey: 'company_representatives', title: 'نمایندگان شرکت‌های حمل‌ونقل',
//   entity: 'نماینده شرکت حمل‌ونقل', pkField: 'id_repre_company',
//   columns: [
//     { key: 'company', label: 'شرکت', render: (row) => <TransportCompanyName id={row.id_company} /> },
//     { key: 'name', label: 'اسم', field: 'name' },
//     { key: 'family', label: 'فامیل', field: 'family' },
//     { key: 'national_code', label: 'کد ملی', field: 'national_code' },
//     { key: 'mobile', label: 'شماره همراه', field: 'mobile' },
//   ],
//   fields: [
//     {
//       key: 'id_company', label: 'اسم شرکت', type: 'reference', required: true,
//       reference: {
//         path: '/transport-companies', valueKey: 'id_company', labelKey: 'company_name',
//       },
//     },
//     { key: 'name', label: 'اسم', required: true },
//     { key: 'family', label: 'فامیل', required: true },
//     { key: 'national_code', label: 'کد ملی', required: true },
//     { key: 'mobile', label: 'شماره همراه', required: true },
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
//     { key: 'name', label: 'نام طاق', field: 'name_tagh' },
//   ],
//   fields: [
//     { key: 'name_tagh', label: 'نام طاق', required: true },
//     { key: 'id_anbar', label: 'شناسه انبار', type: 'number' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }

// // ---- فهرست‌های کدینگ اختصاصی ----
// interface Term {
//   sys_term_id: number; category_id: number | null; key: string | null; value: string | null
//   parent_id: number | null; status: string | null; order_no: number | null; description: string | null
// }

// const TERM_CATEGORY = {
//   border: 1,
//   country: 2,
//   packagingType: 3,
// } as const

// function termResource(
//   route: string,
//   queryKey: string,
//   title: string,
//   entity: string,
//   valueLabel: string,
//   categoryId: number,
// ): CrudConfig<Term> {
//   return {
//     route,
//     path: '/terms',
//     queryKey,
//     title,
//     entity,
//     pkField: 'sys_term_id',
//     listFilter: { category_id: categoryId },
//     fixedValues: { category_id: categoryId },
//     columns: [
//       { key: 'value', label: valueLabel, field: 'value' },
//     ],
//     fields: [
//       { key: 'value', label: valueLabel, required: true },
//     ],
//   }
// }

// const borders = termResource(
//   '/borders', 'borders', 'مرزها', 'مرز', 'نام مرز', TERM_CATEGORY.border,
// )

// const countries = termResource(
//   '/countries', 'countries', 'کشورها', 'کشور', 'نام کشور', TERM_CATEGORY.country,
// )

// const packagingTypes = termResource(
//   '/packaging-types',
//   'packaging_types',
//   'نوع بسته‌بندی',
//   'نوع بسته‌بندی',
//   'عنوان نوع بسته‌بندی',
//   TERM_CATEGORY.packagingType,
// )

// // ---- دیماند ----
// interface KalaDiamound {
//   id_kala_diamound: number; code: string | null; title: string | null
//   price_gher_edari: string | null; price_holiday: string | null; description: string | null
// }
// const kalaDiamound: CrudConfig<KalaDiamound> = {
//   route: '/kala-diamound', path: '/kala-diamound', queryKey: 'kala_diamound',
//   title: 'دیماند', entity: 'ردیف', pkField: 'id_kala_diamound',
//   columns: [
//     { key: 'code', label: 'کد', field: 'code' },
//     { key: 'title', label: 'عنوان', field: 'title' },
//     { key: 'price_gher_edari', label: 'در ساعات غیر اداری', field: 'price_gher_edari' },
//     { key: 'price_holiday', label: 'در روزهای تعطیل', field: 'price_holiday' },
//   ],
//   fields: [
//     { key: 'code', label: 'کد' },
//     { key: 'title', label: 'عنوان' },
//     { key: 'price_gher_edari', label: 'در ساعات غیر اداری' },
//     { key: 'price_holiday', label: 'در روزهای تعطیل' },
//     { key: 'description', label: 'توضیحات' },
//   ],
// }

// // ---- سایر خدمات ----
// interface KalaOtherService {
//   id_kala_other_service: number; code: string | null; title: string | null
//   price: string | null; description: string | null
// }
// const kalaOtherService: CrudConfig<KalaOtherService> = {
//   route: '/kala-other-service', path: '/kala-other-service', queryKey: 'kala_other_service',
//   title: 'سایر خدمات', entity: 'ردیف', pkField: 'id_kala_other_service',
//   columns: [
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

// // ---- استریپ ----
// interface KalaStrip {
//   id_kala_strip: number; code: string | null; title: string | null
//   normal: string | null; non_standard: string | null; dangerous: string | null
//   description: string | null
// }
// const kalaStrip: CrudConfig<KalaStrip> = {
//   route: '/kala-strip', path: '/kala-strip', queryKey: 'kala_strip',
//   title: 'استریپ و استافینگ', entity: 'ردیف', pkField: 'id_kala_strip',
//   columns: [
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

// // ---- توقف شبانه ----
// interface KalaTimeStop {
//   id_kala_time_stop_vehicle: number; code: string | null; title: string | null
//   price: string | null; description: string | null
// }
// const kalaTimeStop: CrudConfig<KalaTimeStop> = {
//   route: '/kala-time-stop', path: '/kala-time-stop', queryKey: 'kala_time_stop',
//   title: 'توقف شبانه', entity: 'ردیف', pkField: 'id_kala_time_stop_vehicle',
//   columns: [
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

// // ---- ورود خودرو ----
// interface KalaVehicleEnter {
//   id_kala_vehicle_enter_price: number; code: string | null; title: string | null
//   price: string | null; description: string | null
// }
// const kalaVehicleEnter: CrudConfig<KalaVehicleEnter> = {
//   route: '/kala-vehicle-enter', path: '/kala-vehicle-enter', queryKey: 'kala_vehicle_enter',
//   title: 'ورود خودرو', entity: 'ردیف', pkField: 'id_kala_vehicle_enter_price',
//   columns: [
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
//   kala, anbar, owners, kalaPrice,
//   transportCompanies, companyRepresentatives, tagh, borders, countries, packagingTypes,
//   kalaDiamound, kalaOtherService, kalaStrip, kalaTimeStop, kalaVehicleEnter,
// ]


import type { CrudConfig } from './components/CrudResource'
import { useQuery } from '@tanstack/react-query'
import { apiGet } from './api/client'

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
// ---- صاحبین کالا (حقیقی / حقوقی) ----
interface Owner {
  id_owner: number; name: string | null; family: string | null
  national_code: string | null; type: 'حقیقی' | 'حقوقی'; company_name: string | null
  address: string | null; phone: string | null; national_id: string | null
  economic_code: string | null
}
const owners: CrudConfig<Owner> = {
  route: '/owners', path: '/owners', queryKey: 'owners',
  title: 'صاحبین کالا', entity: 'صاحب کالا', pkField: 'id_owner',
  columns: [
    { key: 'type', label: 'نوع', field: 'type' },
    {
      key: 'owner_name', label: 'نام صاحب کالا',
      render: (row) => row.type === 'حقوقی'
        ? row.company_name ?? ''
        : `${row.name ?? ''} ${row.family ?? ''}`.trim(),
    },
    {
      key: 'identifier', label: 'کد ملی / شناسه ملی',
      render: (row) => row.type === 'حقوقی' ? row.national_id ?? '' : row.national_code ?? '',
    },
    { key: 'phone', label: 'تلفن', field: 'phone' },
    { key: 'address', label: 'آدرس', field: 'address' },
  ],
  fields: [
    {
      key: 'type', label: 'نوع صاحب کالا', type: 'select', required: true,
      defaultValue: 'حقیقی',
      options: [
        { value: 'حقیقی', label: 'حقیقی' },
        { value: 'حقوقی', label: 'حقوقی' },
      ],
    },
    { key: 'name', label: 'نام', showWhen: { key: 'type', equals: 'حقیقی' }, required: true },
    { key: 'family', label: 'نام خانوادگی', showWhen: { key: 'type', equals: 'حقیقی' }, required: true },
    { key: 'national_code', label: 'کد ملی', showWhen: { key: 'type', equals: 'حقیقی' }, required: true },
    { key: 'company_name', label: 'نام شرکت', showWhen: { key: 'type', equals: 'حقوقی' }, required: true },
    { key: 'address', label: 'آدرس', required: true },
    { key: 'phone', label: 'تلفن', required: true },
    { key: 'national_id', label: 'شناسه ملی', showWhen: { key: 'type', equals: 'حقوقی' }, required: true },
    { key: 'economic_code', label: 'کد اقتصادی', showWhen: { key: 'type', equals: 'حقوقی' }, required: true },
  ],
}

// ---- قیمت کالا (lowercase table, mixed-case cols, FK id_kala, CODE required) ----
interface KalaPrice {
  id_kala_price: number; id_kala: number | null; code: string | null
  goods_group: string | null; storage_price: number | null
  price_30_day: number | null; price_60_day: number | null; price_90_day: number | null
  price_unloding: number | null; description: string | null
}
const kalaPrice: CrudConfig<KalaPrice> = {
  route: '/kala-price', path: '/kala-price', queryKey: 'kala_price',
  title: 'کد گروه کالا', entity: 'گروه کالا', pkField: 'id_kala_price',
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
    { key: 'description', label: 'توضیحات' },
  ],
}
// ---- شرکت حمل و نقل ----
interface TransportCompany {
  id_company: number; company_name: string; address: string
  phone: string; national_id: string; economic_code: string
}
const transportCompanies: CrudConfig<TransportCompany> = {
  route: '/transport-companies', path: '/transport-companies', queryKey: 'transport_companies',
  title: 'شرکت حمل و نقل', entity: 'شرکت حمل و نقل', pkField: 'id_company',
  columns: [
    { key: 'company_name', label: 'اسم شرکت', field: 'company_name' },
    { key: 'national_id', label: 'شناسه ملی', field: 'national_id' },
    { key: 'economic_code', label: 'کد اقتصادی', field: 'economic_code' },
    { key: 'phone', label: 'تلفن', field: 'phone' },
    { key: 'address', label: 'آدرس', field: 'address' },
  ],
  fields: [
    { key: 'company_name', label: 'اسم شرکت', required: true },
    { key: 'address', label: 'آدرس', required: true },
    { key: 'phone', label: 'تلفن', required: true },
    { key: 'national_id', label: 'شناسه ملی', required: true },
    { key: 'economic_code', label: 'کد اقتصادی', required: true },
  ],
}

interface CompanyRepresentative {
  id_repre_company: number; id_company: number; name: string
  family: string; national_code: string; mobile: string
}

function TransportCompanyName({ id }: { id: number }) {
  const { data } = useQuery({
    queryKey: ['transport-companies-for-labels'],
    queryFn: () => apiGet<TransportCompany[]>('/transport-companies'),
    staleTime: 5 * 60 * 1000,
  })
  return data?.find((row) => row.id_company === id)?.company_name ?? '—'
}

const companyRepresentatives: CrudConfig<CompanyRepresentative> = {
  route: '/company-representatives', path: '/company-representatives',
  queryKey: 'company_representatives', title: 'نمایندگان شرکت‌های حمل‌ونقل',
  entity: 'نماینده شرکت حمل‌ونقل', pkField: 'id_repre_company',
  columns: [
    { key: 'company', label: 'شرکت', render: (row) => <TransportCompanyName id={row.id_company} /> },
    { key: 'name', label: 'اسم', field: 'name' },
    { key: 'family', label: 'فامیل', field: 'family' },
    { key: 'national_code', label: 'کد ملی', field: 'national_code' },
    { key: 'mobile', label: 'شماره همراه', field: 'mobile' },
  ],
  fields: [
    {
      key: 'id_company', label: 'اسم شرکت', type: 'reference', required: true,
      reference: {
        path: '/transport-companies', valueKey: 'id_company', labelKey: 'company_name',
      },
    },
    { key: 'name', label: 'اسم', required: true },
    { key: 'family', label: 'فامیل', required: true },
    { key: 'national_code', label: 'کد ملی', required: true },
    { key: 'mobile', label: 'شماره همراه', required: true },
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

// ---- فهرست‌های کدینگ اختصاصی ----
interface Term {
  sys_term_id: number; category_id: number | null; key: string | null; value: string | null
  parent_id: number | null; status: string | null; order_no: number | null; description: string | null
}

const TERM_CATEGORY = {
  border: 1,
  country: 2,
  packagingType: 3,
} as const

function termResource(
  route: string,
  queryKey: string,
  title: string,
  entity: string,
  valueLabel: string,
  categoryId: number,
  emptyStateEntity?: string,
): CrudConfig<Term> {
  return {
    route,
    path: '/terms',
    queryKey,
    title,
    entity,
    emptyStateEntity,
    pkField: 'sys_term_id',
    listFilter: { category_id: categoryId },
    fixedValues: { category_id: categoryId },
    columns: [
      { key: 'value', label: valueLabel, field: 'value' },
    ],
    fields: [
      { key: 'value', label: valueLabel, required: true },
    ],
  }
}

const borders = termResource(
  '/borders', 'borders', 'مرزها', 'مرز', 'نام مرز', TERM_CATEGORY.border, 'مرزی',
)

const countries = termResource(
  '/countries', 'countries', 'کشورها', 'کشور', 'نام کشور', TERM_CATEGORY.country, 'کشوری',
)

const packagingTypes = termResource(
  '/packaging-types',
  'packaging_types',
  'نوع بسته‌بندی',
  'نوع بسته‌بندی',
  'عنوان نوع بسته‌بندی',
  TERM_CATEGORY.packagingType,
)

// ---- دیماند ----
interface KalaDiamound {
  id_kala_diamound: number; code: string | null; title: string | null
  price_gher_edari: string | null; price_holiday: string | null; description: string | null
}
const kalaDiamound: CrudConfig<KalaDiamound> = {
  route: '/kala-diamound', path: '/kala-diamound', queryKey: 'kala_diamound',
  title: 'دیماند', entity: 'ردیف', pkField: 'id_kala_diamound',
  columns: [
    { key: 'code', label: 'کد', field: 'code' },
    { key: 'title', label: 'عنوان', field: 'title' },
    { key: 'price_gher_edari', label: 'در ساعات غیر اداری', field: 'price_gher_edari' },
    { key: 'price_holiday', label: 'در روزهای تعطیل', field: 'price_holiday' },
  ],
  fields: [
    { key: 'code', label: 'کد' },
    { key: 'title', label: 'عنوان' },
    { key: 'price_gher_edari', label: 'در ساعات غیر اداری' },
    { key: 'price_holiday', label: 'در روزهای تعطیل' },
    { key: 'description', label: 'توضیحات' },
  ],
}

// ---- سایر خدمات ----
interface KalaOtherService {
  id_kala_other_service: number; code: string | null; title: string | null
  price: string | null; description: string | null
}
const kalaOtherService: CrudConfig<KalaOtherService> = {
  route: '/kala-other-service', path: '/kala-other-service', queryKey: 'kala_other_service',
  title: 'سایر خدمات', entity: 'ردیف', pkField: 'id_kala_other_service',
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

// ---- استریپ ----
interface KalaStrip {
  id_kala_strip: number; code: string | null; title: string | null
  normal: string | null; non_standard: string | null; dangerous: string | null
  description: string | null
}
const kalaStrip: CrudConfig<KalaStrip> = {
  route: '/kala-strip', path: '/kala-strip', queryKey: 'kala_strip',
  title: 'استریپ و استافینگ', entity: 'ردیف', pkField: 'id_kala_strip',
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

// ---- توقف شبانه ----
interface KalaTimeStop {
  id_kala_time_stop_vehicle: number; code: string | null; title: string | null
  price: string | null; description: string | null
}
const kalaTimeStop: CrudConfig<KalaTimeStop> = {
  route: '/kala-time-stop', path: '/kala-time-stop', queryKey: 'kala_time_stop',
  title: 'توقف شبانه', entity: 'ردیف', pkField: 'id_kala_time_stop_vehicle',
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

// ---- ورود خودرو ----
interface KalaVehicleEnter {
  id_kala_vehicle_enter_price: number; code: string | null; title: string | null
  price: string | null; description: string | null
}
const kalaVehicleEnter: CrudConfig<KalaVehicleEnter> = {
  route: '/kala-vehicle-enter', path: '/kala-vehicle-enter', queryKey: 'kala_vehicle_enter',
  title: 'ورود خودرو', entity: 'ردیف', pkField: 'id_kala_vehicle_enter_price',
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
  kala, anbar, owners, kalaPrice,
  transportCompanies, companyRepresentatives, tagh, borders, countries, packagingTypes,
  kalaDiamound, kalaOtherService, kalaStrip, kalaTimeStop, kalaVehicleEnter,
]
