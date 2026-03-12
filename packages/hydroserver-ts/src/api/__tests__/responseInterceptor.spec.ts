import { describe, it, expect } from 'vitest'
import { responseInterceptor } from '../responseInterceptor'

describe('responseInterceptor', () => {
  it('processes a 200 status code response correctly', async () => {
    const mockJsonResponse = { data: 'Some data' }
    const mockResponse = new Response(JSON.stringify(mockJsonResponse), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })

    const result = await responseInterceptor(mockResponse)
    expect(result).toEqual({
      data: 'Some data',
      status: 200,
      message: 'OK',
      meta: undefined,
      ok: true,
    })
  })

  it('returns an envelope with null data if the Content-Length is 0', async () => {
    const mockResponse = new Response('', {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': '0',
      },
    })

    const result = await responseInterceptor(mockResponse)
    expect(result).toEqual({
      data: null,
      status: 200,
      message: 'OK',
      meta: undefined,
      ok: true,
    })
  })

  it('returns a Blob for CSV content', async () => {
    const csvData = 'id,name\n1,John\n2,Jane'
    const mockResponse = new Response(csvData, {
      status: 200,
      headers: { 'Content-Type': 'text/csv' },
    })

    const result = await responseInterceptor(mockResponse)
    const textContent = await (result.data as Blob).text()
    expect(textContent).toBe(csvData)
  })

  it('returns errorBody for 401 status code without throwing', async () => {
    const errorJson = { error: 'Unauthorized' }
    const mockResponse = new Response(JSON.stringify(errorJson), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    })

    const result = await responseInterceptor(mockResponse)
    expect(result).toEqual({
      data: errorJson,
      status: 401,
      message: 'OK',
      meta: undefined,
      ok: true,
    })
  })

  it('returns an error envelope for non-401 status codes', async () => {
    const mockErrorBody = { detail: 'Bad response' }
    const mockResponse = new Response(JSON.stringify(mockErrorBody), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    })

    await expect(responseInterceptor(mockResponse)).resolves.toEqual({
      data: mockErrorBody,
      status: 500,
      message: 'Bad response',
      ok: false,
    })
  })
})
