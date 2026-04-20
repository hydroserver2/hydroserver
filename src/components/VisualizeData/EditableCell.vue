<template>
  <div
    class="editable-cell"
    :class="{
      'editable-cell--edited': edited,
      'editable-cell--end': align === 'end',
    }"
  >
    <div v-if="isEditing" class="editable-cell__edit" @mousedown.stop>
      <input
        ref="inputEl"
        class="editable-cell__input"
        :type="inputType"
        :value="draft"
        :step="inputType === 'number' ? 'any' : undefined"
        :style="{ textAlign: align }"
        @input="(e) => (draft = (e.target as HTMLInputElement).value)"
        @keydown.enter.prevent="commit"
        @keydown.escape.prevent="cancel"
      />
      <button
        type="button"
        class="editable-cell__btn editable-cell__btn--confirm"
        title="Confirm (Enter)"
        aria-label="Confirm edit"
        @mousedown.prevent
        @click="commit"
      >
        <v-icon icon="mdi-check" size="16" />
      </button>
      <button
        type="button"
        class="editable-cell__btn editable-cell__btn--cancel"
        title="Cancel (Esc)"
        aria-label="Cancel edit"
        @mousedown.prevent
        @click="cancel"
      >
        <v-icon icon="mdi-close" size="16" />
      </button>
    </div>
    <template v-else>
      <button
        type="button"
        class="editable-cell__display"
        :title="edited ? `Was: ${originalDisplay}. Click to edit again.` : 'Click to edit'"
        @click="startEditing"
      >
        <span v-if="edited" class="editable-cell__original">
          {{ originalDisplay }}
        </span>
        <span class="editable-cell__current">
          {{ edited ? editedDisplay : display }}
        </span>
      </button>
      <button
        v-if="edited"
        type="button"
        class="editable-cell__btn editable-cell__btn--revert"
        title="Revert staged edit"
        aria-label="Revert staged edit"
        @click.stop="$emit('clear')"
      >
        <v-icon icon="mdi-undo-variant" size="14" />
      </button>
    </template>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'

const props = defineProps<{
  value: string
  display: string
  edited: boolean
  originalDisplay: string
  editedDisplay: string
  inputType: 'number' | 'datetime-local'
  align?: 'start' | 'end'
}>()

const emit = defineEmits<{
  (e: 'save', raw: string): void
  (e: 'clear'): void
}>()

const isEditing = ref(false)
const draft = ref('')
const inputEl = ref<HTMLInputElement | null>(null)

async function startEditing() {
  draft.value = props.value
  isEditing.value = true
  await nextTick()
  inputEl.value?.focus()
  inputEl.value?.select?.()
}

function commit() {
  if (!isEditing.value) return
  isEditing.value = false
  if (draft.value !== props.value) emit('save', draft.value)
}

function cancel() {
  isEditing.value = false
}
</script>

<style scoped>
.editable-cell {
  display: flex;
  width: 100%;
  min-height: 28px;
  align-items: center;
  gap: 4px;
}

.editable-cell--end {
  justify-content: flex-end;
}

.editable-cell__display {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  border: 1px dashed transparent;
  border-radius: 4px;
  padding: 2px 6px;
  cursor: text;
  font: inherit;
  color: inherit;
  max-width: 100%;
}

.editable-cell__display:hover {
  border-color: rgba(var(--v-theme-primary), 0.45);
  background-color: rgba(var(--v-theme-primary), 0.06);
}

.editable-cell--edited .editable-cell__display {
  border: 1px solid rgb(var(--v-theme-warning));
  background-color: rgba(var(--v-theme-warning), 0.08);
}

.editable-cell__original {
  text-decoration: line-through;
  opacity: 0.55;
  font-size: 0.75rem;
}

.editable-cell__current {
  font-weight: 500;
}

.editable-cell--edited .editable-cell__current {
  color: rgb(var(--v-theme-warning-darken-1, var(--v-theme-warning)));
}

.editable-cell__edit {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  width: 100%;
}

.editable-cell__input {
  flex: 1 1 auto;
  min-width: 0;
  padding: 4px 6px;
  border: 1px solid rgb(var(--v-theme-primary));
  border-radius: 4px;
  outline: none;
  background-color: white;
  font: inherit;
}

.editable-cell__input:focus {
  box-shadow: 0 0 0 2px rgba(var(--v-theme-primary), 0.25);
}

.editable-cell__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 4px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  transition: background-color 120ms ease, border-color 120ms ease, color 120ms ease;
  flex: 0 0 auto;
}

.editable-cell__btn:hover {
  background-color: rgba(0, 0, 0, 0.06);
}

.editable-cell__btn--confirm {
  color: rgb(var(--v-theme-success, 76 175 80));
  border-color: rgba(var(--v-theme-success, 76 175 80), 0.4);
}

.editable-cell__btn--confirm:hover {
  background-color: rgba(var(--v-theme-success, 76 175 80), 0.12);
  border-color: rgb(var(--v-theme-success, 76 175 80));
}

.editable-cell__btn--cancel {
  color: rgb(var(--v-theme-error));
  border-color: rgba(var(--v-theme-error), 0.4);
}

.editable-cell__btn--cancel:hover {
  background-color: rgba(var(--v-theme-error), 0.12);
  border-color: rgb(var(--v-theme-error));
}

.editable-cell__btn--revert {
  color: rgb(var(--v-theme-warning));
  opacity: 0.85;
}

.editable-cell__btn--revert:hover {
  background-color: rgba(var(--v-theme-warning), 0.15);
  opacity: 1;
}
</style>
