#!/usr/bin/env node
import crypto from 'crypto'
import { promises as fs } from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

import sharp from 'sharp'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '..')
const assetsDir = path.join(projectRoot, 'src', 'assets')
const optimizedDir = path.join(assetsDir, 'optimized')
const cachePath = path.join(projectRoot, '.imgopt-cache.json')

const SOURCE_GLOB_EXT = ['.png', '.jpg', '.jpeg']
const TARGET_WIDTHS = [480, 768, 1024, 1440]
const FORMATS = [
  { key: 'webp', options: { quality: 72 } },
  { key: 'avif', options: { quality: 50 } },
]

async function readCache() {
  try {
    const raw = await fs.readFile(cachePath, 'utf8')
    return JSON.parse(raw)
  } catch {
    return {}
  }
}

async function writeCache(cache) {
  await fs.writeFile(cachePath, JSON.stringify(cache, null, 2))
}

async function* walk(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true })
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      yield* walk(fullPath)
    } else {
      yield fullPath
    }
  }
}

function shouldProcess(filePath) {
  const ext = path.extname(filePath).toLowerCase()
  if (!SOURCE_GLOB_EXT.includes(ext)) return false
  // Skip already optimized outputs
  if (path.relative(assetsDir, filePath).startsWith(`optimized${path.sep}`)) {
    return false
  }
  return true
}

function hashBuffer(buffer) {
  return crypto.createHash('sha1').update(buffer).digest('hex')
}

function outputBasename(relativePath) {
  const parsed = path.parse(relativePath)
  const withoutExt = path.join(parsed.dir, parsed.name).replace(/[/\\]+/g, '-')
  return withoutExt
}

async function processImage(filePath, cache) {
  const relative = path.relative(assetsDir, filePath)
  const buffer = await fs.readFile(filePath)
  const digest = hashBuffer(buffer)

  if (cache[relative]?.hash === digest) {
    return false
  }

  await fs.mkdir(optimizedDir, { recursive: true })

  const baseName = outputBasename(relative)
  const tasks = []
  for (const width of TARGET_WIDTHS) {
    const pipeline = sharp(buffer).resize({ width, fit: 'inside', withoutEnlargement: true })
    for (const format of FORMATS) {
      const targetPath = path.join(optimizedDir, `${baseName}-w${width}.${format.key}`)
      tasks.push(
        pipeline
          .clone()
          .toFormat(format.key, format.options)
          .toFile(targetPath)
      )
    }
  }

  await Promise.all(tasks)
  cache[relative] = { hash: digest, updatedAt: new Date().toISOString() }
  return true
}

async function main() {
  const cache = await readCache()
  let optimizedCount = 0
  for await (const filePath of walk(assetsDir)) {
    if (!shouldProcess(filePath)) continue
    const processed = await processImage(filePath, cache)
    if (processed) {
      optimizedCount += 1
      console.log(`Optimized ${path.relative(assetsDir, filePath)}`)
    }
  }
  await writeCache(cache)
  if (!optimizedCount) {
    console.log('All images already optimized.')
  }
}

main().catch((err) => {
  console.error('Image optimization failed:', err)
  process.exitCode = 1
})
