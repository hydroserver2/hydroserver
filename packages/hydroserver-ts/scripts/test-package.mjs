import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtemp, mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

const directory = await mkdtemp(join(tmpdir(), 'hydroserver-client-package-'))
const tsc = resolve('node_modules/typescript/bin/tsc')
const run = (command, args, cwd = directory) =>
  execFileSync(command, args, { cwd, stdio: 'inherit' })

try {
  // Exercise prepack as well as the actual files shipped to consumers.
  run('npm', ['pack', '--loglevel', 'error', '--pack-destination', directory], process.cwd())
  const { name, version } = JSON.parse(await readFile('package.json', 'utf8'))
  const archive = join(directory, `${name.replace('@', '').replace('/', '-')}-${version}.tgz`)
  const installed = join(directory, 'node_modules', name)
  await mkdir(installed, { recursive: true })
  run('tar', ['-xzf', archive, '-C', installed, '--strip-components=1'])
  const declarationFiles = (await readdir(join(installed, 'dist'), { recursive: true }))
    .filter(path => /\.d\.(?:ts|cts)$/.test(path))
    .sort()
  assert.deepEqual(declarationFiles, ['index.d.cts', 'index.d.ts'])
  await writeFile(join(directory, 'package.json'), '{"type":"module"}\n')
  const consumer = `
import hs, { HydroServer, ThingContract, UserService } from '@hydroserver/client'
const client: HydroServer = hs
const query: ThingContract.QueryParameters = { page: 1 }
client.things.list(query)
const name: ThingContract.DetailResponse['name'] = 'A site'
// @ts-expect-error Schema types must not silently become any.
const invalidName: ThingContract.DetailResponse['name'] = 123
// @ts-expect-error Generated query types must reject invalid values.
client.things.list({ page: 'invalid' })
const userService: UserService = client.user
`
  await writeFile(join(directory, 'consumer.mts'), consumer)
  await writeFile(join(directory, 'consumer.cts'), consumer)
  await writeFile(join(directory, 'consumer.ts'), consumer)
  const declarations = declarationFiles.map(path => join(installed, 'dist', path))
  for (const [module, moduleResolution, files] of [
    ['Node16', 'Node16', ['consumer.mts', 'consumer.cts']],
    ['NodeNext', 'NodeNext', ['consumer.mts', 'consumer.cts']],
    ['ESNext', 'Bundler', ['consumer.ts']],
    ['ESNext', 'Node', ['consumer.ts']],
  ]) {
    run(process.execPath, [tsc, '--noEmit', '--strict', '--skipLibCheck', 'false',
      '--target', 'ES2022', '--module', module, '--moduleResolution', moduleResolution,
      ...files, ...declarations])
  }
  console.log('Packed client declarations passed all consumer resolution checks.')
} finally {
  await rm(directory, { recursive: true, force: true })
}
