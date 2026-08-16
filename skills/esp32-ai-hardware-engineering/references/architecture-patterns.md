# ESP32 AI Hardware Architecture Patterns

## Contents

1. [Start From Constraints](#1-start-from-constraints)
2. [Main-Task Single Writer](#2-main-task-single-writer)
3. [State Legality and Side Effects](#3-state-legality-and-side-effects)
4. [Compile-Time Hardware Product Line](#4-compile-time-hardware-product-line)
5. [Capability Interfaces and Null Objects](#5-capability-interfaces-and-null-objects)
6. [Bounded Realtime Queues](#6-bounded-realtime-queues)
7. [Task-Owned Drivers](#7-task-owned-drivers)
8. [Generation Guards](#8-generation-guards)
9. [Protocol Semantics and Transport Strategies](#9-protocol-semantics-and-transport-strategies)
10. [Schema-Driven Device Tools](#10-schema-driven-device-tools)
11. [Separate Lifecycles](#11-separate-lifecycles)
12. [C++ Ownership Rules](#12-c-ownership-rules)
13. [Warning Signs](#13-warning-signs)

## 1. Start From Constraints

Capture these before selecting an architecture:

| Constraint | Required decision |
|---|---|
| Chip and ESP-IDF | target, supported SDK range, component compatibility |
| Memory | flash, internal RAM, PSRAM, largest transient allocation |
| Timing | audio frame duration, end-to-end latency, blocking limits |
| Hardware | codec, microphones, reference channel, display, camera, power |
| Network | Wi-Fi/cellular/Ethernet, reconnect behavior, transport |
| Lifecycle | OTA identity, partition layout, NVS schema, asset format |
| Validation | host tests, build targets, available physical boards |

Do not inherit queue sizes, task priorities, stack sizes, or PSRAM assumptions from another board.

## 2. Main-Task Single Writer

Choose one task as the writer of device-level state. Network, audio, button, timer, and driver callbacks publish event bits or bounded commands.

Use when multiple asynchronous sources coordinate UI, protocol, session, and power behavior.

Require:

- Short, non-blocking main-loop handlers.
- Bounded command storage or command coalescing.
- Captures with proven lifetime.
- An assertion or documented API boundary preventing off-task mutation.

Avoid treating a mutex around every application method as an equivalent design; it does not define event order or prevent callbacks under lock.

## 3. State Legality and Side Effects

Separate three operations:

1. Validate `from -> to` against a state graph.
2. Commit the new state atomically under the single-writer rule or one transaction lock.
3. Publish a state-changed event; execute UI, audio, and protocol effects from the owning context.

Test legal and illegal transitions independently from side effects. Never execute side effects before the transition commits.

## 4. Compile-Time Hardware Product Line

Prefer one selected board implementation per firmware image:

```text
variant metadata -> Kconfig -> CMake/component rules -> board source -> one factory
```

Keep core code dependent on capability interfaces, never concrete board headers or pins.

Treat these as one consistency chain:

- Directory/variant name.
- Reported board type and release name.
- Chip target and SDK constraints.
- Flash and partition settings.
- Kconfig symbol and CMake source selection.
- Exactly one board factory.

Add a new variant when pins or compatibility identity differ. Limited runtime revision detection is acceptable only inside one stable product identity.

## 5. Capability Interfaces and Null Objects

Use a Null Object when absence has a natural no-op meaning and callers should not branch, such as an optional status display or LED.

Use `nullptr`, `optional`, or a capability flag when absence changes protocol advertisement, workflow, or error handling, such as a camera or battery monitor.

Fail initialization when the capability is mandatory for the selected product. A Null Object must not hide an invalid build configuration.

## 6. Bounded Realtime Queues

Specify capacity in time or bytes, then derive item count.

| Stream | Typical full policy | Reason |
|---|---|---|
| Microphone frames | Drop oldest | stale realtime audio has low value; producer must not block |
| Network send audio | Drop oldest and count | preserve current speech under congestion |
| Playback decode input | Bounded wait or reject | caller may apply backpressure |
| UI commands | Coalesce latest | intermediate brightness/status values may be obsolete |
| Control commands | Reject with visible error | silent loss may violate device state |

For every queue record capacity, producer, consumer, whether producer may block, full policy, shutdown wakeup, high-water mark, and drop/error counters.

Log outside realtime locks and rate-limit repeated diagnostics.

## 7. Task-Owned Drivers

Assign non-thread-safe or blocking drivers to one task. Other contexts update atomic intent, event bits, or a command queue. The owner applies changes at documented safe points.

Use for AFE fetch/reset/control, I2S lifecycle, display rendering, camera pipelines, modem AT state, and shared SPI devices.

Do not hold a general mutex across an indefinitely blocking driver call. That can make stop/reset wait forever.

## 8. Generation Guards

Use a monotonically increasing generation when stop, reconnect, reset, or mode changes cannot cancel in-flight work.

```cpp
class SessionGate {
public:
    uint32_t BeginWork() const { return generation_.load(); }

    void Invalidate() { generation_.fetch_add(1); }

    bool IsCurrent(uint32_t captured) const {
        return captured == generation_.load();
    }

private:
    std::atomic<uint32_t> generation_{0};
};

const auto generation = gate.BeginWork();
auto decoded = DecodeBlocking(packet);
if (gate.IsCurrent(generation)) {
    playback_queue.Push(std::move(decoded));
}
```

Invalidate before clearing old queues. Check again immediately before committing the result. This rejects stale work; it does not by itself make captured object pointers safe.

## 9. Protocol Semantics and Transport Strategies

Place message meaning in one shared protocol layer: start/stop listening, abort, wake word, session lifecycle, MCP payloads, and capability advertisement.

Transport implementations own connection, framing, encryption, QoS, reconnect, and binary audio packaging.

Use one parser/validator for shared incoming JSON whenever possible. Apply equivalent type, range, size, session, and authentication checks to every transport. A shared semantic change requires tests for all transports.

## 10. Schema-Driven Device Tools

Register tools with name, description, typed properties, bounds/defaults, permission/audience, and callback. Validate the full request before scheduling a side effect.

Require:

- Stable names and versioning policy.
- Bounded/paginated tool listing.
- Typed arguments with range and required-field checks.
- Explicit execution context.
- Structured error results.
- Clear confirmation policy for sensitive actions.

Prefer RAII/value ownership for JSON trees and tool results. Avoid mixing raw owning pointers into variants.

## 11. Separate Lifecycles

Manage firmware, assets, NVS configuration, credentials, and board identity separately.

- Firmware: signed OTA, rollback, compatible partition.
- Assets: independent partition, format version, firmware compatibility.
- NVS: schema version, migration, commit behavior, reset semantics.
- Identity: stable board type/name/UUID used by OTA and backend routing.

Changing an NVS key, board name, protocol field, partition label, or asset format is an API migration, not a local rename.

## 12. C++ Ownership Rules

- Use `unique_ptr` and move semantics for single-owner packets and tasks.
- Use RAII for locks, NVS handles, JSON values, codec handles, and task cleanup.
- Use atomics for individual flags/counters, not multi-field invariants.
- Use `function`/lambdas at asynchronous boundaries only with deliberate capture lifetime and allocation cost.
- Use `variant`/`optional` for valid alternatives; do not hide ownership in a raw-pointer alternative.
- Measure heap churn and code size before using allocation-heavy abstractions in audio hot paths.

## 13. Warning Signs

Stop and redesign when you see:

- Board pins or concrete board headers in core modules.
- An unbounded `deque`, `queue`, callback list, or scheduler backlog.
- A driver called from multiple tasks because it is "protected by a mutex."
- Stop/reset that clears queues but cannot reject in-flight results.
- Shared protocol behavior copied into each transport.
- Persistent keys or board identities renamed without migration.
- A successful firmware build presented as proof of hardware behavior.

## XiaoZhi Provenance

These patterns were distilled from the local XiaoZhi snapshot at `%USERPROFILE%\Desktop\AI-HRADWARE\xiaozhi-esp32` (commit `8e2899d`). Use it as evidence and comparison material, not a drop-in template. The human-readable study is `%USERPROFILE%\Desktop\AI-HRADWARE\docs\architecture\xiaozhi-esp32-engineering-playbook.md`.
