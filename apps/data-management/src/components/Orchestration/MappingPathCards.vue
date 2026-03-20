<template>
  <v-card
    v-for="(p, pi) in mapping.paths"
    :key="pi"
    elevation="2"
    class="mb-4 mx-2"
  >
    <v-card-title class="py-2">
      <div class="d-flex align-center w-100">
        <div class="d-flex align-center">
          <v-icon :icon="mdiSignDirection" size="16" class="mr-2" />
          <span class="text-subtitle-2">Path {{ pi + 1 }}</span>
        </div>
        <v-spacer />
        <v-btn
          variant="text"
          size="small"
          color="error"
          :prepend-icon="mdiTrashCanOutline"
          @click="removePath(pi)"
        >
          Remove path
        </v-btn>
      </div>
    </v-card-title>

    <v-divider />

    <v-card-text class="pt-4">
      <v-row
        v-for="(t, ti) in p.dataTransformations"
        :key="ti"
        class="align-center mb-2"
      >
        <v-col cols="auto">
          <v-chip
            size="small"
            :color="t.type === 'expression' ? 'deep-purple' : 'teal'"
            variant="tonal"
          >
            <v-icon
              :icon="
                t.type === 'expression' ? mdiFunctionVariant : mdiTableSearch
              "
              size="14"
              class="mr-1"
            />

            <span v-if="t.type === 'expression'">expression</span>
            <span v-else>rating curve</span>
          </v-chip>
        </v-col>

        <v-col>
          <v-text-field
            v-if="t.type === 'expression'"
            v-model="t.expression"
            label="output ="
            placeholder="(x - 32) * 5/9"
            hide-details
          />

          <v-text-field
            v-else
            :model-value="getRatingCurveReference(t)"
            @update:model-value="setRatingCurveReference(t, String($event ?? ''))"
            placeholder="Rating curve URL"
            hide-details
          />
        </v-col>

        <v-col cols="auto">
          <v-btn
            variant="text"
            :prepend-icon="mdiTrashCanOutline"
            color="error"
            @click="removeTransform(p, ti)"
          >
            Remove transformation
          </v-btn>
        </v-col>
      </v-row>

      <v-row>
        <v-menu>
          <template #activator="{ props: act }">
            <v-btn
              v-bind="act"
              variant="tonal"
              color="primary"
              :prepend-icon="mdiPlus"
              class="mx-3 my-2"
            >
              Add transform
            </v-btn>
          </template>
          <v-list density="compact">
            <v-list-item @click="addExpression(p)">
              <v-list-item-title>
                <v-icon :icon="mdiFunctionVariant" size="16" class="mr-1" />
                Expression
              </v-list-item-title>
            </v-list-item>
            <v-list-item @click="addLookup(p)">
              <v-list-item-title>
                <v-icon :icon="mdiTableSearch" size="16" class="mr-1" />
                Rating curve
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </v-row>

      <v-row>
        <v-col cols="12" md="4">
          <DatastreamSelectAndDisplay
            button-name="Select target datastream"
            :datastream-id="String(p.targetIdentifier ?? '')"
            @update-selected-id="p.targetIdentifier = $event"
          />
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import DatastreamSelectAndDisplay from '@/components/Datastream/DatastreamSelectAndDisplay.vue'
import {
  MappingPath,
  ExpressionDataTransformation,
  Mapping,
} from '@hydroserver/client'
import {
  getRatingCurveReference,
  setRatingCurveReference,
} from '@/utils/orchestration/ratingCurve'
import {
  mdiFunctionVariant,
  mdiPlus,
  mdiSignDirection,
  mdiTableSearch,
  mdiTrashCanOutline,
} from '@mdi/js'

const mapping = defineModel<Mapping>('mapping', { required: true })

function addExpression(p: MappingPath) {
  const t: ExpressionDataTransformation = { type: 'expression', expression: '' }
  p.dataTransformations.push(t)
}

function addLookup(p: MappingPath) {
  const t: any = { type: 'rating_curve', ratingCurveUrl: '' }
  setRatingCurveReference(t, '')
  p.dataTransformations.push(t)
}

function removeTransform(p: MappingPath, tIndex: number) {
  p.dataTransformations.splice(tIndex, 1)
}

function removePath(pathIndex: number) {
  mapping.value.paths.splice(pathIndex, 1)
  if (!mapping.value.paths.length)
    mapping.value.paths.push({ targetIdentifier: '', dataTransformations: [] })
}
</script>
