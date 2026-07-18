# Understand Video conflict matrix

| Conflict or ambiguity | Resolution |
|---|---|
| The initial request says to build, while TEMPO requires a separate human warrant | Complete source analysis, business artifacts, readiness, and the bounded cheaper experiment; do not edit product implementation paths until an interactive human signs the charter and issues the warrant. |
| The requested Rank-1 claim is a learning-outcome claim, but no learner study exists | Keep it as an untested Rank-1 hypothesis. A graph-to-video feasibility experiment may reduce technical uncertainty but cannot prove faster learning. |
| Build Week FAQ says “3 minutes or under”; official rules say “less than three minutes” | Follow the stricter official rules: enforce `< 180000 ms`; target 165000 ms and cap at 179000 ms. |
| The product fits Developer Tools and Education | Select Developer Tools because the primary user is a developer working with repositories; preserve educational value as the use case. |
| The requested native integration could copy upstream code | Consume the graph contract through a modular package and preserve MIT notice. Record every reused/modified upstream file; initially none. |
| TEMPO is Python while Understand-Anything is TypeScript | Keep TEMPO in its own repository as an external governance dependency. Add product code here as a TypeScript workspace only after authorization; never vendor or port the TEMPO kernel. |
| The upstream sample graph is not fresh at the selected commit | Use it only for the explicitly bounded feasibility experiment. Strict architecture/hackathon generation must require a fresh graph bound to the exact target commit. |
| GPT-5.6 must be a runtime product feature, but the current task uses GPT-5.6 as the build model | Implement a provider boundary and schema-only storyboard output after authorization. Build-time use is real but does not substitute for the runtime role required by this product brief. |
| A real voice is required, but external TTS is an outward and potentially billable action | Implement and test fixture/local boundaries after authorization; require a valid warrant, provider declaration, character/cost cap, and separate human authority before a real external speech call. |
| The final video is requested but publishing is forbidden | Render and verify locally after authorization; never upload to YouTube or submit to Devpost without a separate explicit human action. |
