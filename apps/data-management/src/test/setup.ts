const createMemoryStorage = (): Storage => {
  const store = new Map<string, string>()

  return {
    clear: () => store.clear(),
    getItem: (key: string) => store.get(key) ?? null,
    key: (index: number) => Array.from(store.keys())[index] ?? null,
    removeItem: (key: string) => {
      store.delete(key)
    },
    setItem: (key: string, value: string) => {
      store.set(key, value)
    },
    get length() {
      return store.size
    },
  }
}

const hasUsableStorage = (storageType: 'localStorage' | 'sessionStorage') => {
  try {
    const storage = window[storageType]
    return (
      typeof storage?.clear === 'function' &&
      typeof storage?.getItem === 'function' &&
      typeof storage?.removeItem === 'function' &&
      typeof storage?.setItem === 'function'
    )
  } catch {
    return false
  }
}

if (!hasUsableStorage('localStorage')) {
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: createMemoryStorage(),
  })
}

if (!hasUsableStorage('sessionStorage')) {
  Object.defineProperty(window, 'sessionStorage', {
    configurable: true,
    value: createMemoryStorage(),
  })
}
