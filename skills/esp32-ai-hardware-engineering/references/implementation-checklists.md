# ESP32 AI Hardware Implementation Checklists

## Contents

1. [Context and Baseline](#1-context-and-baseline)
2. [Architecture and Concurrency](#2-architecture-and-concurrency)
3. [Board or BSP Changes](#3-board-or-bsp-changes)
4. [Audio Changes](#4-audio-changes)
5. [Protocol and MCP Changes](#5-protocol-and-mcp-changes)
6. [NVS, OTA, Partitions, and Assets](#6-nvs-ota-partitions-and-assets)
7. [Kconfig, CMake, and Build Matrix](#7-kconfig-cmake-and-build-matrix)
8. [Implementation Review](#8-implementation-review)
9. [Verification Ladder](#9-verification-ladder)
10. [Completion Report](#10-completion-report)

Use only the sections relevant to the current task, plus Context, Implementation Review, Verification Ladder, and Completion Report.

## 1. Context and Baseline

- [ ] Read the closest `AGENTS.md` and authoritative project docs.
- [ ] Inspect the nearest existing implementation before designing a new one.
- [ ] Record chip target, exact board/variant, ESP-IDF version, and component versions.
- [ ] Record flash, RAM/PSRAM, partition, peripheral, network, and power constraints.
- [ ] Check worktree status and preserve unrelated changes.
- [ ] Identify generated/vendor/build outputs that must not be edited.
- [ ] Run the smallest relevant baseline test/build before changing behavior.
- [ ] State which physical board and instruments are available.

## 2. Architecture and Concurrency

- [ ] Name the narrowest owning module for the change.
- [ ] Name the sole writer for every changed device-level state.
- [ ] List callback/task/ISR contexts that enter the changed code.
- [ ] Route cross-context mutations through event bits or bounded commands.
- [ ] Define legal state transitions separately from transition effects.
- [ ] Define each queue's producer, consumer, capacity, blocking rule, and full policy.
- [ ] Keep blocking IO, codec work, and allocation bursts out of the main event loop.
- [ ] Assign non-thread-safe drivers to one owner task.
- [ ] Avoid holding locks across driver calls, logging, callbacks, or unbounded waits.
- [ ] Add generation/epoch invalidation for stale in-flight work.
- [ ] Define shutdown order and wake every blocked task/condition variable.
- [ ] Add counters for queue drops, high-water marks, timeouts, and recovery.

## 3. Board or BSP Changes

- [ ] Add a unique board or release variant when pins/hardware identity differ.
- [ ] Do not change an existing board's pins to support unrelated hardware.
- [ ] Update the complete metadata -> Kconfig -> CMake -> source selection chain.
- [ ] Export exactly one board factory.
- [ ] Keep concrete board headers/configuration out of core modules.
- [ ] Mark every capability as required, optional with Null Object, or optional with explicit absence.
- [ ] Verify no-display, no-camera, no-battery, and other absent-capability paths as applicable.
- [ ] Verify GPIO boot strapping, pull state, active level, interrupt mode, and power-up order.
- [ ] Verify I2C addresses and bus pullups; verify I2S slot/clock/channel/sample format.
- [ ] Check target-specific PSRAM, DMA, cache, and peripheral restrictions.
- [ ] Preserve board identity used by OTA/backend compatibility.
- [ ] Document wiring, flash size, partitions, and canonical build command.

## 4. Audio Changes

- [ ] Draw capture -> preprocess -> encode -> transport -> decode -> playback.
- [ ] Express buffer capacity as milliseconds and calculate memory cost.
- [ ] Define full behavior for input, encode, send, decode, and playback queues.
- [ ] Keep microphone/AFE producer paths non-blocking unless timing proof allows blocking.
- [ ] Identify the owner of codec, I2S, AFE, AEC, VAD, and wake-word operations.
- [ ] Reject pre-stop/pre-reset/pre-reconnect frames with generation checks.
- [ ] Verify sample rate, bit depth, channel order, reference channel, and frame duration end to end.
- [ ] Verify resampler and codec state changes cannot race processing.
- [ ] Rate-limit realtime-path logging and perform it outside locks.
- [ ] Measure task stack high-water marks, heap/PSRAM, queue high water, drops, and latency.
- [ ] Test capture, playback, wake word, VAD, interruption, reconnect, and all applicable AEC modes.
- [ ] Listen for clipping, underrun, repeated frames, stale playback, and acoustic feedback on hardware.

## 5. Protocol and MCP Changes

- [ ] Put shared message meaning in the protocol layer, not a transport implementation.
- [ ] Verify every affected transport, including WebSocket and MQTT/UDP where present.
- [ ] Validate parse result, root shape, required fields, type, range, size, and session identity.
- [ ] Bound incoming JSON/binary payload and decompressed/decoded sizes.
- [ ] Define reconnect, duplicate, out-of-order, goodbye, and timeout behavior.
- [ ] Preserve buffer/JSON ownership through callbacks and asynchronous scheduling.
- [ ] Give every MCP tool a stable name, typed schema, bounds/defaults, and audience/permission.
- [ ] Validate all MCP arguments before any hardware side effect.
- [ ] Schedule tool execution on the correct owner task.
- [ ] Bound or paginate tool listing and large tool responses.
- [ ] Return structured errors without leaking credentials or unsafe internals.
- [ ] Test malformed, oversized, missing, unknown, duplicate, and stale-session messages.

## 6. NVS, OTA, Partitions, and Assets

- [ ] Treat NVS namespace/key names as persistent API.
- [ ] Add schema version and migration for renamed or retyped settings.
- [ ] Test set, overwrite, erase key, erase all, commit failure, and power-loss behavior.
- [ ] Avoid excessive flash writes; make transaction boundaries explicit.
- [ ] Keep credentials and private device identity out of logs.
- [ ] Preserve OTA board identity and compatible version rules.
- [ ] Verify OTA download, hash/signature, partition capacity, rollback, and interrupted update.
- [ ] Version asset formats independently from firmware.
- [ ] Validate asset size before flash and compatibility before mmap/use.
- [ ] Test missing, corrupt, older, and newer asset partitions.
- [ ] Confirm factory reset behavior for configuration, credentials, identity, and assets separately.

## 7. Kconfig, CMake, and Build Matrix

- [ ] Guard target-specific code with Kconfig and component requirements.
- [ ] Keep defaults in one authoritative place and validate user overrides.
- [ ] Ensure configuration selects all required dependencies and excludes incompatible ones.
- [ ] Ensure source selection cannot link zero or multiple board factories.
- [ ] Validate duplicate board identities, release names, and artifact names.
- [ ] Keep generated headers/assets reproducible; never hand-edit them.
- [ ] Test build tooling as code, including invalid configuration diagnostics.
- [ ] Build affected variants, plus representative chip/network/display/resource paths for shared changes.
- [ ] Record the exact SDK environment and canonical build command.
- [ ] Do not assume a reused build directory still represents the previous target.

## 8. Implementation Review

- [ ] The patch changes only the narrowest owning layer.
- [ ] No board-specific condition leaked into core code.
- [ ] No new unbounded queue, retry loop, allocation growth, or callback backlog exists.
- [ ] Ownership is visible in types (`unique_ptr`, values, RAII) rather than comments alone.
- [ ] Atomic variables are not used as a substitute for a compound invariant transaction.
- [ ] Callback captures remain valid across disconnect, stop, destroy, and reconnect.
- [ ] Error paths release locks, buffers, handles, and JSON trees exactly once.
- [ ] Logs are actionable, rate-limited where needed, and contain no secrets.
- [ ] Compatibility changes include migrations or explicit release boundaries.
- [ ] Tests cover invariants and failure modes, not only implementation details.

## 9. Verification Ladder

Run the highest applicable layers; do not collapse their meaning.

1. Static checks: formatting, configuration validation, generated-file consistency.
2. Host tests: state graph, parsers, build tooling, schemas, queue policies, migrations.
3. Component/build checks: exact affected variant and representative shared paths.
4. Flash/boot smoke test: partition, initialization, peripheral discovery, basic UI/audio.
5. Functional hardware test: real microphone/speaker/network/display/camera/power behavior.
6. Stress/fault test: congestion, reconnect, rapid mode changes, low memory, corrupt input, OTA interruption.
7. Long-run test: thermal behavior, heap stability, task stacks, reconnect recovery, flash wear signals.

For every command record exact result, warnings, skipped cases, and environment. A test cleanup error is not a pass; a compile is not a functional hardware test.

## 10. Completion Report

Report:

- Files and owning modules changed.
- Invariants added or preserved.
- Exact host/static/build commands and results.
- Exact board/variant/SDK used.
- Physical behaviors tested and observed.
- Queue, memory, stack, timing, and drop measurements when relevant.
- Unavailable hardware paths and untested variants/transports.
- Compatibility/migration impact for board identity, protocol, NVS, partitions, and assets.
- Remaining risks and the next concrete validation action.
