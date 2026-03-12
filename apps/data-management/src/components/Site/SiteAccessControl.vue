<template>
  <v-card>
    <v-toolbar color="primary-darken-5">
      <v-card-title>Site access control</v-card-title>
    </v-toolbar>

    <v-card-text>
      <v-row>
        <v-col cols="auto" class="pb-0">
          <h6 class="text-h6 mt-4" v-if="thing">
            Toggle Site Privacy
            <v-icon
              @click="showPrivacyHelp = !showPrivacyHelp"
              color="grey"
              small
              :icon="mdiHelpCircleOutline"
            />
          </h6>
        </v-col>
      </v-row>

      <p cols="12" md="6" v-if="showPrivacyHelp" class="py-5">
        Setting your site to private will make it and all related datastreams
        and workspace metadata visible to only you and other collaborators of
        your workspace. Setting your site to public will make it visible to all
        users and guests of the system. By default, all related datastreams will
        also be public, but can be made private from on the Site Details page.
      </p>

      <v-row v-if="thing">
        <v-col cols="auto" class="py-0">
          <v-checkbox
            v-model="thing.isPrivate"
            label="Make site private"
            color="primary"
            hide-details
            @change="toggleSitePrivacy"
          />
        </v-col>
      </v-row>
    </v-card-text>

    <v-divider />

    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn-cancel @click="emitClose">Close</v-btn-cancel>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { useThingStore } from '@/store/thing'
import { storeToRefs } from 'pinia'
import { ref } from 'vue'
import hs from '@hydroserver/client'
import { mdiHelpCircleOutline } from '@mdi/js'

const emits = defineEmits(['close'])
const props = defineProps<{
  thingId: string
}>()

const { thing } = storeToRefs(useThingStore())
const showPrivacyHelp = ref(false)

const isUpdating = ref(false)

async function toggleSitePrivacy() {
  try {
    isUpdating.value = true

    const res = await hs.things.updatePrivacy(
      props.thingId,
      thing.value!.isPrivate
    )
    thing.value = res.data
  } catch (error) {
    console.error('Error updating thing privacy', error)
  } finally {
    isUpdating.value = false
  }
}

const emitClose = () => emits('close')
</script>
