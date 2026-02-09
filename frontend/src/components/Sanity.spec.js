import { describe, it, expect } from 'vitest'

describe('System Sanity Check', () => {
  it('confirms that 1 + 1 equals 2', () => {
    expect(1 + 1).toBe(2)
  })

  it('confirms the testing infrastructure is active', () => {
    expect(true).toBe(true)
  })
})
