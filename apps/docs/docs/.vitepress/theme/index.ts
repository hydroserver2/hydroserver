import DefaultTheme from "vitepress/theme";
import ImageModal from "./components/ImageModal.vue";
import "./custom.css";
import { h } from "vue";

export default {
  extends: DefaultTheme,
  Layout() {
    return h(DefaultTheme.Layout, null, {
      "layout-bottom": () => h(ImageModal),
    });
  },
};
