<template>
  <VPTeamPage>
    <VPTeamPageTitle>
      <template #title>Contact Us</template>
      <template #lead>
        Have questions about our software or development? We'd love to hear from
        you.
      </template>
    </VPTeamPageTitle>

    <div class="contact-cards">
      <div class="contact-card">
        <h4 class="h2 title">Email Us</h4>
        <p>
          The HydroServer software is under development at the Utah Water
          Research Laboratory at Utah State University through support from the
          National Oceanic and Atmospheric Administration’s (NOAA) Cooperative
          Institute for Research to Operations in Hydrology (CIROH). Please
          contact Jeff Horsburgh at
          <a href="mailto:jeff.horsburgh@usu.edu">jeff.horsburgh@usu.edu</a>.
        </p>
        <VPButton
          text="Send an email"
          theme="brand"
          href="mailto:jeff.horsburgh@usu.edu"
        />
      </div>
      <div class="contact-card">
        <h4>Connect With Us on GitHub</h4>
        <p>
          All of our software development activities are open source and
          available on GitHub. You can submit bugs or issues and follow our
          software development activities on our repository.
        </p>

        <VPButton
          text="Go to GitHub"
          theme="brand"
          href="https://github.com/hydroserver2/hydroserver"
          target="_blank"
        />
      </div>
    </div>
  </VPTeamPage>
</template>

<script setup>
import { VPButton, VPTeamPage, VPTeamPageTitle } from "vitepress/theme";
</script>

<style>
.contact-cards {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 2rem;
}

.contact-card {
  display: flex;
  flex-direction: column;
  background-color: var(--vp-c-bg-soft);
  border-radius: 8px;
  padding: 1.5rem;
  width: 100%;
  max-width: 500px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.contact-card .VPButton {
  margin-top: auto; /* Pushes the button to the bottom */
  align-self: flex-end; /* Aligns the button to the right */
}

.contact-card p {
  color: var(--vp-c-text-2); /* Primary text color */
  font-size: 1rem; /* Font size matching feature text */
  line-height: 1.5; /* Line height matching feature text */
  margin-bottom: 1rem;
}
</style>
