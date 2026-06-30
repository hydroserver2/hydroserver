<template>
  <div class="map-wrapper">
    <!-- 2) Dropdown, absolutely positioned -->
    <div class="basemap-select-container" v-if="basemapTileSources.length > 1">
      <v-select
        v-model="selectedTileSourceName"
        :items="basemapTileSources"
        item-title="name"
        item-value="name"
        label="Base Map"
        dense
        hide-details
        variant="solo-filled"
        style="width: 180px"
      />
    </div>
    <div ref="mapContainer" class="fill-width fill-height"></div>

    <div class="map-overlay">
      <slot name="overlay" />
    </div>

    <div ref="popupContainer" class="ol-popup">
      <a href="#" ref="popupCloser" class="ol-popup-closer" />
      <div ref="popupContent" />
    </div>

    <div ref="selectionLabelContainer" class="selected-site-label">
      {{ selectedSiteLabel }}
    </div>

    <div v-if="uniqueColoredThings.length" class="legend">
      <h3>Legend</h3>
      <ul>
        <li v-for="thing in uniqueColoredThings" :key="thing.tagValue">
          <v-icon
            :icon="mdiMapMarker"
            :style="{ color: thing.color?.background }"
          ></v-icon>
          {{ thing?.tagValue }}
        </li>
      </ul>
    </div>

    <transition name="detail-card">
      <div v-if="selectable && detailThing" class="site-detail-card">
        <div class="detail-accent" />
        <div class="detail-body">
          <div class="detail-header">
            <div class="detail-heading">
              <h2 class="detail-name">{{ detailThing.name }}</h2>
              <div v-if="detailSubtitle" class="detail-meta">
                <v-icon :icon="mdiMapMarker" size="14" />
                <span>{{ detailSubtitle }}</span>
              </div>
            </div>
            <button
              class="detail-close"
              aria-label="Close"
              @click="emit('select', undefined)"
            >
              <v-icon :icon="mdiClose" size="18" />
            </button>
          </div>

          <div v-if="detailCoordinates" class="detail-grid">
            <div class="detail-field-label">Coordinates</div>
            <div class="detail-field-value detail-mono">
              {{ detailCoordinates }}
            </div>
          </div>

          <div class="detail-actions">
            <v-btn
              color="primary"
              variant="flat"
              style="flex: 1"
              :append-icon="mdiChevronRight"
              :href="`/sites/${detailThing.id}`"
            >
              View details
            </v-btn>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import {
  ref,
  onMounted,
  onBeforeUnmount,
  watch,
  computed,
  type PropType,
} from 'vue'
import hs, { Thing } from '@hydroserver/client'
import { MapThing, MapThingWithColor } from '@/types'
import {
  addColorToMarkers,
  generateMarkerContent,
  hasThingTags,
  isThingMarker,
} from '@/utils/maps/markers'
import OlMap from 'ol/Map'
import View from 'ol/View'
import TileLayer from 'ol/layer/Tile'
import VectorLayer from 'ol/layer/Vector'
import VectorSource from 'ol/source/Vector'
import { Feature, Overlay } from 'ol'
import type { FeatureLike } from 'ol/Feature'
import Point from 'ol/geom/Point'
import { Style, Icon } from 'ol/style'
import { fromLonLat, toLonLat } from 'ol/proj'
import { settings } from '@/config/settings'
import { Extent, isEmpty as extentIsEmpty } from 'ol/extent'
import { fetchLocationData } from '@/utils/maps/location'
import WebGLVectorLayer from 'ol/layer/WebGLVector'
import mapMarkerUrl from '@/assets/map-marker-64.png?url'
import { OSM, XYZ } from 'ol/source'
import { mdiMapMarker, mdiChevronRight, mdiClose } from '@mdi/js'

const props = defineProps({
  things: {
    type: Array as PropType<MapThing[]>,
    default: () => [],
  },
  colorKey: { type: String, default: '' },
  startInSatellite: Boolean,
  singleMarkerMode: Boolean,
  fitPadding: {
    type: Array as unknown as PropType<[number, number, number, number]>,
    default: () => [100, 100, 100, 100],
  },
  selectedThingId: {
    type: String,
    default: undefined,
  },
  // Browse-style selection: clicking a marker selects it (instead of opening
  // the anchored popup), the selected marker grows + shows its name label, and
  // details render in a fixed card rather than a marker-tethered popup.
  selectable: Boolean,
})
const emit = defineEmits(['location-clicked', 'select'])

interface ConfigTileSource {
  name: string
  source: import('ol/source/Tile').default
}

const defaultView = {
  center: fromLonLat([
    settings.mapConfiguration.defaultLongitude,
    settings.mapConfiguration.defaultLatitude,
  ]),
  zoom: settings.mapConfiguration.defaultZoomLevel,
}

const basemapTileSources = settings.mapConfiguration.basemapLayers.map(
  (mapLayer) => ({
    name: mapLayer.name,
    source: new XYZ({
      url: mapLayer.source,
      attributions: mapLayer.attribution,
    }),
  })
)

// TODO: Create a separate map control to toggle overlay layers
const overlayTileSources = settings.mapConfiguration.overlayLayers.map(
  (mapLayer) => ({
    name: mapLayer.name,
    source: new XYZ({
      url: mapLayer.source,
      attributions: mapLayer.attribution,
    }),
  })
)

if (basemapTileSources.length === 0) {
  basemapTileSources.push({
    name: 'Open Street Map',
    source: new OSM(),
  })
}

const mapContainer = ref<HTMLElement>()
const popupContainer = ref<HTMLElement>()
const popupContent = ref<HTMLElement>()
const popupCloser = ref<HTMLElement>()
const selectionLabelContainer = ref<HTMLElement>()

const coloredThings = ref<MapThingWithColor[]>([])
const selectedTileSourceName = ref<string>(basemapTileSources[0].name)
const detailedThingCache = new Map<string, Thing>()

let map: OlMap
let rasterLayer: TileLayer
let popupOverlay: Overlay | undefined
let selectionLabelOverlay: Overlay | undefined
let selectedThingTransitionId = 0
let selectedThingPopupTimer: number | undefined
let activeFlyId = 0
const vectorSource = new VectorSource<Feature>()
const markerLayer = ref<WebGLVectorLayer>()

// ── Browse-style selection (only used when `selectable`) ──
const detailThing = ref<MapThing>()
const selectionSource = new VectorSource<Feature>()
let selectionLayer: VectorLayer | undefined
// Final scale of the grown selection marker, relative to the 64px source png.
const SELECTION_SCALE = 0.78
let selectionScale = SELECTION_SCALE
let selectionAnimId = 0
const selectedSiteLabel = ref('')

const detailSubtitle = computed(() => {
  const thing = detailThing.value
  if (!thing) return ''
  const parts: string[] = []
  if (isThingMarker(thing)) {
    if (thing.siteType) parts.push(thing.siteType)
  } else {
    if (thing.siteType) parts.push(thing.siteType)
    const area = [thing.location.adminArea2, thing.location.adminArea1]
      .filter(Boolean)
      .join(', ')
    if (area) parts.push(area)
  }
  return parts.join(' · ')
})

const detailCoordinates = computed(() => {
  const thing = detailThing.value
  if (!thing) return ''
  const [lng, lat] = getThingCoordinates(thing as MapThingWithColor)
  const latNum = Number(lat)
  const lngNum = Number(lng)
  if (!isFinite(latNum) || !isFinite(lngNum)) return ''
  return `${latNum.toFixed(4)}, ${lngNum.toFixed(4)}`
})

const uniqueColoredThings = computed(() => {
  const firstOccurrenceMap = new Map()
  coloredThings.value.forEach((thing) => {
    if (thing.tagValue && !firstOccurrenceMap.has(thing.tagValue)) {
      firstOccurrenceMap.set(thing.tagValue, thing)
    }
  })
  return Array.from(firstOccurrenceMap.values()).sort((a, b) => {
    return a.tagValue.localeCompare(b.tagValue)
  })
})

const getThingCoordinates = (thing: MapThingWithColor) => {
  if (isThingMarker(thing)) {
    return [thing.longitude, thing.latitude] as const
  }

  return [thing.location.longitude, thing.location.latitude] as const
}

const createFeature = (thing: MapThingWithColor) => {
  const [longitude, latitude] = getThingCoordinates(thing)
  if (
    latitude == null ||
    longitude == null ||
    latitude === '' ||
    longitude === ''
  )
    return null
  const f = new Feature({
    geometry: new Point(fromLonLat([longitude, latitude])),
  })
  f.set('markerColor', thing?.color?.background || '#D32F2F')
  f.set('thing', thing)
  return f
}

const fitViewToMarkers = (duration = 0) => {
  if (!map) return

  const extent = vectorSource.getExtent() as Extent
  if (extentIsEmpty(extent) || props.singleMarkerMode) return

  map.getView().fit(extent, {
    padding: props.fitPadding,
    maxZoom: 16,
    duration,
  })
}

const getPopupThing = async (thing: MapThing): Promise<MapThing> => {
  if (!isThingMarker(thing)) return thing

  const cachedThing = detailedThingCache.get(thing.id)
  if (cachedThing) return cachedThing

  try {
    const detailedThing = await hs.things.getItem(thing.id)
    if (!detailedThing) return thing
    detailedThingCache.set(thing.id, detailedThing)
    return detailedThing
  } catch (error) {
    console.error('Error fetching marker details', error)
    return thing
  }
}

const getFeatureThing = (feature: Feature) =>
  feature.get('thing') as MapThing | undefined

const findFeatureByThingId = (thingId: string) =>
  vectorSource
    .getFeatures()
    .find((feature) => getFeatureThing(feature)?.id === thingId)

const openPopupForFeature = async (feature: Feature) => {
  const thing = getFeatureThing(feature)
  const geometry = feature.getGeometry()
  if (!thing || !(geometry instanceof Point) || !popupOverlay) return

  const popupThing = await getPopupThing(thing)
  popupContent.value!.innerHTML = generateMarkerContent(popupThing)
  popupOverlay.setPosition(geometry.getCoordinates())
}

// Style for the grown selection marker drawn on top of the WebGL markers.
const selectionStyle = (feature: FeatureLike) => {
  const color = (feature.get('markerColor') as string) || '#D32F2F'
  return new Style({
    image: new Icon({
      src: mapMarkerUrl,
      anchor: [0.5, 1],
      color,
      scale: selectionScale,
    }),
  })
}

// Quick "pop" as the marker grows in, for parity with the design's CSS scale.
const animateSelectionScale = (from: number, to: number, duration = 180) => {
  const animId = ++selectionAnimId
  const start = performance.now()
  const ease = (k: number) => 1 - Math.pow(1 - k, 2)
  const step = (now: number) => {
    if (animId !== selectionAnimId) return
    const k = Math.min(1, (now - start) / duration)
    selectionScale = from + (to - from) * ease(k)
    selectionLayer?.changed()
    if (k < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

const updateSelectionMarker = (thingId?: string | null) => {
  selectionSource.clear()
  if (!thingId) {
    selectedSiteLabel.value = ''
    selectionLabelOverlay?.setPosition(undefined)
    selectionAnimId++ // stop any in-flight grow
    return
  }
  const feature = findFeatureByThingId(thingId)
  const geometry = feature?.getGeometry()
  if (!feature || !(geometry instanceof Point)) {
    selectedSiteLabel.value = ''
    selectionLabelOverlay?.setPosition(undefined)
    return
  }

  const clone = new Feature({ geometry: geometry.clone() })
  clone.set('markerColor', feature.get('markerColor'))
  clone.set('thing', getFeatureThing(feature))
  selectionSource.addFeature(clone)
  selectedSiteLabel.value = getFeatureThing(feature)?.name ?? ''
  selectionLabelOverlay?.setPosition(geometry.getCoordinates())
  animateSelectionScale(SELECTION_SCALE * 0.78, SELECTION_SCALE)
}

const loadDetailThing = async (thingId?: string | null) => {
  if (!thingId) {
    detailThing.value = undefined
    return
  }
  const base = props.things.find((thing) => thing.id === thingId)
  if (!base) return
  detailThing.value = base // show immediately, then enrich
  const detailed = await getPopupThing(base)
  if (props.selectedThingId === thingId) detailThing.value = detailed
}

const getPaddedCenter = (
  coordinates: [number, number],
  zoom: number
): [number, number] => {
  const [top, right, bottom, left] = props.fitPadding
  const resolution = map.getView().getResolutionForZoom(zoom)

  return [
    coordinates[0] - ((left - right) / 2) * resolution,
    coordinates[1] + ((top - bottom) / 2) * resolution,
  ]
}

/**
 * Smooth zoom-and-pan that mirrors Leaflet's `flyTo`, using the
 * van Wijk & Nuij "Smooth and efficient zooming and panning" algorithm.
 * OpenLayers' `view.animate` interpolates center and zoom linearly, which
 * feels abrupt over long distances; this drives the view per frame instead so
 * the camera arcs out and back in along an optimal path.
 */
const flyTo = (
  targetCenter: [number, number],
  targetZoom: number,
  { duration, onComplete }: { duration?: number; onComplete?: () => void } = {}
) => {
  if (!map) return
  const view = map.getView()
  const size = map.getSize()
  const from = view.getCenter()
  const startResolution = view.getResolution()
  const endResolution = view.getResolutionForZoom(targetZoom)

  view.cancelAnimations()
  const flyId = ++activeFlyId

  if (!size || !from || startResolution == null) {
    view.setCenter(targetCenter)
    view.setResolution(endResolution)
    onComplete?.()
    return
  }

  const maxPx = Math.max(size[0], size[1])
  const dx = targetCenter[0] - from[0]
  const dy = targetCenter[1] - from[1]
  const u1 = Math.hypot(dx, dy)
  const pixelDistance = u1 / startResolution

  const easeOutFly = (k: number) => 1 - Math.pow(1 - k, 1.5)
  const start = performance.now()

  // Negligible pan: the van Wijk path degenerates, so just ease the
  // resolution (and the tiny center delta) directly.
  if (pixelDistance < 2) {
    const totalDuration = duration ?? 350
    const step = (now: number) => {
      if (flyId !== activeFlyId) return
      const k = Math.min(1, (now - start) / totalDuration)
      const e = easeOutFly(k)
      view.setCenter([from[0] + dx * e, from[1] + dy * e])
      view.setResolution(
        startResolution + (endResolution - startResolution) * e
      )
      if (k < 1) requestAnimationFrame(step)
      else onComplete?.()
    }
    requestAnimationFrame(step)
    return
  }

  // van Wijk smooth zoom-and-pan. Work in projection units (meters): viewport
  // width in world units is resolution * pixels, so widths are zoom-independent.
  const w0 = Math.max(startResolution * maxPx, 1e-6)
  const w1 = Math.max(endResolution * maxPx, 1e-6)
  const rho = 1.42
  const rho2 = rho * rho
  const cosh = (n: number) => (Math.exp(n) + Math.exp(-n)) / 2
  const sinh = (n: number) => (Math.exp(n) - Math.exp(-n)) / 2
  const tanh = (n: number) => sinh(n) / cosh(n)
  const r = (i: 0 | 1) => {
    const s1 = i ? -1 : 1
    const s2 = i ? w1 : w0
    const t1 = w1 * w1 - w0 * w0 + s1 * rho2 * rho2 * u1 * u1
    const b = t1 / (2 * s2 * rho2 * u1)
    const sq = Math.sqrt(b * b + 1) - b
    return sq < 1e-9 ? -18 : Math.log(sq)
  }
  const r0 = r(0)
  const bigS = (r(1) - r0) / rho
  const w = (s: number) => (w0 * cosh(r0)) / cosh(rho * s + r0)
  const u = (s: number) =>
    (w0 * (cosh(r0) * tanh(rho * s + r0) - sinh(r0))) / rho2
  const totalDuration = duration ?? Math.max(300, bigS * 0.8 * 1000)

  const step = (now: number) => {
    if (flyId !== activeFlyId) return
    const k = Math.min(1, (now - start) / totalDuration)
    if (k < 1) {
      const s = easeOutFly(k) * bigS
      const frac = u(s) / u1
      view.setCenter([from[0] + dx * frac, from[1] + dy * frac])
      view.setResolution(w(s) / maxPx)
      requestAnimationFrame(step)
    } else {
      view.setCenter(targetCenter)
      view.setResolution(endResolution)
      onComplete?.()
    }
  }
  requestAnimationFrame(step)
}

const focusThingById = (thingId?: string | null) => {
  selectedThingTransitionId++
  const transitionId = selectedThingTransitionId

  if (selectedThingPopupTimer !== undefined) {
    window.clearTimeout(selectedThingPopupTimer)
    selectedThingPopupTimer = undefined
  }

  if (!map || !thingId) {
    activeFlyId++ // cancel any in-flight fly
    popupOverlay?.setPosition(undefined)
    if (props.selectable) updateSelectionMarker(undefined)
    return
  }

  const feature = findFeatureByThingId(thingId)
  const geometry = feature?.getGeometry()
  if (!feature || !(geometry instanceof Point)) return

  const view = map.getView()
  const currentZoom = view.getZoom() ?? 0
  const targetZoom = Math.max(currentZoom, 12.5)
  const targetCoordinates = geometry.getCoordinates() as [number, number]
  const targetCenter = getPaddedCenter(targetCoordinates, targetZoom)

  popupOverlay?.setPosition(undefined)

  if (props.selectable) {
    // Browse mode: grow the marker + show its label; details live in the card.
    updateSelectionMarker(thingId)
    flyTo(targetCenter, targetZoom, { duration: 700 })
    return
  }

  flyTo(targetCenter, targetZoom, {
    duration: 700,
    onComplete: () => {
      if (transitionId !== selectedThingTransitionId) return
      void openPopupForFeature(feature)
    },
  })
}

async function updateFeatures() {
  // 1) Rebuild features
  coloredThings.value = props.colorKey
    ? props.things.every(hasThingTags)
      ? addColorToMarkers(props.things, props.colorKey)
      : props.things
    : props.things

  const features = coloredThings.value
    .map(createFeature)
    .filter((feature) => feature !== null)

  // 2) clear & add
  if (!vectorSource) return
  vectorSource.clear()
  vectorSource.addFeatures(features)

  if (props.selectedThingId) {
    if (findFeatureByThingId(props.selectedThingId)) {
      focusThingById(props.selectedThingId)
      return
    }

    if (props.selectable) updateSelectionMarker(undefined)
  }

  // 3) zoom to the extent of whatever source we used
  fitViewToMarkers()
}

const initializeMap = () => {
  if (!basemapTileSources.length) {
    console.error(
      '[OpenLayersMap] No tile services available.' +
        ' Please check you openLayers Map Config file and make sure' +
        ' you have at least one valid tile source defined.'
    )
    return
  }

  const desiredType = props.startInSatellite ? 'satellite' : 'base'
  const chosenSourceLayerName =
    desiredType === 'satellite'
      ? settings.mapConfiguration.defaultSatelliteLayer
      : settings.mapConfiguration.defaultBaseLayer
  let chosenSource = basemapTileSources.find(
    (s) => s.name === chosenSourceLayerName
  )
  if (!chosenSource) chosenSource = basemapTileSources[0]
  selectedTileSourceName.value = chosenSource.name

  rasterLayer = new TileLayer({ source: chosenSource.source })
  markerLayer.value = new WebGLVectorLayer({
    source: vectorSource,
    style: {
      'icon-src': mapMarkerUrl,
      'icon-width': [
        'interpolate',
        ['linear'],
        ['zoom'],
        1,
        4, // at zoom level 1 → 4px
        8,
        32, // at zoom level 8 → 32px
        16,
        48, // at zoom level 16 → 48px
      ],
      'icon-height': ['interpolate', ['linear'], ['zoom'], 1, 4, 8, 32, 16, 48],
      'icon-anchor': [0.5, 1],
      'icon-color': ['get', 'markerColor'], // red-darken-2
      'icon-opacity': 0.85,
    },
  })

  selectionLayer = new VectorLayer({
    source: selectionSource,
    style: selectionStyle,
  })

  popupOverlay = new Overlay({
    element: popupContainer.value,
    autoPan: props.singleMarkerMode ? false : { animation: { duration: 250 } },
  })

  selectionLabelOverlay = new Overlay({
    element: selectionLabelContainer.value,
    positioning: 'center-left',
    offset: [42, -26],
    stopEvent: false,
  })

  popupCloser.value!.onclick = () => {
    popupOverlay?.setPosition(undefined)
    return false
  }

  map = new OlMap({
    target: mapContainer.value,
    layers: [rasterLayer, markerLayer.value, selectionLayer],
    overlays: [popupOverlay, selectionLabelOverlay],
    view: new View(defaultView),
  })

  map.on('click', async (evt) => {
    if (props.singleMarkerMode) {
      vectorSource.clear()
      const single = new Feature(new Point(evt.coordinate))
      single.set('markerColor', '#D32F2F')
      vectorSource.addFeature(single)

      const [lon, lat] = toLonLat(evt.coordinate)
      const locationData = await fetchLocationData(lat, lon)
      emit('location-clicked', locationData)
      return
    }

    const rawFeatures = map.forEachFeatureAtPixel(evt.pixel, (f) => f)

    // Browse mode: clicks drive selection rather than opening a popup.
    if (props.selectable) {
      if (!rawFeatures) {
        emit('select', undefined)
        return
      }
      const clickedFeature = Array.isArray(rawFeatures.get('features'))
        ? rawFeatures.get('features')[0]
        : rawFeatures
      const thingId = getFeatureThing(clickedFeature as Feature)?.id
      if (thingId) emit('select', thingId)
      return
    }

    if (!rawFeatures) {
      popupOverlay?.setPosition(undefined)
      return
    }
    // if it’s a cluster, OL puts real features in a “features” array
    const clicked = Array.isArray(rawFeatures.get('features'))
      ? rawFeatures.get('features')[0]
      : rawFeatures
    await openPopupForFeature(clicked as Feature)
  })

  map.on('pointermove', function (e) {
    // change mouse cursor when over marker
    const hit = map.hasFeatureAtPixel(e.pixel)
    map.getTargetElement().style.cursor = hit ? 'pointer' : ''
  })

  updateFeatures()

  // The sites likely aren't loaded at this point. Skip fitting the view and let the update function handle fitting when they arrive.
  const features = vectorSource.getFeatures()
  if (!features.length) return

  fitViewToMarkers()
}

const onKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.selectedThingId) emit('select', undefined)
}

onMounted(async () => {
  if (!mapContainer.value) return
  initializeMap()
  if (props.selectable) {
    void loadDetailThing(props.selectedThingId)
    window.addEventListener('keydown', onKeydown)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})

watch(() => [props.things] as const, updateFeatures, { deep: true })

watch(
  () => props.selectedThingId,
  (thingId) => {
    void focusThingById(thingId)
    if (props.selectable) void loadDetailThing(thingId)
  }
)

watch(
  () => props.fitPadding,
  () => {
    if (!map) return
    map.updateSize()
    if (props.selectedThingId) {
      void focusThingById(props.selectedThingId)
    } else {
      fitViewToMarkers(250)
    }
  },
  { deep: true }
)

function getConfigByName(name: string): ConfigTileSource {
  const found = basemapTileSources.find((cfg) => cfg.name === name)
  return found || basemapTileSources[0]
}
watch(
  () => selectedTileSourceName.value,
  (newName) => {
    const cfg = getConfigByName(newName)
    if (cfg && rasterLayer) {
      rasterLayer.setSource(cfg.source)
    }
  }
)
</script>

<style scoped>
.map-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
}

:deep(.ol-zoom) {
  top: auto;
  right: 14px;
  bottom: 56px;
  left: auto;
}

:deep(.ol-zoom button) {
  width: 36px;
  height: 36px;
  font-size: 1.4rem;
}

/* 2) Position the dropdown in the top-right corner */
.basemap-select-container {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 2; /* above the map tiles */
}

.fill-width {
  width: 100%;
}

.map-overlay {
  position: absolute;
  left: 0;
  bottom: 0;
  z-index: 5;
}

.legend {
  position: absolute;
  bottom: 10px;
  left: 10px;
  background: rgba(255, 255, 255, 0.8);
  padding: 10px;
  border: 1px solid #000;
  z-index: 1;
  max-height: 200px;
  overflow-y: auto;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.selected-site-label {
  max-width: 320px;
  padding: 6px 12px;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.22);
  color: rgba(0, 0, 0, 0.78);
  font-size: 13px;
  font-weight: 600;
  line-height: 1.2;
  pointer-events: none;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selected-site-label:empty {
  display: none;
}

/* ── Browse selected-site detail card ── */
.site-detail-card {
  position: absolute;
  left: 412px;
  bottom: 16px;
  width: 348px;
  z-index: 6;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.22);
  overflow: hidden;
}

.detail-accent {
  height: 4px;
  background: rgb(var(--v-theme-primary));
}

.detail-body {
  padding: 13px 16px 15px;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.detail-heading {
  flex: 1;
  min-width: 0;
}

.detail-name {
  font-size: 16.5px;
  font-weight: 600;
  line-height: 1.25;
  color: rgba(0, 0, 0, 0.87);
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 4px;
  font-size: 12.5px;
  color: rgba(0, 0, 0, 0.6);
}

.detail-close {
  flex-shrink: 0;
  display: flex;
  border: none;
  background: transparent;
  border-radius: 50%;
  padding: 5px;
  cursor: pointer;
  color: rgba(0, 0, 0, 0.6);
}

.detail-close:hover {
  background: rgba(0, 0, 0, 0.07);
}

.detail-grid {
  margin: 13px 0;
  padding: 11px 12px;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 10px;
}

.detail-field-label {
  font-size: 10.5px;
  color: rgba(0, 0, 0, 0.6);
  margin-bottom: 2px;
}

.detail-field-value {
  font-size: 12.5px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.87);
}

.detail-mono {
  font-family: 'Roboto Mono', monospace;
  font-weight: 400;
}

.detail-actions {
  display: flex;
  gap: 8px;
}

.detail-card-enter-active,
.detail-card-leave-active {
  transition: opacity 0.2s ease, transform 0.2s cubic-bezier(0.2, 0.8, 0.3, 1);
}

.detail-card-enter-from,
.detail-card-leave-to {
  opacity: 0;
  transform: translateY(14px);
}

@media (max-width: 900px) {
  .selected-site-label {
    display: none;
  }

  .site-detail-card {
    left: 12px;
    right: 12px;
    bottom: 12px;
    width: auto;
  }
}

.ol-popup {
  position: absolute;
  background-color: white;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
  padding: 15px;
  border-radius: 10px;
  border: 1px solid #cccccc;
  bottom: 12px;
  left: -50px;
  min-width: 400px;
}
.ol-popup:after,
.ol-popup:before {
  top: 100%;
  border: solid transparent;
  content: ' ';
  height: 0;
  width: 0;
  position: absolute;
  pointer-events: none;
}
.ol-popup:after {
  border-top-color: white;
  border-width: 10px;
  left: 48px;
  margin-left: -10px;
}
.ol-popup:before {
  border-top-color: #cccccc;
  border-width: 11px;
  left: 48px;
  margin-left: -11px;
}
.ol-popup-closer {
  text-decoration: none;
  position: absolute;
  top: 2px;
  right: 8px;
}
.ol-popup-closer:after {
  content: '✖';
}
</style>
