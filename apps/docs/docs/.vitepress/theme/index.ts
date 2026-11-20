import DefaultTheme from "vitepress/theme";
import ImageModal from "./components/ImageModal.vue";
import VersionNotices from "./components/VersionNotices.vue";
import "./custom.css";
import { h } from "vue";

export default {
  extends: DefaultTheme,
  Layout() {
    return h(DefaultTheme.Layout, null, {
      "doc-before": () => h(VersionNotices),
      "home-hero-before": () =>
        h("div", { class: "home-version-notices" }, [h(VersionNotices)]),
      "layout-bottom": () => h(ImageModal),
    });
  },
};
