# LangGraph → Playwright-CLI runner

This small framework reads a plain-text scenario (one step per line), looks up existing mappings in `playwright-cli-steps-library.txt`, and executes matching `npx playwright-cli` commands. Missing steps trigger `npx playwright-cli snapshot` to discover locators and attempt to build and run an appropriate command; successful discoveries are added to the steps library.

Usage

1. Install node, npx and Playwright CLI in your project.
2. (Optional) create a scenario file, e.g. `scenario.txt` with one natural-language step per line.
3. Run:

```bash
python cli.py scenario_example.txt
```

Files
- `cli.py`: CLI entrypoint
- `langgraph_framework/step_library.py`: read/update library
- `langgraph_framework/executor.py`: run commands and snapshot parsing
- `langgraph_framework/runner.py`: orchestrator
- `playwright-cli-steps-library.txt`: steps database (CSV of two quoted fields)

Notes and limitations
- The snapshot locator extraction uses heuristics — results depend on your `npx playwright-cli snapshot` output format.
- The action detection is simple (navigate/type/click); you may extend `Executor.build_command_for_step` for richer parsing.
