// import type { JunctionConfig } from './TallyJunctionSection'

// // All rate junctions, described as data. The detail page maps this to sections.
// // Most catalogs have code + title; fa_kala_price has no title, uses description.
// export const tallyJunctions: JunctionConfig[] = [
//   {
//     key: 'diamound', title: 'دیماند در ساعات غیراداری',
//     apiPath: '/tali-kala-diamound', readPath: 'diamound', linkKey: 'kala_diamound_id',
//     catalogPath: '/kala-diamound', catalogValueKey: 'id_kala_diamound',
//     catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
//   },
//   {
//     key: 'strip', title: 'استریپ و استافینگ',
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
//   {
//     key: 'dangerous', title: 'نرخ کالای خطرناک',
//     apiPath: '/tali-kala-dangerous', readPath: 'dangerous', linkKey: 'kala_dangerous_id',
//     catalogPath: '/kala-dangerous', catalogValueKey: 'id_kala_dangerous',
//     catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
//   },
// ]

import type { JunctionConfig } from './TallyJunctionSection'

// All rate junctions, described as data. The detail page maps this to sections.
// Most catalogs have code + title; fa_kala_price has no title, uses description.
export const tallyJunctions: JunctionConfig[] = [
  {
    key: 'diamound', title: 'دیماند در ساعات غیراداری',
    apiPath: '/tali-kala-diamound', readPath: 'diamound', linkKey: 'kala_diamound_id',
    catalogPath: '/kala-diamound', catalogValueKey: 'id_kala_diamound',
    catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
  },
  {
    key: 'strip', title: 'استریپ و استافینگ',
    apiPath: '/tali-kala-strip', readPath: 'strip', linkKey: 'kala_strip_id',
    catalogPath: '/kala-strip', catalogValueKey: 'id_kala_strip',
    catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
    selectField: {
      key: 'pricing_type', label: 'نوع قیمت', defaultValue: 'normal',
      options: [
        { value: 'normal', label: 'عادی' },
        { value: 'non_standard', label: 'غیراستاندارد' },
        { value: 'dangerous', label: 'خطرناک' },
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
  },
  {
    key: 'vehicle-enter', title: 'ورودی / حق محوطه',
    apiPath: '/tali-kala-vehicle-enter', readPath: 'vehicle-enter', linkKey: 'kala_vehicle_enter_price_id',
    catalogPath: '/kala-vehicle-enter', catalogValueKey: 'id_kala_vehicle_enter_price',
    catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
  },
  {
    key: 'dangerous', title: 'نرخ کالای خطرناک',
    apiPath: '/tali-kala-dangerous', readPath: 'dangerous', linkKey: 'kala_dangerous_id',
    catalogPath: '/kala-dangerous', catalogValueKey: 'id_kala_dangerous',
    catalogLabel: (r) => `${r.code ?? ''} ${r.title ? `(${r.title})` : ''}`.trim(),
  },
]