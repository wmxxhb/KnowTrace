<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path v-for="(path, index) in (paths[name] || paths.chat)" :key="index" :d="path" />
  </svg>
</template>
<script setup>
defineProps({ name: String, size: { type: [Number, String], default: 20 } })
const paths = {
  trash: ['M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7'],
  edit: ['m16 3 5 5-12 12-5 1 1-5L17 2l5 5'],
  upload: ['M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6'],
  download: ['M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4'],
  back: ['M20 12H4m6-6-6 6 6 6'],
  refresh: ['M20 7v5h-5M4 17v-5h5', 'M6 6a8 8 0 0 1 13 1l1 5M4 12l1 5a8 8 0 0 0 13 1'],
  check: ['m5 12 4 4L19 6'],
  panel: ['M4 3h16a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z', 'M9 3v18'],
  compose: ['M12 4H5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2v-7', 'm16 3 5 5-10 10-5 1 1-5L17 2l5 5'],
  chat: ['M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7A8.4 8.4 0 0 1 4 11.5a8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5Z'],
  folder: ['M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z'],
  assistant: ['M12 3v3', 'M10 3h4', 'M5 7h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Z', 'M8 12h.01M16 12h.01M9 17h6'],
  layers: ['m12 3 10 5-10 5L2 8l10-5Z', 'm2 12 10 5 10-5M2 16l10 5 10-5'],
  chart: ['M4 3v18h17', 'M8 16v-4M13 16V8M18 16V5'],
  activity: ['M2 12h5l3-8 4 16 3-8h5'],
  sun: ['M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z', 'M12 2v2M12 20v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4'],
  moon: ['M21 12.8A9 9 0 0 1 11.2 3 9 9 0 1 0 21 12.8Z'],
  monitor: ['M4 3h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z', 'M12 17v4M8 21h8'],
  chevron: ['m9 5 7 7-7 7'],
  down: ['m6 9 6 6 6-6'],
  plus: ['M12 5v14M5 12h14'],
  arrow: ['M12 19V5m-6 6 6-6 6 6'],
  settings: ['M4 7h16M4 17h16', 'M8 4v6M16 14v6'],
  close: ['m6 6 12 12M6 18 18 6'],
  search: ['M10.5 3a7.5 7.5 0 1 0 0 15 7.5 7.5 0 0 0 0-15Z', 'm16 16 5 5'],
  file: ['M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z', 'M14 2v6h6M8 13h8M8 17h5'],
  more: ['M5 12h.01M12 12h.01M19 12h.01'],
}
</script>
