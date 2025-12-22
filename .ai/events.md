# Canonical Events Vocabulary

Events drive Phase 1 (streaks, challenges, coach). Each event must be idempotent and free of side effects in handlers.

## post.generated
- Payload: { userId, platform, prompt, draftId, archetype?, valuesMode? }
- Source: backend (generation), workflow
- Side-effect rules: Handlers may log, score, or enqueue; must not post or mutate streaks directly.
- Idempotency: keyed by draftId.

## post.posted
- Payload: { userId, platform, postId, contentRef, postedAt }
- Source: backend (posting), workflow
- Side-effect rules: Can advance streaks, emit analytics; must not double-award on retry.
- Idempotency: keyed by postId.

## post.scheduled
- Payload: { userId, platform, postId?, scheduledFor, contentRef }
- Source: backend (schedule), workflow
- Side-effect rules: No streak changes until posted; can schedule reminders.
- Idempotency: keyed by contentRef+scheduledFor.

## streak.incremented
- Payload: { userId, streakDay, reason: 'post'|'challenge', protectionUsed?: boolean }
- Source: streak service
- Side-effect rules: No additional streak mutations; emit analytics only.
- Idempotency: keyed by userId+streakDay.

## streak.missed
- Payload: { userId, missedDay, protectionAvailable?: boolean }
- Source: streak service
- Side-effect rules: Do not retro-break; handlers may trigger recovery prompts.
- Idempotency: keyed by userId+missedDay.

## challenge.assigned
- Payload: { userId, challengeId, type, assignedAt, dueAt }
- Source: challenges service, Temporal
- Side-effect rules: Do not increment streak; can enqueue reminders.
- Idempotency: keyed by userId+challengeId+assignedAt.

## challenge.completed
- Payload: { userId, challengeId, completedAt, result: 'full'|'partial', ringEarned? }
- Source: challenges service
- Side-effect rules: Can increment streaks and momentum; must not double-award.
- Idempotency: keyed by userId+challengeId+completedAt.

## coach.feedback_generated
- Payload: { userId, draftId, scores, suggestions, warnings }
- Source: coach service
- Side-effect rules: Must not auto-post or change streak counts; can influence confidence signals.
- Idempotency: keyed by draftId.
