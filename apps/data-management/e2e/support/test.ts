import { randomUUID } from 'crypto'
import { expect, test as base } from '@playwright/test'

import { applyScenario, type E2EScenario } from './fixtures'

const API_BASE_URL = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:18000'
const CONTROL_TOKEN = process.env.E2E_CONTROL_TOKEN || ''

type ScenarioFixture = {
  isolatedScenario: E2EScenario
}

export const test = base.extend<ScenarioFixture>({
  isolatedScenario: [
    async ({ request }, use, testInfo) => {
      const scenarioKey = [
        `w${testInfo.workerIndex}`,
        `r${testInfo.retry}`,
        randomUUID().replaceAll('-', ''),
      ].join('-')
      const headers = { 'X-E2E-Control-Token': CONTROL_TOKEN }
      const response = await request.post(`${API_BASE_URL}/api/e2e/scenarios`, {
        headers,
        data: { scenarioKey },
      })

      expect(
        response.ok(),
        `Unable to create isolated E2E scenario: ${await response.text()}`
      ).toBeTruthy()

      const scenario = (await response.json()) as E2EScenario
      applyScenario(scenario)

      try {
        await use(scenario)
      } finally {
        const cleanup = await request.delete(
          `${API_BASE_URL}/api/e2e/scenarios`,
          {
            headers,
            data: { scenarioKey },
          }
        )
        expect(
          cleanup.ok(),
          `Unable to clean up isolated E2E scenario: ${await cleanup.text()}`
        ).toBeTruthy()
      }
    },
    { auto: true },
  ],
})

export { expect }
export type { Page } from '@playwright/test'
