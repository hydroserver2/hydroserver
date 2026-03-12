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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { Thing } from '@hydroserver/client'
import { ThingWithColor } from '@/types'
import { addColorToMarkers, generateMarkerContent } from '@/utils/maps/markers'
import OlMap from 'ol/Map'
import View from 'ol/View'
import TileLayer from 'ol/layer/Tile'
import VectorSource from 'ol/source/Vector'
import { Feature, Overlay } from 'ol'
import Point from 'ol/geom/Point'
import { fromLonLat, toLonLat } from 'ol/proj'
import { settings } from '@/config/settings'
import { Extent, isEmpty as extentIsEmpty } from 'ol/extent'
import { fetchLocationData } from '@/utils/maps/location'
import WebGLVectorLayer from 'ol/layer/WebGLVector'
import mapMarkerUrl from '@/assets/map-marker-64.png?url'
import { OSM, XYZ } from 'ol/source'
import { mdiMapMarker } from '@mdi/js'

const props = defineProps({
  things: { type: Array<Thing>, default: [] },
  colorKey: { type: String, default: '' },
  startInSatellite: Boolean,
  singleMarkerMode: Boolean,
})
const emit = defineEmits(['location-clicked'])

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

const coloredThings = ref<ThingWithColor[]>([])
const selectedTileSourceName = ref<string>(basemapTileSources[0].name)

let map: OlMap
let rasterLayer: TileLayer
const vectorSource = new VectorSource<Feature>()
const markerLayer = ref<WebGLVectorLayer>()

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

const createFeature = (thing: ThingWithColor) => {
  if (!thing.location.latitude || !thing.location.longitude) return null
  const f = new Feature({
    geometry: new Point(
      fromLonLat([thing.location.longitude, thing.location.latitude])
    ),
  })
  f.set('markerColor', thing?.color?.background || '#D32F2F')
  f.set('thing', thing)
  return f
}

async function updateFeatures() {
  // 1) Rebuild features
  coloredThings.value = props.colorKey
    ? addColorToMarkers(props.things, props.colorKey)
    : props.things

  const features = coloredThings.value
    .map(createFeature)
    .filter((feature) => feature !== null)

  // 2) clear & add
  if (!vectorSource) return
  vectorSource.clear()
  vectorSource.addFeatures(features)

  // 3) zoom to the extent of whatever source we used
  const extent = vectorSource.getExtent() as Extent
  if (extentIsEmpty(extent) || props.singleMarkerMode) return
  map.getView().fit(extent, {
    padding: [100, 100, 100, 100],
    maxZoom: 16,
    duration: 0,
  })
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

  const overlay = new Overlay({
    element: popupContainer.value,
    autoPan: props.singleMarkerMode ? false : { animation: { duration: 250 } },
  })

  popupCloser.value!.onclick = () => overlay.setPosition(undefined)

  map = new OlMap({
    target: mapContainer.value,
    layers: [rasterLayer, markerLayer.value],
    overlays: [overlay],
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
    if (!rawFeatures) {
      overlay.setPosition(undefined)
      return
    }
    // if it’s a cluster, OL puts real features in a “features” array
    const clicked = Array.isArray(rawFeatures.get('features'))
      ? rawFeatures.get('features')[0]
      : rawFeatures

    const thing = clicked.get('thing')
    popupContent.value!.innerHTML = generateMarkerContent(thing)
    overlay.setPosition(evt.coordinate)
  })

  map.on('pointermove', function (e) {
    // change mouse cursor when over marker
    const hit = map.hasFeatureAtPixel(e.pixel)
    map.getTargetElement().style.cursor = hit ? 'pointer' : ''
  })

  updateFeatures()

  const extent = vectorSource.getExtent() as Extent

  // The sites likely aren't loaded at this point. Skip fitting the view and let the update function handle fitting when they arrive.
  const features = vectorSource.getFeatures()
  if (!features.length) return

  map.getView().fit(extent, {
    padding: [100, 100, 100, 100],
    maxZoom: 16,
    duration: 0,
  })
}

onMounted(async () => {
  if (!mapContainer.value) return
  initializeMap()
})

watch(() => [props.things] as const, updateFeatures, { deep: true })

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
