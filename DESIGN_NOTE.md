# Design note: reducing manual review of dashcam alerts

**Setting.** 500 trucks raise about 2,000 events a day, and about 40% (800) are false alarms. The goal is
less human review **without missing serious events**. So the system should decide what a person needs to
look at, and how soon. It should not decide that safety events do not matter.

## Approach

1. **Sort events by severity first, using fixed rules.** Each event type gets a tier, agreed with the
   safety team. *Serious* covers phone use at speed, close following at high speed, harsh braking with a
   near miss, drowsiness and any collision. *Low* covers phone use while parked and short close-following
   at low speed. *Device* covers a blocked or failed camera. Serious events always go to a person, whatever
   any model says. Device events go to maintenance, not the safety queue.
2. **Group repeats.** One behaviour often raises a burst of events: the same driver, type and trip within a
   few minutes. Group them so a reviewer sees one item with all its clips.
3. **Use context.** Speed, GPS (yard or highway), time of day and the vehicle's recent events, from data
   we already have. A phone event at 0 mph in a depot is not the same as one at 65 mph.
4. **Add a second model that judges false alarms.** It looks at the clip and that context and gives the
   probability that this is a false alarm. Common causes are glare, a passenger, a hand near the face, or
   a sticker on the lens. Its score only reorders the queue or **auto-closes low-tier events** when it is
   very sure. Every auto-closed event stays searchable, with its clip.
5. **Order the review queue by risk,** so serious and likely-real events are seen first. A short summary
   per item (type, speed, location, a still image) speeds up each review.

## Labelled data

- **Source:** past reviewer decisions, roughly 2,000 a day already, each with its clip and telematics.
- **Labels to record:** real or false alarm; for false alarms, a reason code (glare, passenger, object,
  sensor fault); severity as judged by the reviewer; and the action taken (none, coaching, escalated).
  Reason codes show which false alarms can be fixed in the device instead of by review.
- **Quality:** two reviewers label a weekly sample to measure agreement. A fixed *gold set* is checked by a
  senior reviewer. Serious events get a second look, because a mislabelled serious event teaches the
  model to miss it.
- **Splits:** by time, and by vehicle or driver, so the test set has days and trucks the model never saw.
  Report results by event type, camera model, day or night, and weather.

## Metrics

- **Primary, as a guardrail: recall on serious events.** It must stay at about 99% or higher, with a
  confidence interval, per event type. Serious events are rare, so this needs a large held-out set.
- **For auto-closed events: the miss rate,** meaning how many auto-closed events were actually real.
  It is measured through a random audit (see rollout).
- **Workload:** events reaching a person per day, and minutes spent per reviewed event.
- **Speed:** time from the event to a reviewer seeing it, for serious events.
- **Calibration:** whether a 0.9 false-alarm score is right about 90% of the time. The thresholds depend on it.

Thresholds are set from the held-out data so that the guardrail is met first. Workload reduction comes
second. For example, if half of the 800 daily false alarms are low-tier and the model is very sure about
them, about 400 events a day (20%) leave the queue. Grouping repeats would add to that. These are targets
to check against real data, not promises.

## Rollout

1. **Shadow mode, 3 to 4 weeks.** The model scores every event and people still review everything.
   We compare the two and pick thresholds.
2. **Reorder the queue only.** Nothing is closed automatically yet, so there is no risk of a miss.
   We measure the time saved.
3. **Auto-close one low-tier event type** for a subset of the fleet, with a **random audit of 5 to 10% of
   auto-closed events** reviewed by a person. Expand by event type and fleet only while the audit shows
   misses below the agreed limit.
4. A **kill switch** that sends every event back to manual review within minutes.

## Catching performance dropping over time

- **The audit is the main signal.** The weekly miss rate from the random audit of auto-closed events,
  with an alert when it passes the limit.
- **Reviewer overrides.** How often people disagree with the model on the events they still review.
- **Input drift.** Event rate per truck, score distribution and auto-close rate, split by camera model,
  firmware version, route, day or night and season. Winter glare, new truck models and firmware updates
  all change what the camera sees.
- **Change triggers.** A firmware update, a new vehicle type or a new customer fleet triggers a re-check on
  recent labelled data before auto-close stays on for that segment.
- **Retraining** on fresh labels on a fixed schedule, for example monthly. Each new model must beat the
  current one on the gold set and on the latest weeks before it ships.
