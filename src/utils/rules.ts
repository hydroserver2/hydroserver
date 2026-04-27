export const required = [
  (value: string) => !!value || 'This field is required.',
]

export const requiredNumber = [
  (value: number | string) => {
    if (typeof value === 'number' && !isNaN(value)) return true
    if (
      typeof value === 'string' &&
      /^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$/.test(value)
    )
      return true
    return 'This field requires a valid number.'
  },
]

const emailFormat = [
  (value: string) => /.+@.+\..+/.test(value) || 'Email must be valid.',
]

export const rules = {
  required,
  email: [...required, ...emailFormat],
}
