import test from 'node:test'
import assert from 'node:assert/strict'
import { inspectJourney, stageProgress } from '../src/domain/journeyModel.ts'
import { JOURNEY_STAGES } from '../src/domain/demoScenario.ts'
import { digestDiff } from '../src/domain/digestDiff.ts'

test('cursor uses actual timestamp spacing and lands at the exact recorded samples', () => {
  assert.deepEqual(JOURNEY_STAGES.map((_, index) => stageProgress(index)), [0, .28125, .5625, 1])
  JOURNEY_STAGES.forEach((stage, index) => {
    const view = inspectJourney(stageProgress(index), false)
    assert.equal(view.nearest, index)
    assert.equal(view.interpolated, false)
    assert.equal(view.timestamp, Date.parse(stage.timestamp))
    assert.equal(view.temperature, stage.temperature)
    assert.equal(view.humidity, stage.humidity)
    assert.equal(view.routeProgress, index / 3)
  })
  const midway = inspectJourney((stageProgress(1) + stageProgress(2)) / 2, false)
  assert.equal(midway.interpolated, true)
  assert.equal(midway.timestamp, Date.parse('2026-09-30T09:22:30Z'))
  assert.ok(Math.abs(midway.temperature - (7.6 + 3.5) / 2) < 1e-9)
  assert.equal(inspectJourney(-1, false).progress, 0)
  assert.equal(inspectJourney(2, false).progress, 1)
})

test('digest comparison counts actual hex and bit differences', () => {
  assert.equal(digestDiff('0'.repeat(64), '0'.repeat(64)).changedBits, 0)
  const all = digestDiff('0'.repeat(64), 'f'.repeat(64))
  assert.equal(all.changedBits, 256)
  assert.equal(all.changedHex, 64)
  const one = digestDiff('0'.repeat(64), '0'.repeat(63) + '1')
  assert.equal(one.changedHex, 1)
  assert.equal(one.changedBits, 1)
  assert.throws(() => digestDiff('fake', 'placeholder'))
})
