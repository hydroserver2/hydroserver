<template>
  <v-row class="my-6" justify="center">
    <v-col
      v-for="(card, index) in cards"
      :key="index"
      :md="getColumnSpan(numCols)"
      cols="12"
      class="d-flex"
    >
      <v-card
        class="fill-height d-flex flex-column justify-space-between"
        style="width: 100%"
      >
        <v-card-text>
          <h5 class="text-h5 mb-4 d-flex align-center">
            <v-icon
              v-if="card.titleIcon"
              left
              color="grey-darken-1"
              class="mr-2"
            >
              {{ card.titleIcon }}
            </v-icon>
            {{ card.title }}
          </h5>
          <div>{{ card.text }}</div>
        </v-card-text>
        <v-card-actions class="justify-end">
          <v-btn
            variant="outlined"
            rounded="xl"
            :color="card.btnColor"
            :href="card.btnHref"
            :target="card.btnTarget"
          >
            {{ card.btnText }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
export interface Card {
  title: string
  titleIcon?: string
  text: string
  btnText: string
  btnColor: string
  btnHref?: string
  btnTarget?: string
  btnComponent?: string
}

const props = defineProps<{ cards: Card[]; numCols: number }>()

/**
 * Computes the column span based on the number of desired columns.
 * Ensures the number of columns is between 1 and 4.
 */
const getColumnSpan = (columns: number) =>
  12 / Math.min(Math.max(columns, 1), 4)
</script>
