// import type { JunctionConfig } from './TallyJunctionSection'

// // All rate junctions, described as data. The detail page maps this to sections.
// // Most catalogs have code + title; fa_kala_price has no title, uses description.
// export const tallyJunctions: JunctionConfig[] = [
//   {
//     key: 'diamound', title: 'دیماند',
//     apiPath: '/tali-kala-diamound', readPath: 'diamound', linkKey: 'kala_diamound_id',
//     catalogPath: '/kala-diamound', catalogValueKey: 'id_kala_diamound',
//     catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
//   },
//   {
//     key: 'strip', title: 'استریپ یا استافینگ',
//     apiPath: '/tali-kala-strip', readPath: 'strip', linkKey: 'kala_strip_id',
//     catalogPath: '/kala-strip', catalogValueKey: 'id_kala_strip',
//     catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
//   },
//   {
//     key: 'other-service', title: 'سایر خدمات',
//     apiPath: '/tali-kala-other-service', readPath: 'other-service', linkKey: 'kala_other_service_id',
//     catalogPath: '/kala-other-service', catalogValueKey: 'id_kala_other_service',
//     catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
//     extraField: { key: 'number_service', label: 'تعداد' },
//   },
//   {
//     key: 'time-stop', title: 'توقف شبانه حامل‌های خالی',
//     apiPath: '/tali-kala-time-stop', readPath: 'time-stop', linkKey: 'kala_time_stop_vehicle_id',
//     catalogPath: '/kala-time-stop', catalogValueKey: 'id_kala_time_stop_vehicle',
//     catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
//   },
//   {
//     key: 'vehicle-enter', title: 'ورودی / حق محوطه',
//     apiPath: '/tali-kala-vehicle-enter', readPath: 'vehicle-enter', linkKey: 'kala_vehicle_enter_price_id',
//     catalogPath: '/kala-vehicle-enter', catalogValueKey: 'id_kala_vehicle_enter_price',
//     catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
//   },
// ]

import type { JunctionConfig } from './TallyJunctionSection'

// All rate junctions, described as data. The detail page maps this to sections.
// Most catalogs have code + title; fa_kala_price has no title, uses description.
export const tallyJunctions: JunctionConfig[] = [
  {
    key: 'diamound', title: 'دیماند',
    apiPath: '/tali-kala-diamound', readPath: 'diamound', linkKey: 'kala_diamound_id',
    catalogPath: '/kala-diamound', catalogValueKey: 'id_kala_diamound',
    catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
    extraField: { key: 'number_service', label: 'تعداد' },
    selectField: {
      key: 'pricing_type', label: 'زمان اعمال', defaultValue: 'off_hours',
      inlineWithCatalog: true,
      options: [
        {
          value: 'off_hours',
          label: 'در ساعات غیر اداری',
          catalogField: 'price_gher_edari',
        },
        {
          value: 'holiday',
          label: 'در روزهای تعطیل',
          catalogField: 'price_holiday',
        },
      ],
    },
  },
  {
    key: 'strip', title: 'استریپ / تخلیه', serviceKind: 'strip',
    apiPath: '/tali-kala-strip', readPath: 'strip', linkKey: 'kala_strip_id',
    catalogPath: '/kala-strip', catalogValueKey: 'id_kala_strip',
    catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
    extraField: { key: 'number_service', label: 'تعداد' },
    carrierField: { key: 'number_hamel', label: 'شماره حامل' },
    selectField: {
      key: 'pricing_type', label: 'نوع قیمت', defaultValue: 'normal',
      options: [
        { value: 'normal', label: 'عادی' },
        { value: 'non_standard', label: 'غیراستاندارد' },
        { value: 'dangerous', label: 'خطرناک' },
        { value: 'unloading', label: 'تخلیه' },
      ],
    },
  },
  {
    key: 'stuffing', title: 'استافینگ / بارگیری', serviceKind: 'stuffing',
    apiPath: '/tali-kala-strip', readPath: 'stuffing', linkKey: 'kala_strip_id',
    catalogPath: '/kala-strip', catalogValueKey: 'id_kala_strip',
    catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
    extraField: { key: 'number_service', label: 'تعداد' },
    carrierField: { key: 'number_hamel', label: 'شماره حامل' },
    selectField: {
      key: 'pricing_type', label: 'نوع قیمت', defaultValue: 'normal',
      options: [
        { value: 'normal', label: 'عادی' },
        { value: 'non_standard', label: 'غیراستاندارد' },
        { value: 'dangerous', label: 'خطرناک' },
        { value: 'loading', label: 'بارگیری' },
      ],
    },
  },
  {
    key: 'other-service', title: 'سایر خدمات',
    apiPath: '/tali-kala-other-service', readPath: 'other-service', linkKey: 'kala_other_service_id',
    catalogPath: '/kala-other-service', catalogValueKey: 'id_kala_other_service',
    catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
    extraField: { key: 'number_service', label: 'تعداد' },
  },
  {
    key: 'time-stop', title: 'توقف شبانه حامل‌های خالی',
    apiPath: '/tali-kala-time-stop', readPath: 'time-stop', linkKey: 'kala_time_stop_vehicle_id',
    catalogPath: '/kala-time-stop', catalogValueKey: 'id_kala_time_stop_vehicle',
    catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
    extraField: { key: 'number_service', label: 'تعداد' },
  },
  {
    key: 'vehicle-enter', title: 'ورودی / حق محوطه',
    apiPath: '/tali-kala-vehicle-enter', readPath: 'vehicle-enter', linkKey: 'kala_vehicle_enter_price_id',
    catalogPath: '/kala-vehicle-enter', catalogValueKey: 'id_kala_vehicle_enter_price',
    catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
    extraField: { key: 'number_service', label: 'تعداد' },
  },
]
