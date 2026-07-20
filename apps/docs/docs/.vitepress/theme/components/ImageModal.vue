<template>
  <Teleport to="body">
    <div
      v-if="activeImage"
      class="image-modal"
      role="dialog"
      aria-modal="true"
      :aria-label="activeImage.alt || 'Expanded documentation image'"
      @click="closeModal"
    >
      <button
        ref="closeButton"
        class="image-modal__close"
        type="button"
        aria-label="Close expanded image"
        @click.stop="closeModal"
      >
        &times;
      </button>
      <img
        class="image-modal__image"
        :src="activeImage.src"
        :alt="activeImage.alt"
        @click.stop
      />
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vitepress";

type ModalImage = {
  src: string;
  alt: string;
};

const route = useRoute();
const activeImage = ref<ModalImage | null>(null);
const closeButton = ref<HTMLButtonElement | null>(null);
let observer: MutationObserver | undefined;

const docsImageSelector = ".VPContent img";
const docsImageClass = "docs-clickable-image";

function getDocsImage(target: EventTarget | null): HTMLImageElement | null {
  if (!(target instanceof Element)) {
    return null;
  }

  return target.closest<HTMLImageElement>(docsImageSelector);
}

function prepareImages() {
  document
    .querySelectorAll<HTMLImageElement>(docsImageSelector)
    .forEach((image) => {
      image.classList.add(docsImageClass);

      if (!image.hasAttribute("tabindex")) {
        image.tabIndex = 0;
      }

      if (!image.hasAttribute("role")) {
        image.setAttribute("role", "button");
      }

      if (!image.hasAttribute("aria-label")) {
        const label = image.alt ? `Expand image: ${image.alt}` : "Expand image";
        image.setAttribute("aria-label", label);
      }
    });
}

function openImage(image: HTMLImageElement) {
  const src = image.currentSrc || image.src;

  if (!src) {
    return;
  }

  activeImage.value = {
    src,
    alt: image.alt,
  };

  document.documentElement.classList.add("image-modal-open");
  void nextTick(() => closeButton.value?.focus());
}

function closeModal() {
  activeImage.value = null;
  document.documentElement.classList.remove("image-modal-open");
}

function handleClick(event: MouseEvent) {
  const image = getDocsImage(event.target);

  if (!image) {
    return;
  }

  event.preventDefault();
  openImage(image);
}

function handleKeydown(event: KeyboardEvent) {
  if (activeImage.value && event.key === "Escape") {
    closeModal();
    return;
  }

  if (event.key !== "Enter" && event.key !== " ") {
    return;
  }

  const image = getDocsImage(event.target);

  if (!image) {
    return;
  }

  event.preventDefault();
  openImage(image);
}

watch(
  () => route.path,
  () => {
    void nextTick(prepareImages);
  },
);

onMounted(() => {
  prepareImages();

  observer = new MutationObserver(prepareImages);
  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });

  document.addEventListener("click", handleClick);
  document.addEventListener("keydown", handleKeydown);
});

onUnmounted(() => {
  observer?.disconnect();
  document.removeEventListener("click", handleClick);
  document.removeEventListener("keydown", handleKeydown);
  document.documentElement.classList.remove("image-modal-open");
});
</script>

<style scoped>
:global(html.image-modal-open),
:global(html.image-modal-open body) {
  overflow: hidden;
}

:global(.VPContent img.docs-clickable-image) {
  cursor: zoom-in;
}

:global(.VPContent img.docs-clickable-image:focus-visible) {
  outline: 3px solid var(--vp-c-brand);
  outline-offset: 4px;
}

.image-modal {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgb(3, 7, 18);
  cursor: zoom-out;
}

.image-modal__image {
  display: block;
  max-width: calc(100vw - 32px);
  max-height: calc(100dvh - 32px);
  object-fit: contain;
  cursor: default;
}

.image-modal__close {
  position: fixed;
  top: 16px;
  right: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 50%;
  color: white;
  background: rgba(15, 23, 42, 0.72);
  font-size: 28px;
  line-height: 1;
  cursor: pointer;
}

.image-modal__close:hover,
.image-modal__close:focus-visible {
  background: rgba(33, 150, 243, 0.95);
  outline: none;
}

@media (max-width: 640px) {
  .image-modal {
    padding: 8px;
  }

  .image-modal__image {
    max-width: calc(100vw - 16px);
    max-height: calc(100dvh - 16px);
  }
}
</style>
