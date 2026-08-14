<template>
  <v-container class="max-w-[64rem]">
    <h4 class="hs-text-lg mt-6 mb-2">Streaming Data Loader</h4>
    <p class="hs-text-sm text-medium-emphasis mb-4 max-w-[46rem]">
      A simple alternative to the main HydroServer orchestration system — it
      reads CSV files on your laptop and streams updates as those updates
      happen.
    </p>

    <div class="flex flex-wrap items-center gap-2 mb-6">
      <v-chip
        v-if="release"
        size="small"
        color="primary"
        variant="tonal"
        :prepend-icon="mdiTagOutline"
      >
        {{ release.tag_name }}
      </v-chip>
      <span v-if="formattedReleaseDate" class="hs-text-2xs text-medium-emphasis">
        Released {{ formattedReleaseDate }}
      </span>
      <a
        class="hs-text-2xs text-primary d-inline-flex align-center text-decoration-none"
        :href="releasesUrl"
        target="_blank"
        rel="noopener noreferrer"
      >
        View all releases
        <v-icon :icon="mdiOpenInNew" size="12" class="ml-1" />
      </a>
    </div>

    <v-alert
      v-if="loadError"
      type="warning"
      variant="tonal"
      density="comfortable"
      class="mb-6"
    >
      Couldn't check GitHub for the latest build, so these buttons open the
      release page instead.
      <template #append>
        <v-btn
          size="small"
          variant="text"
          class="text-none"
          @click="loadLatestRelease"
        >
          Retry
        </v-btn>
      </template>
    </v-alert>

    <v-row justify="center">
      <v-col
        v-for="platform in platforms"
        :key="platform.id"
        cols="12"
        md="4"
        class="d-flex"
      >
        <v-card
          class="fill-height d-flex flex-column justify-space-between"
          style="width: 100%"
        >
          <v-card-text>
            <h5 class="hs-text-md mb-2 d-flex align-center">
              <v-icon
                :icon="platform.icon"
                :color="platform.iconColor"
                class="mr-2"
              />
              {{ platform.name }}
            </h5>
            <div class="hs-text-sm text-medium-emphasis">
              {{ platform.requirement }}
            </div>
          </v-card-text>
          <v-card-actions class="flex-column align-stretch px-4 pb-4">
            <v-btn
              block
              variant="elevated"
              :loading="loadingRelease"
              :href="platform.href"
              :prepend-icon="mdiTrayArrowDown"
            >
              Download for {{ platform.short }}
            </v-btn>
            <span class="hs-text-2xs text-medium-emphasis text-center mt-2">
              {{
                platform.assetName
                  ? `${platform.assetName} · ${platform.assetSize}`
                  : 'Opens the release page'
              }}
            </span>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-text>
            <h5 class="hs-text-md mb-3">Guides</h5>
            <div class="flex flex-col">
              <a
                class="flex items-center gap-2 py-2 hs-text-sm text-primary text-decoration-none border-b border-black/10"
                :href="installGuideUrl"
                target="_blank"
                rel="noopener noreferrer"
              >
                <v-icon :icon="mdiBookOpenVariant" size="18" />
                Installation instructions
              </a>
              <a
                class="flex items-center gap-2 py-2 hs-text-sm text-primary text-decoration-none border-b border-black/10"
                :href="usageGuideUrl"
                target="_blank"
                rel="noopener noreferrer"
              >
                <v-icon :icon="mdiFileDocumentOutline" size="18" />
                How to use the Streaming Data Loader
              </a>
              <a
                class="flex items-center gap-2 py-2 hs-text-sm text-primary text-decoration-none"
                :href="repoUrl"
                target="_blank"
                rel="noopener noreferrer"
              >
                <v-icon :icon="mdiGithub" size="18" />
                Source code &amp; issue tracker
              </a>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  mdiApple,
  mdiMicrosoftWindows,
  mdiLinux,
  mdiTrayArrowDown,
  mdiTagOutline,
  mdiOpenInNew,
  mdiBookOpenVariant,
  mdiFileDocumentOutline,
  mdiGithub,
} from '@mdi/js'

const REPO = 'hydroserver2/streaming-data-loader'
const DOCS_BASE = 'https://hydroserver2.github.io/hydroserver'
const CACHE_KEY = 'sdl-latest-release'
const CACHE_TTL_MS = 60 * 60 * 1000 // 1 hour

const releasesUrl = `https://github.com/${REPO}/releases`
const repoUrl = `https://github.com/${REPO}`
const installGuideUrl = `${DOCS_BASE}/references/streaming-data-loader.html`
const usageGuideUrl = `${DOCS_BASE}/user-guides/how-to/using-streaming-data-loader.html`

interface GitHubAsset {
  name: string
  size: number
  browser_download_url: string
}
interface GitHubRelease {
  tag_name: string
  published_at: string
  assets: GitHubAsset[]
}

const release = ref<GitHubRelease | null>(null)
const loadingRelease = ref(true)
const loadError = ref(false)

interface PlatformDef {
  id: string
  name: string
  short: string
  requirement: string
  icon: string
  iconColor: string
  match: RegExp[]
}

// Rather than hardcoding a version + exact asset filenames (which drifts
// stale every release, as the old page's dead links showed), match assets
// from whatever the latest GitHub release actually contains.
const platformDefs: PlatformDef[] = [
  {
    id: 'macos',
    name: 'macOS',
    short: 'macOS',
    requirement: 'macOS 11 (Big Sur) or later, Intel or Apple Silicon',
    icon: mdiApple,
    iconColor: 'grey-darken-1',
    match: [/mac/i, /\.dmg$/i],
  },
  {
    id: 'windows',
    name: 'Windows',
    short: 'Windows',
    requirement: 'Windows 10 or later, 64-bit',
    icon: mdiMicrosoftWindows,
    iconColor: 'grey-darken-1',
    match: [/win/i, /\.exe$/i],
  },
  {
    id: 'linux',
    name: 'Linux',
    short: 'Linux',
    requirement: 'Most 64-bit distributions (AppImage)',
    icon: mdiLinux,
    iconColor: 'grey-darken-1',
    match: [/linux/i, /ubuntu/i, /appimage/i],
  },
]

function findAsset(assets: GitHubAsset[], matchers: RegExp[]) {
  return assets.find((asset) => matchers.some((re) => re.test(asset.name)))
}

function formatBytes(bytes: number) {
  if (!bytes) return ''
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const formattedReleaseDate = computed(() => {
  if (!release.value?.published_at) return ''
  return new Date(release.value.published_at).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
})

const platforms = computed(() =>
  platformDefs.map((def) => {
    const asset = release.value
      ? findAsset(release.value.assets, def.match)
      : undefined
    return {
      ...def,
      // Always safe to click: falls back to the releases page whenever we
      // don't yet have (or couldn't find) a specific asset link.
      href: asset?.browser_download_url ?? releasesUrl,
      assetName: asset?.name,
      assetSize: asset ? formatBytes(asset.size) : undefined,
    }
  })
)

function readCache(): GitHubRelease | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const { data, cachedAt } = JSON.parse(raw)
    if (Date.now() - cachedAt > CACHE_TTL_MS) return null
    return data
  } catch {
    return null
  }
}

function writeCache(data: GitHubRelease) {
  try {
    sessionStorage.setItem(
      CACHE_KEY,
      JSON.stringify({ data, cachedAt: Date.now() })
    )
  } catch {
    // Ignore storage errors (private browsing, quota, etc.) — caching is
    // just an optimization, not required for correctness.
  }
}

async function loadLatestRelease() {
  loadingRelease.value = true
  loadError.value = false
  try {
    const cached = readCache()
    if (cached) {
      release.value = cached
      return
    }
    const res = await fetch(
      `https://api.github.com/repos/${REPO}/releases/latest`
    )
    if (!res.ok) throw new Error(`GitHub API responded with ${res.status}`)
    const data: GitHubRelease = await res.json()
    release.value = data
    writeCache(data)
  } catch (error) {
    console.error('Error fetching latest Streaming Data Loader release', error)
    loadError.value = true
  } finally {
    loadingRelease.value = false
  }
}

onMounted(() => {
  void loadLatestRelease()
})
</script>
