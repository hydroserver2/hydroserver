<template>
  <VPTeamPage>
    <VPTeamPageTitle>
      <template #title>Funding and Acknowledgements</template>
      <template #lead>
        HydroServer is based on work supported by the Cooperative Institute for
        Research to Operations in Hydrology (CIROH). Funding was awarded to
        CIROH through the NOAA Cooperative Agreement with the University of
        Alabama (NA22NWS4320003). Additional support for HydroServer development
        has been provided by the State of Utah Division of Water Rights and by
        the Utah Water Research Laboratory.
      </template>
    </VPTeamPageTitle>

    <div class="image-row">
      <img
        :src="withBase('/DWRi-logo.png')"
        alt="DWRI Logo"
        class="dwri-logo"
      />
      <img
        :src="withBase('/UStateVertical_Blue.png')"
        alt="UWRL Logo"
        class="logo uwrl-logo logo-blue img"
      />
      <img
        :src="withBase('/UStateVertical_White.png')"
        alt="UWRL Logo"
        class="logo uwrl-logo logo-white img"
      />
      <div class="ciroh-logo-wrapper">
        <img
          :src="withBase('/CIROH_logo_transparent-min.png')"
          alt="CIROH Logo"
        />
      </div>
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

.image-row .dwri-logo {
  max-width: 15%;
}

/* Ensure the CIROH logo has a white background */
.ciroh-logo-wrapper {
  background-color: white;
  margin: 10px;
  border-radius: 50%;
  max-width: 15%;
}

:root .image-row img.logo-blue {
  display: inline;
  max-width: 25%;
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
  max-width: 25%;
}
</style>
