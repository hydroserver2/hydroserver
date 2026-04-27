<template>
  <div class="d-flex align-center gap-1" v-bind="$attrs">
    <v-text-field
      ref="dateField"
      :model-value="dateInput"
      @blur="handleDateBlur"
      placeholder="MM/DD/YYYY"
      append-inner-icon="mdi-calendar-blank"
      @click:append-inner="showDateDialog = true"
      hide-details
      density="compact"
    />

    <v-text-field
      ref="timeField"
      :model-value="timeInput"
      @blur="handleTimeBlur"
      :placeholder="seconds ? 'HH:MM:SS' : 'HH:MM'"
      prepend-inner-icon="mdi-clock-outline"
      hide-details
      density="compact"
      :style="{ 'max-width': seconds ? '9rem' : '7rem' }"
    />
  </div>

  <v-dialog v-model="showDateDialog" max-width="20rem">
    <v-card class="date-picker-card">
      <div class="d-flex align-center px-4 py-2">
        <span class="text-subtitle-1 font-weight-medium">
          Select {{ placeholder }}
        </span>
        <v-spacer />
        <v-btn
          icon="mdi-close"
          variant="text"
          size="small"
          density="comfortable"
          @click="showDateDialog = false"
        />
      </div>
      <v-divider />
      <v-date-picker
        hide-header
        show-adjacent-months
        v-model="pickerDate"
        @update:modelValue="onDatePicked"
      />
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  modelValue: { type: Date, required: true },
  placeholder: String,
  /** When true, the time input shows HH:MM:SS instead of HH:MM and the
   *  emitted Date carries the seconds component too. */
  seconds: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

// --- Mask shape -------------------------------------------------------------
// Each input is a fixed-width string. Separator positions hold the literal
// `/` or `:`; digit positions hold `0`-`9` or `_` for "not yet typed". Tight
// in-house mask logic — replaces maska, whose eager-mode reformat passes
// fought the segment-aware caret behaviour we want.
type Segment = readonly [number, number]

interface MaskShape {
  empty: string
  segments: readonly Segment[]
  seps: ReadonlySet<number>
}

const DATE: MaskShape = {
  empty: '__/__/____',
  segments: [
    [0, 2], // MM
    [3, 5], // DD
    [6, 10], // YYYY
  ],
  seps: new Set([2, 5]),
}

const TIME: MaskShape = {
  empty: '__:__',
  segments: [
    [0, 2], // HH
    [3, 5], // MM
  ],
  seps: new Set([2]),
}

const TIME_WITH_SECONDS: MaskShape = {
  empty: '__:__:__',
  segments: [
    [0, 2], // HH
    [3, 5], // MM
    [6, 8], // SS
  ],
  seps: new Set([2, 5]),
}

const timeShape = (): MaskShape => (props.seconds ? TIME_WITH_SECONDS : TIME)

// --- Format helpers ---------------------------------------------------------
const formatDateStr = (date: Date) => {
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${m}/${d}/${date.getFullYear()}`
}

const formatTimeStr = (date: Date) => {
  const h = String(date.getHours()).padStart(2, '0')
  const m = String(date.getMinutes()).padStart(2, '0')
  if (!props.seconds) return `${h}:${m}`
  const s = String(date.getSeconds()).padStart(2, '0')
  return `${h}:${m}:${s}`
}

const toMidnight = (date: Date) => {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  return d
}

// --- v-model bridge ---------------------------------------------------------
const showDateDialog = ref(false)

const dateInput = ref(formatDateStr(props.modelValue))
const timeInput = ref(formatTimeStr(props.modelValue))
const pickerDate = ref<Date>(toMidnight(props.modelValue))

watch(
  () => props.modelValue,
  (newValue) => {
    dateInput.value = formatDateStr(newValue)
    timeInput.value = formatTimeStr(newValue)
    pickerDate.value = toMidnight(newValue)
  }
)

const emitCombined = (date: Date, time: string) => {
  const parts = time.split(':').map(Number)
  const h = parts[0] || 0
  const m = parts[1] || 0
  const s = props.seconds ? (parts[2] || 0) : 0
  const result = new Date(date)
  result.setHours(h, m, s, 0)
  emit('update:modelValue', result)
}

const onDatePicked = (date: Date) => {
  pickerDate.value = toMidnight(date)
  dateInput.value = formatDateStr(date)
  emitCombined(pickerDate.value, timeInput.value)
  showDateDialog.value = false
}

const handleDateBlur = () => {
  const match = dateInput.value.match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
  if (match) {
    const m = Math.max(1, Math.min(12, +match[1]!))
    const d = Math.max(1, Math.min(31, +match[2]!))
    const parsed = new Date(+match[3]!, m - 1, d)
    if (!isNaN(parsed.getTime())) {
      pickerDate.value = toMidnight(parsed)
      dateInput.value = formatDateStr(parsed)
      emitCombined(pickerDate.value, timeInput.value)
      return
    }
  }
  // Anything not a complete date snaps back to the picker's last good value.
  dateInput.value = formatDateStr(pickerDate.value)
}

const handleTimeBlur = () => {
  const re = props.seconds
    ? /^(\d{2}):(\d{2}):(\d{2})$/
    : /^(\d{2}):(\d{2})$/
  const match = timeInput.value.match(re)
  if (match) {
    const h = Math.max(0, Math.min(23, +match[1]!))
    const m = Math.max(0, Math.min(59, +match[2]!))
    const s = props.seconds ? Math.max(0, Math.min(59, +match[3]!)) : 0
    const pad = (n: number) => String(n).padStart(2, '0')
    const time = props.seconds
      ? `${pad(h)}:${pad(m)}:${pad(s)}`
      : `${pad(h)}:${pad(m)}`
    timeInput.value = time
    emitCombined(pickerDate.value, time)
    return
  }
  timeInput.value = formatTimeStr(props.modelValue)
}

// --- Mask engine ------------------------------------------------------------
// Pure helpers. Each takes a value + position, returns a new value + caret.
const segmentAt = (segments: readonly Segment[], pos: number): number => {
  for (let i = 0; i < segments.length; i++) {
    if (pos >= segments[i]![0] && pos <= segments[i]![1]) return i
  }
  return segments.length - 1
}

const isSegmentFilled = (value: string, seg: Segment): boolean => {
  const part = value.slice(seg[0], seg[1])
  return /^\d+$/.test(part) && part.length === seg[1] - seg[0]
}

const skipForwardSep = (pos: number, seps: ReadonlySet<number>): number =>
  seps.has(pos) ? pos + 1 : pos

const skipBackwardSep = (pos: number, seps: ReadonlySet<number>): number =>
  seps.has(pos - 1) ? pos - 1 : pos

const writeDigitAt = (
  value: string,
  pos: number,
  digit: string,
  shape: MaskShape
): { value: string; caret: number } => {
  const p = Math.min(skipForwardSep(pos, shape.seps), shape.empty.length - 1)
  if (shape.seps.has(p)) return { value, caret: p }
  const next = value.slice(0, p) + digit + value.slice(p + 1)
  return { value: next, caret: skipForwardSep(p + 1, shape.seps) }
}

const blankRange = (
  value: string,
  start: number,
  end: number,
  shape: MaskShape
): string => {
  // Replace digit slots in [start, end) with '_'; keep separators intact.
  const chars = value.split('')
  for (let i = start; i < end; i++) {
    if (!shape.seps.has(i)) chars[i] = '_'
  }
  return chars.join('')
}

// --- Per-input controller ---------------------------------------------------
type InputCtl = {
  inputRef: { value: { $el: HTMLElement } | null }
  modelRef: { value: string }
  shape: MaskShape
}

const makeController = (ctl: InputCtl) => {
  let pendingSelection: [number, number] | null = null

  const getInput = (): HTMLInputElement | null =>
    (ctl.inputRef.value?.$el?.querySelector(
      'input'
    ) as HTMLInputElement | null) ?? null

  const setValueAndSelection = async (
    value: string,
    selection: [number, number]
  ) => {
    ctl.modelRef.value = value
    pendingSelection = selection
    await nextTick()
    const input = getInput()
    if (input && document.activeElement === input && pendingSelection) {
      input.setSelectionRange(pendingSelection[0], pendingSelection[1])
      pendingSelection = null
    }
  }

  const onFocus = () => {
    const input = getInput()
    if (!input) return
    requestAnimationFrame(() => {
      if (document.activeElement !== input) return
      const idx = segmentAt(ctl.shape.segments, input.selectionStart ?? 0)
      const seg = ctl.shape.segments[idx]
      input.setSelectionRange(seg[0], seg[1])
    })
  }

  const onClick = () => {
    const input = getInput()
    if (!input) return
    requestAnimationFrame(() => {
      const idx = segmentAt(ctl.shape.segments, input.selectionStart ?? 0)
      const seg = ctl.shape.segments[idx]
      input.setSelectionRange(seg[0], seg[1])
    })
  }

  const onBeforeInput = (ev: Event) => {
    const e = ev as InputEvent
    const input = getInput()
    if (!input) return
    const value = ctl.modelRef.value || ctl.shape.empty
    const start = input.selectionStart ?? 0
    const end = input.selectionEnd ?? start

    if (e.inputType === 'insertText') {
      const data = e.data ?? ''
      // Only digits make it through — anything else is rejected.
      if (!/^\d$/.test(data)) {
        e.preventDefault()
        return
      }
      e.preventDefault()
      // If the user has a range selected (via our own segment selection
      // or a manual highlight), wipe that range to '_' first so the
      // digit lands on a clean slot rather than in the middle of an
      // otherwise-overwriting selection.
      const base =
        end > start ? blankRange(value, start, end, ctl.shape) : value
      const target = end > start ? start : start
      const { value: nextVal, caret } = writeDigitAt(
        base,
        target,
        data,
        ctl.shape
      )
      // Auto-advance when the segment that just received the digit is
      // now fully filled. Otherwise leave the caret where it landed.
      const segIdx = segmentAt(ctl.shape.segments, target)
      const seg = ctl.shape.segments[segIdx]
      const segNowFull = isSegmentFilled(nextVal, seg)
      const nextSeg =
        segNowFull && segIdx + 1 < ctl.shape.segments.length
          ? ctl.shape.segments[segIdx + 1]
          : null
      void setValueAndSelection(
        nextVal,
        nextSeg ? [nextSeg[0], nextSeg[1]] : [caret, caret]
      )
      return
    }

    if (
      e.inputType === 'deleteContentBackward' ||
      e.inputType === 'deleteContentForward' ||
      e.inputType === 'deleteByCut'
    ) {
      e.preventDefault()
      if (end > start) {
        // Range delete — blank the digits in the range, leave caret at start.
        const next = blankRange(value, start, end, ctl.shape)
        void setValueAndSelection(next, [start, start])
        return
      }
      if (e.inputType === 'deleteContentBackward') {
        const target = skipBackwardSep(start, ctl.shape.seps)
        if (target === 0) return
        const slot = target - 1
        const next = blankRange(value, slot, slot + 1, ctl.shape)
        void setValueAndSelection(next, [slot, slot])
        return
      }
      // deleteContentForward / cut: blank slot at caret.
      const slot = skipForwardSep(start, ctl.shape.seps)
      if (slot >= ctl.shape.empty.length) return
      const next = blankRange(value, slot, slot + 1, ctl.shape)
      void setValueAndSelection(next, [start, start])
      return
    }

    // Anything else (paste, drag-drop, IME composition) — block.
    // Pasting a full date could be wired up later; for now keep the
    // rule "only digit keys mutate the value".
    e.preventDefault()
  }

  const onKeydown = (ev: KeyboardEvent) => {
    const input = getInput()
    if (!input) return
    if (ev.key === 'ArrowLeft' || ev.key === 'ArrowRight') {
      const pos = input.selectionStart ?? 0
      const idx = segmentAt(ctl.shape.segments, pos)
      const next = ev.key === 'ArrowRight' ? idx + 1 : idx - 1
      if (next < 0 || next >= ctl.shape.segments.length) return
      ev.preventDefault()
      const seg = ctl.shape.segments[next]
      input.setSelectionRange(seg[0], seg[1])
    }
  }

  return { onFocus, onClick, onBeforeInput, onKeydown }
}

// --- Wiring -----------------------------------------------------------------
const dateField = ref<{ $el: HTMLElement } | null>(null)
const timeField = ref<{ $el: HTMLElement } | null>(null)

let cleanupFns: Array<() => void> = []

const attach = (
  fieldRef: { value: { $el: HTMLElement } | null },
  modelRef: { value: string },
  shape: MaskShape
) => {
  const input = fieldRef.value?.$el?.querySelector(
    'input'
  ) as HTMLInputElement | null
  if (!input) return
  const ctl = makeController({ inputRef: fieldRef, modelRef, shape })
  input.addEventListener('focus', ctl.onFocus)
  input.addEventListener('click', ctl.onClick)
  input.addEventListener('beforeinput', ctl.onBeforeInput)
  input.addEventListener('keydown', ctl.onKeydown)
  cleanupFns.push(() => {
    input.removeEventListener('focus', ctl.onFocus)
    input.removeEventListener('click', ctl.onClick)
    input.removeEventListener('beforeinput', ctl.onBeforeInput)
    input.removeEventListener('keydown', ctl.onKeydown)
  })
}

onMounted(() => {
  attach(dateField, dateInput, DATE)
  attach(timeField, timeInput, timeShape())
})

onBeforeUnmount(() => {
  for (const fn of cleanupFns) fn()
  cleanupFns = []
})
</script>

<style scoped>
.date-picker-card :deep(.v-date-picker-controls) {
  justify-content: center;
  gap: 0.25rem;
  height: 48px;
  padding: 4px 8px;
}

.date-picker-card :deep(.v-date-picker-controls__month),
.date-picker-card :deep(.v-date-picker-controls__year) {
  align-items: center;
}

.date-picker-card :deep(.v-date-picker-controls__month-btn),
.date-picker-card :deep(.v-date-picker-controls__year-btn) {
  font-weight: 600;
  padding: 0 8px;
}

.date-picker-card :deep(.v-picker) {
  box-shadow: none;
}

.date-picker-card :deep(.v-date-picker-month) {
  padding: 0 8px 8px;
}
</style>
