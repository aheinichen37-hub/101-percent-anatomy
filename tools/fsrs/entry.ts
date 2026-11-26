// 101% Anatomy: the FSRS-6 scheduler only, built synchronously from ts-fsrs (see build.mjs).
// Mirrors DefaultScheduler({version: 'FSRS-6'}) in ts-fsrs 6.0.1, minus the async loading of other models.
import { defineScheduler, schedulerStatsMiddleware } from '@open-spaced-repetition/srs-kit'
import { dateChrono } from '@open-spaced-repetition/srs-kit/chrono/date'
import { schedulerDesiredRetentionMiddleware } from '@/middlewares/desired-retention/middleware.js'
import { schedulerFuzzingMiddleware } from '@/middlewares/fuzzing/middleware.js'
import { schedulerLearningStepsMiddleware } from '@/middlewares/learning-steps/middleware.js'
import { defaultLearningSteps, defaultRelearningSteps } from '@/middlewares/learning-steps/schema.js'
import { schedulerMaximumIntervalMiddleware } from '@/middlewares/maximum-interval/middleware.js'
import { schedulerMonotonicIntervalMiddleware } from '@/middlewares/monotonic-interval/middleware.js'
import { schedulerScheduledDaysMiddleware } from '@/middlewares/scheduled-days/middleware.js'
import { FSRS6Model, migrateFSRS6Parameters } from '@/models/fsrs-6/index.js'
export { Rating, State } from '@/index.js'

const definition = (defineScheduler as any)({ model: FSRS6Model, chrono: dateChrono }).use(
  schedulerDesiredRetentionMiddleware, schedulerFuzzingMiddleware, schedulerStatsMiddleware,
  schedulerScheduledDaysMiddleware, schedulerLearningStepsMiddleware,
  schedulerMaximumIntervalMiddleware, schedulerMonotonicIntervalMiddleware)

export function createFSRS6(o: { desiredRetention?: number; maximumInterval?: number; enableShortTerm?: boolean; enableFuzz?: boolean } = {}) {
  const enableShortTerm = o.enableShortTerm ?? true
  const relearningSteps = Array.from(defaultRelearningSteps)
  return definition.create({ config: {
    fractionalDays: false,
    weights: migrateFSRS6Parameters(undefined, relearningSteps.length, enableShortTerm),
    enableShortTerm, numRelearningSteps: relearningSteps.length,
    desiredRetention: o.desiredRetention ?? 0.9,
    learningSteps: Array.from(defaultLearningSteps), relearningSteps,
    allowModelOverride: false, enableFuzz: o.enableFuzz ?? false,
    maximumInterval: o.maximumInterval ?? 36500,
  } })
}
