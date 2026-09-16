# Hermes Context Contract

Hermes must not inject generated operational startup summaries or retired compatibility policy before the first model call.

Intentional context is limited to the harness/system contract, `SOUL.md`, enabled product memory/user-profile features, the current conversation/session, and project files explicitly read for the current task.

Historical startup snapshots, old scratchpads, project-status summaries, and host excerpts are not automatic model context. They may be inspected explicitly when the task requires them.

No plugin may silently replace a model's final response as a policy mechanism.
