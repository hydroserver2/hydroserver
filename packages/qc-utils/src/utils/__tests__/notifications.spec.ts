import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import {
  Snackbar,
  Snack,
  SnackColor,
  SnackIcon,
  SnackTitle,
  Position,
  DEFAULT_SNACK_DURATION,
} from '../notifications'
import { Subscription } from 'rxjs'

describe('Snackbar', () => {
  let snacks: Snack[] = []
  let subscription: Subscription

  beforeEach(() => {
    subscription = Snackbar.snack$.subscribe((snack) => snacks.push(snack))
  })

  afterEach(() => {
    subscription.unsubscribe()
    snacks = []
  })

  it('emits a success Snack', () => {
    const message = 'Success message'
    Snackbar.success(message)

    expect(snacks.length).toBe(1)
    const snack = snacks[0]
    expect(snack.message).toBe(message)
    expect(snack.color).toBe(SnackColor.Success)
    expect(snack.icon).toBe(SnackIcon.Success)
    expect(snack.title).toBe(SnackTitle.Success)
    expect(snack.timeout).toBe(DEFAULT_SNACK_DURATION)
    expect(snack.position).toBe(Position.Bottom)
    expect(snack.visible).toBe(true)
  })

  it('emits a warning Snack', () => {
    const message = 'Warning message'
    Snackbar.warn(message)

    expect(snacks.length).toBe(1)
    const snack = snacks[0]
    expect(snack.message).toBe(message)
    expect(snack.color).toBe(SnackColor.Warning)
    expect(snack.icon).toBe(SnackIcon.Warning)
    expect(snack.title).toBe(SnackTitle.Warning)
  })

  it('handles info and error snacks at the same time', () => {
    const infoMessage = 'Info message'
    const errorMessage = 'Error message'
    Snackbar.info(infoMessage)
    Snackbar.error(errorMessage)

    expect(snacks.length).toBe(2)
    const infoSnack = snacks[0]
    expect(infoSnack.timeout).toBe(DEFAULT_SNACK_DURATION)
    expect(infoSnack.position).toBe(Position.Bottom)
    expect(infoSnack.visible).toBe(true)

    const errorSnack = snacks[1]
    expect(errorSnack.message).toBe(errorMessage)
    expect(errorSnack.color).toBe(SnackColor.Error)
    expect(errorSnack.icon).toBe(SnackIcon.Error)
    expect(errorSnack.title).toBe(SnackTitle.Error)
  })
})
