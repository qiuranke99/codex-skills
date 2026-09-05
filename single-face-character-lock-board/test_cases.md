# Single-Face Character Lock Board: Acceptance Scenarios

Use these scenarios when maintaining the workflow. They are review examples,
not evidence that a model or image tool has executed successfully.

| Input or event | Expected behavior |
| --- | --- |
| One selected identity, no collaboration tools or local Codex database | Use the available image tool directly; those unrelated capabilities do not block generation. |
| Two different people without a selected identity | Ask which identity to preserve; do not blend or pick one. |
| One person plus another person's outfit reference | Identity stays with the selected person; the second source controls only assigned wardrobe. |
| References exist only as supported conversation images | Inspect them and use the current tool's supported reference mechanism; do not invent local paths. |
| Tool returns an accessible completed image in the current turn | Inspect and finish the authorized prompt-pair delivery without requesting another user message. |
| Tool or host actually requires continuation | Preserve the pending attempt; resume when its result is available and do not claim QA or completion early. |
| Unrelated images are created concurrently | Bind the result to its actual call response; never choose by newest timestamp. |
| A second face appears in a printed shirt, reflection, or body panel | Fail topology QA; allow the bounded focused repair. |
| Front or back view crops a foot | Repair or reject; a good bust does not compensate for incomplete body views. |
| Back garment details are not visible in the sources | Mark inference or missingness; do not claim those details verified. |
| Source-faithful board returns a nearby raster ratio | Record actual dimensions; ratio alone does not trigger content repair or a native-4K claim. |
| Accepted repair follows a rejected first image | Deliver the accepted image with that attempt's exact generation prompt and hash. |
| Enhancement is drafted before inspecting the board | It remains a draft; do not claim observed defects or publish it as image-specific. |
| Final sidecar hash differs from the saved value | Report the mismatch; do not reconstruct the prompt from memory. |
| User requests complete prompts as files | Deliver the actual complete files in that format; retain their computed hashes and the real board. |
| External provider controls or original references are missing | Deliver the prepared prompt with limits; external readiness and verification remain false. |
| Visual QA passes but no production approval exists | Deliver the reviewed board; do not promote it into approved project authority. |

The default final result shows the real board, complete accepted generation
and enhancement prompts, their hashes, observed dimensions, QA, and external
readiness. No image-only, invented-provenance, or promised-inspection result
counts as complete. A future runtime smoke test must observe these events;
this document itself cannot prove them.
