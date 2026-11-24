// Runs the Observable Framework CLI with its usage telemetry turned off,
// the same way on Windows, macOS and CI: `node observable.mjs build|preview`.
process.env.OBSERVABLE_TELEMETRY_DISABLE = "true";
process.argv = [process.argv[0], "observable", ...process.argv.slice(2)];
await import("@observablehq/framework/dist/bin/observable.js");
