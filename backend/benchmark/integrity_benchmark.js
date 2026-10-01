const { createHash } = require('node:crypto')
const { performance } = require('node:perf_hooks')

function canonicalizeJson(value) {
  if (value === null) return 'null'

  if (typeof value === 'string') return JSON.stringify(value)
  if (typeof value === 'boolean') return value ? 'true' : 'false'

  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      throw new TypeError('RFC 8785 does not allow NaN or Infinity')
    }
    if (Object.is(value, -0)) return '0'
    return JSON.stringify(value)
  }

  if (Array.isArray(value)) {
    return `[${value.map((item) => canonicalizeJson(item)).join(',')}]`
  }

  if (typeof value === 'object') {
    const entries = Object.keys(value)
      .sort()
      .map((key) => {
        const item = value[key]
        if (
          item === undefined ||
          typeof item === 'function' ||
          typeof item === 'symbol' ||
          typeof item === 'bigint'
        ) {
          throw new TypeError(`Value at key ${key} is not valid JSON`)
        }
        return `${JSON.stringify(key)}:${canonicalizeJson(item)}`
      })
    return `{${entries.join(',')}}`
  }

  throw new TypeError(`Unsupported JSON value type: ${typeof value}`)
}

function sha256(input) {
  return createHash('sha256').update(input, 'utf8').digest('hex')
}

function createEvents(count) {
  return Array.from({ length: count }, (_, index) => ({
    event_seq: index + 1,
    humidity_pct: 75 + (index % 10),
    lot_id: 'benchmark-lot-01',
    stage: index % 2 === 0 ? 'storage' : 'transport',
    temp_c: 3 + (index % 5) / 10,
    timestamp: new Date(Date.UTC(2026, 8, 30, 0, index)).toISOString(),
  }))
}

function buildHashChain(events) {
  let previousHash = '0'.repeat(64)
  return events.map((event) => {
    const payload = { ...event, prev_hash: previousHash }
    const hash = sha256(canonicalizeJson(payload))
    previousHash = hash
    return { ...event, prev_hash: payload.prev_hash, hash }
  })
}

function verifyHashChain(records) {
  let previousHash = '0'.repeat(64)
  for (const record of records) {
    if (record.prev_hash !== previousHash) return false
    const { hash, ...payload } = record
    if (sha256(canonicalizeJson(payload)) !== hash) return false
    previousHash = hash
  }
  return true
}

function runBenchmark(count = 1000) {
  const events = createEvents(count)

  const writeStart = performance.now()
  const chain = buildHashChain(events)
  const writeDurationMs = performance.now() - writeStart

  const verifyStart = performance.now()
  const isValid = verifyHashChain(chain)
  const verifyDurationMs = performance.now() - verifyStart

  const tampered = chain.map((record) => ({ ...record }))
  if (tampered.length > 0) {
    const index = Math.floor(tampered.length / 2)
    tampered[index].temp_c = 99.9
  }

  return {
    count,
    writeDurationMs,
    verifyDurationMs,
    isValid,
    detectedTamper: !verifyHashChain(tampered),
  }
}

module.exports = {
  canonicalizeJson,
  sha256,
  buildHashChain,
  verifyHashChain,
  runBenchmark,
}
