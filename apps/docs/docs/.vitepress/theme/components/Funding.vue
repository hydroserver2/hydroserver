<template>
  <VPTeamPage>
    <VPTeamPageTitle>
      <template #title>Funding and Acknowledgements</template>
      <template #lead>
        HydroServer is based on work supported by multiple funding
        organizations, including the Cooperative Institute for Research to
        Operations in Hydrology (CIROH). Funding was awarded to CIROH through
        the NOAA Cooperative Agreement with the University of Alabama
        (NA22NWS4320003). Additional support for HydroServer development has
        been provided by the State of Utah Division of Water Rights, the Utah
        Water Research Laboratory (UWRL) at Utah State University, and the World
        Meteorological Organization (WMO).
      </template>
    </VPTeamPageTitle>

    <div class="image-row">
      <img
        :src="withBase('/DWRi-logo.png')"
        alt="DWRI Logo"
        class="funding-logo dwri-logo"
      />
      <img
        :src="withBase('/UStateVertical_Blue.png')"
        alt="UWRL Logo"
        class="funding-logo logo uwrl-logo logo-blue img"
      />
      <img
        :src="withBase('/UStateVertical_White.png')"
        alt="UWRL Logo"
        class="funding-logo logo uwrl-logo logo-white img"
      />
      <div class="ciroh-logo-wrapper">
        <img
          :src="withBase('/CIROH_logo_transparent-min.png')"
          alt="CIROH Logo"
          class="funding-logo"
        />
      </div>
      <img
        :src="withBase('/WMO-logo.png')"
        alt="WMO Logo"
        class="funding-logo wmo-logo"
      />
    </div>
  </VPTeamPage>
</template>

<script setup>
import { VPTeamPage, VPTeamPageTitle } from "vitepress/theme";
import { withBase } from "vitepress";
</script>

<style scoped>
.image-row {
  display: flex;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
}

.image-row .funding-logo {
  height: 110px;
  width: auto;
  max-width: 220px;
  object-fit: contain;
}

.image-row .wmo-logo {
  transform: scale(1.35);
}

@media (max-width: 640px) {
  .image-row .funding-logo {
    height: 90px;
    max-width: 180px;
  }
  .ciroh-logo-wrapper {
    height: 90px;
    width: 90px;
  }
  .ciroh-logo-wrapper img {
    transform: scale(1.15);
  }
}

/* Ensure the CIROH logo has a white background */
.ciroh-logo-wrapper {
  background-color: white;
  margin: 10px;
  border-radius: 50%;
  height: 110px;
  width: 110px;
  display: flex;
  align-items: center;
  justify-content: center;
}

:root .image-row img.logo-blue {
  display: inline;
}

:root .image-row img.logo-white {
  display: none;
}

/* In dark mode, show the white logo and hide the blue logo */
:root.dark .image-row img.logo-blue {
  display: none;
}

:root.dark .image-row img.logo-white {
  display: inline;
}
</style>
