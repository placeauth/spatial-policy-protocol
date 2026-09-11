#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { jcs, rejectUnsupported, strictJsonParse } from "./verify_vectors.mjs";

const corpus = JSON.parse(readFileSync(process.argv[2] ?? new URL("./adversarial-corpus.json", import.meta.url), "utf8"));
const results = corpus.cases.map(({ id, source }) => {
  try {
    const parsed = strictJsonParse(source);
    rejectUnsupported(parsed);
    return { id, category: "accepted", canonical: jcs(parsed) };
  } catch (error) { return { id, category: "malformed", detail: String(error.message ?? error) }; }
});
console.log(JSON.stringify({ implementation: "node", results }));
