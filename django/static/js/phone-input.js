// Same Maska version and mask as v1.12.1's AccountForm.vue. Keep the
// formatted value in the input so form submissions retain v1's storage format.
(() => {
  const inputs = document.querySelectorAll('input[data-maska]')
  new Maska.MaskInput(inputs)

  for (const input of inputs) {
    const validate = () => {
      const digits = input.value.replace(/\D/g, '')
      input.setCustomValidity(
        digits.length === 0 || digits.length === 10
          ? ''
          : 'Phone number must contain 10 digits.'
      )
    }
    input.addEventListener('input', validate)
    // Maska formats existing values in a microtask during initialization.
    queueMicrotask(validate)
  }
})()
