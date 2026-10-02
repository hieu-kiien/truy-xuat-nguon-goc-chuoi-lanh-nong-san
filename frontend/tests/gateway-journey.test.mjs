import test from 'node:test'
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { createRequire } from 'node:module'
const { canonicalizeJson, verifyHashChain } = createRequire(import.meta.url)('../../backend/benchmark/integrity_benchmark.js')
import { gatewayPosition, gatewayProgressPath, gatewayProgressAt, gatewayTemperature } from '../src/domain/gatewayJourney.ts'
import { calculateDemoHashChain, JOURNEY_STAGES } from '../src/domain/demoScenario.ts'

test('route projection and prefix track the same parcel, including segment boundaries', () => {
  assert.deepEqual([0, 1 / 3, 2 / 3, 1].map(gatewayPosition), [
    { x: 60, y: 234 }, { x: 230, y: 115 }, { x: 410, y: 235 }, { x: 580, y: 70 },
  ])
  for (let index = 1; index <= 300; index++) {
    const progress = index / 300
    const point = gatewayPosition(progress)
    assert.ok(Math.abs(gatewayProgressAt(point.x, point.y) - progress) <= 1 / 240)
    const numbers = gatewayProgressPath(progress).match(/-?\d+(?:\.\d+)?(?:e[-+]?\d+)?/gi).map(Number)
    assert.ok(Math.abs(numbers.at(-2) - point.x) < 1e-8)
    assert.ok(Math.abs(numbers.at(-1) - point.y) < 1e-8)
  }
  assert.deepEqual(gatewayPosition(-1), gatewayPosition(0))
  assert.deepEqual(gatewayPosition(2), gatewayPosition(1))
})

test('temperature interpolation changes only the transport scenario and preserves endpoints', () => {
  for (const excursion of [false, true]) {
    const values = [14.2, 7.6, excursion ? 9.9 : 3.5, 4]
    values.forEach((value, index) => assert.equal(gatewayTemperature(index / 3, excursion), value))
    for (let step = 0; step <= 300; step++) {
      const value = gatewayTemperature(step / 300, excursion)
      assert.ok(Number.isFinite(value) && value >= 3.5 && value <= 14.2)
    }
  }
})

test('actual SHA-256 distinguishes excursions, payload tampering and downstream ancestry', async () => {
  const fixture = JSON.stringify(JOURNEY_STAGES)
  for (const temperatureExcursion of [false, true]) {
    for (const tampered of [false, true]) {
      const blocks = await calculateDemoHashChain({ tampered, temperatureExcursion })
      assert.equal(verifyHashChain(blocks.map((block) => ({ ...block.payload, hash: block.recordedHash }))), !tampered)
      blocks.forEach((block, index) => {
        assert.equal(block.canonicalPayload, canonicalizeJson(block.payload), 'matches repository canonicalization logic')
        assert.equal(block.computedHash, createHash('sha256').update(block.canonicalPayload).digest('hex'))
        assert.equal(block.recordedHash, createHash('sha256').update(block.originalCanonicalPayload).digest('hex'))
        assert.equal(block.hashMatches, !(tampered && index === 2))
        assert.equal(block.ancestryValid, !(tampered && index >= 2))
      })
      assert.equal(blocks[2].sourceTemperature, temperatureExcursion ? 9.9 : 3.5)
      assert.equal(blocks[2].payload.temp_c, tampered ? 99.9 : blocks[2].sourceTemperature)
      assert.equal(blocks[3].previousHash, blocks[2].recordedHash)
    }
  }
  assert.equal(JSON.stringify(JOURNEY_STAGES), fixture, 'simulations must not mutate source fixtures')
  const reset = await calculateDemoHashChain({ tampered: false, temperatureExcursion: false })
  assert.ok(reset.every((block) => block.hashMatches && block.ancestryValid))
})
