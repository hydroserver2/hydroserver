import { Datastream } from '@hydroserver/client'
import { api } from '@uwrl/qc-utils'
// import { Datastream } from '@/types'
import JSZip from 'jszip'

export const downloadDatastreamCSV = async (id: string) => {
  try {
    const data = await api.downloadDatastreamCSV(id)
    const blob = new Blob([data], { type: 'text/csv' })
    const link = document.createElement('a')
    link.href = window.URL.createObjectURL(blob)
    link.download = `datastream_${id}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (error) {
    console.error('Error downloading datastream CSV', error)
  }
}

export const downloadPlottedDatastreamsCSVs = async (
  plottedDatastreams: Datastream[]
) => {
  const zip = new JSZip()

  try {
    const csvPromises = plottedDatastreams.map(async (d) => {
      const data = await api.downloadDatastreamCSV(d.id)
      const blob = new Blob([data], { type: 'text/csv' })
      zip.file(`datastream_${d.id}.csv`, blob)
    })

    await Promise.all(csvPromises)

    // Generate the zip file
    zip.generateAsync({ type: 'blob' }).then(function (content) {
      const link = document.createElement('a')
      link.href = window.URL.createObjectURL(content)
      link.download = 'datastreams.zip'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    })
  } catch (error) {
    console.error('Error downloading datastreams CSVs', error)
  }
}
