#!/usr/bin/env node
/*
 * Dependency-free JavaScript verifier for experimental admission-trust vectors.
 * It independently implements the deliberately limited Python JSON profile
 * described in README.md; it never invokes Python.
 */
import { createHash, createPublicKey, verify as verifySignature } from "node:crypto";
import { readFileSync } from "node:fs";

function strictJsonParse(source) {
  let index = 0;
  const whitespace = /[\x20\x09\x0a\x0d]/;
  const skip = () => { while (whitespace.test(source[index] ?? "")) index += 1; };
  const fail = (message) => { throw new Error(`invalid JSON at ${index}: ${message}`); };
  const string = () => {
    if (source[index] !== '"') fail("string expected");
    const start = index++;
    while (index < source.length) {
      const char = source[index++];
      if (char === '"') return JSON.parse(source.slice(start, index));
      if (char === "\\") {
        if (index >= source.length) fail("unfinished escape");
        const escaped = source[index++];
        if (escaped === "u") index += 4;
      } else if (char < " ") {
        fail("unescaped control character");
      }
    }
    fail("unterminated string");
  };
  const value = () => {
    skip();
    const char = source[index];
    if (char === "{") {
      index += 1;
      skip();
      const object = {};
      const keys = new Set();
      if (source[index] === "}") { index += 1; return object; }
      while (true) {
        skip();
        const key = string();
        if (keys.has(key)) fail(`duplicate key ${JSON.stringify(key)}`);
        keys.add(key);
        skip();
        if (source[index++] !== ":") fail("colon expected");
        const nested = value();
        object[key] = nested;
        skip();
        if (source[index] === "}") { index += 1; return object; }
        if (source[index++] !== ",") fail("comma expected");
      }
    }
    if (char === "[") {
      index += 1;
      skip();
      const array = [];
      if (source[index] === "]") { index += 1; return array; }
      while (true) {
        array.push(value());
        skip();
        if (source[index] === "]") { index += 1; return array; }
        if (source[index++] !== ",") fail("comma expected");
      }
    }
    if (char === '"') return string();
    for (const [token, result] of [["true", true], ["false", false], ["null", null]]) {
      if (source.startsWith(token, index)) { index += token.length; return result; }
    }
    const matched = source.slice(index).match(/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/);
    if (!matched) fail("value expected");
    index += matched[0].length;
    return Number(matched[0]);
  };
  const parsed = value();
  skip();
  if (index !== source.length) fail("trailing data");
  return parsed;
}

function comparePythonStrings(left, right) {
  const a = Array.from(left, item => item.codePointAt(0));
  const b = Array.from(right, item => item.codePointAt(0));
  for (let i = 0; i < Math.min(a.length, b.length); i += 1) {
    if (a[i] !== b[i]) return a[i] < b[i] ? -1 : 1;
  }
  return a.length - b.length;
}

function pythonString(value) {
  let output = '"';
  for (let index = 0; index < value.length; index += 1) {
    const code = value.codePointAt(index);
    if (code > 0xffff) index += 1;
    if (code === 0x22) output += '\\"';
    else if (code === 0x5c) output += "\\\\";
    else if (code === 0x08) output += "\\b";
    else if (code === 0x0c) output += "\\f";
    else if (code === 0x0a) output += "\\n";
    else if (code === 0x0d) output += "\\r";
    else if (code === 0x09) output += "\\t";
    else if (code < 0x20 || code > 0x7e) {
      if (code <= 0xffff) output += `\\u${code.toString(16).padStart(4, "0")}`;
      else {
        const pair = code - 0x10000;
        output += `\\u${(0xd800 + (pair >> 10)).toString(16)}\\u${(0xdc00 + (pair & 0x3ff)).toString(16)}`;
      }
    } else output += String.fromCodePoint(code);
  }
  return `${output}"`;
}

function pythonNumber(value) {
  if (Number.isNaN(value)) return "NaN";
  if (value === Infinity) return "Infinity";
  if (value === -Infinity) return "-Infinity";
  if (Object.is(value, -0)) return "-0.0";
  if (Number.isInteger(value)) return String(value);
  return String(value).replace(/e([+-]?)(\d)$/, "e$10$2");
}

function pythonCanonical(value) {
  if (value === null) return "null";
  if (typeof value === "string") return pythonString(value);
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return pythonNumber(value);
  if (Array.isArray(value)) return `[${value.map(pythonCanonical).join(",")}]`;
  if (typeof value === "object") {
    return `{${Object.keys(value).sort(comparePythonStrings).map(key => `${pythonString(key)}:${pythonCanonical(value[key])}`).join(",")}}`;
  }
  throw new Error("unsupported value in canonical JSON");
}

function sha256(value) {
  return `sha256:${createHash("sha256").update(pythonCanonical(value), "utf8").digest("hex")}`;
}

function envelopeSignatureInput(envelope) {
  return pythonCanonical({
    issuer_id: envelope.issuer_id,
    algorithm: envelope.algorithm,
    envelope_type: envelope.envelope_type,
    envelope_version: envelope.envelope_version,
    subject_id: envelope.subject_id,
    place: envelope.place,
    space: envelope.space,
    scope: envelope.scope,
    issued_at: envelope.issued_at,
    expires_at: envelope.expires_at,
    signed_payload_digest: envelope.signed_payload_digest,
  });
}

function spkiForEd25519(rawPublicKey) {
  return Buffer.concat([Buffer.from("302a300506032b6570032100", "hex"), rawPublicKey]);
}

function parseTimestamp(value) {
  if (typeof value !== "string" || !value) return null;
  const result = Date.parse(value);
  return Number.isNaN(result) ? null : result;
}

function verifyEnvelope(vector) {
  const envelope = vector.envelope;
  const issuer = vector.trusted_issuer;
  const expected = vector.verification;
  if (envelope.envelope_version !== "0.1-experimental") return "unsupported_envelope_version";
  if (envelope.envelope_type !== "spp:admission-envelope" || envelope.algorithm !== "Ed25519") return "unsupported_signature_algorithm";
  if (envelope.subject_id !== envelope.profile.actor_id || envelope.place !== envelope.profile.place || envelope.space !== envelope.profile.space || envelope.scope !== `${envelope.profile.place}::${envelope.profile.space}`) return "malformed_envelope";
  const issued = parseTimestamp(envelope.issued_at);
  const expires = parseTimestamp(envelope.expires_at);
  const now = parseTimestamp(expected.now);
  if (issued === null || expires === null || now === null) return "malformed_envelope_time";
  if (expires <= issued) return "invalid_envelope_time_range";
  if (issued > now) return "envelope_issued_in_future";
  if (expires <= now) return "envelope_expired";
  if (issuer.issuer_id !== envelope.issuer_id) return "unknown_issuer";
  if (!issuer.enabled) return "issuer_disabled";
  if (!issuer.allowed_envelope_types.includes(envelope.envelope_type)) return "issuer_unauthorized_envelope_type";
  if (!issuer.allowed_scopes.includes(envelope.scope)) return "issuer_unauthorized_scope";
  const profileCanonical = pythonCanonical(envelope.profile);
  if (profileCanonical !== vector.canonical_profile_json) throw new Error(`${vector.id}: canonical profile bytes diverged`);
  if (Buffer.from(profileCanonical, "utf8").toString("base64") !== vector.canonical_profile_utf8_base64) throw new Error(`${vector.id}: profile UTF-8 bytes diverged`);
  if (sha256(envelope.profile) !== envelope.signed_payload_digest) return "signed_payload_digest_mismatch";
  if (sha256(envelope.profile) !== vector.computed_profile_digest) throw new Error(`${vector.id}: fixture digest diverged`);
  const signed = Buffer.from(envelope.signature, "base64");
  const input = Buffer.from(envelopeSignatureInput(envelope), "utf8");
  if (input.toString("base64") !== vector.signature_input_utf8_base64) throw new Error(`${vector.id}: signature input bytes diverged`);
  const publicKey = createPublicKey({ key: spkiForEd25519(Buffer.from(issuer.public_key_base64, "base64")), format: "der", type: "spki" });
  if (!verifySignature(null, input, publicKey, signed)) return "invalid_envelope_signature";
  if (envelope.subject_id !== expected.expected_subject_id) return "envelope_subject_mismatch";
  if (envelope.place !== expected.expected_place || envelope.space !== expected.expected_space) return "envelope_place_mismatch";
  return null;
}

function restrictionDigest(restriction) { return sha256({ restriction }); }

function verifyAcknowledgement(vector) {
  const profile = vector.profile;
  const embedded = profile.operating_profile.restrictions;
  if (!Array.isArray(profile.restrictions) || !Array.isArray(embedded)) return { outcome: "BLOCKED", may_rely: false };
  const restrictions = [...new Set([...profile.restrictions, ...embedded])].sort(comparePythonStrings);
  if (pythonCanonical(restrictions) !== pythonCanonical(vector.effective_restrictions)) throw new Error("restriction order diverged");
  const operatingProfile = { ...profile.operating_profile };
  delete operatingProfile.restrictions;
  const bindingPayload = {
    status: profile.status, actor_id: profile.actor_id, place: profile.place, space: profile.space,
    policy_version: profile.policy_version, evidence_digest: profile.evidence_digest,
    binding: profile.binding, operating_profile: operatingProfile,
    effective_restrictions: restrictions, unresolved: profile.unresolved, reason_codes: profile.reason_codes,
  };
  const binding = `urn:spp:restriction-profile:${sha256(bindingPayload).slice("sha256:".length)}`;
  if (binding !== vector.profile_binding) throw new Error("profile binding diverged");
  for (const restriction of restrictions) {
    if (restrictionDigest(restriction) !== vector.restriction_digests[restriction]) throw new Error("restriction digest diverged");
    const acks = vector.acknowledgements.filter(item => item.restriction === restriction);
    const maps = vector.enforcement_mappings.filter(item => item.restriction === restriction);
    if (acks.length !== 1 || maps.length !== 1 || acks[0].profile_id !== binding || acks[0].restriction_digest !== restrictionDigest(restriction) || maps[0].restriction_digest !== restrictionDigest(restriction) || !acks[0].enforcement_handler || acks[0].enforcement_handler !== maps[0].enforcement_handler) return { outcome: "BLOCKED", may_rely: false };
  }
  return { outcome: "ACKNOWLEDGED", may_rely: true };
}

function main() {
  const filename = process.argv[2] ?? new URL("./vectors.json", import.meta.url);
  const vectors = strictJsonParse(readFileSync(filename, "utf8"));
  let checked = 0;
  for (const vector of vectors.vectors) {
    if (vector.kind === "admission_envelope") {
      const reason = verifyEnvelope(vector);
      const observed = { verified: reason === null, reason };
      if (observed.verified !== vector.expected.verified || observed.reason !== vector.expected.reason) throw new Error(`${vector.id}: expected ${JSON.stringify(vector.expected)}, observed ${JSON.stringify(observed)}`);
    } else if (vector.kind === "restriction_acknowledgement") {
      const observed = verifyAcknowledgement(vector);
      if (observed.outcome !== vector.expected.outcome || observed.may_rely !== vector.expected.may_rely) throw new Error(`${vector.id}: acknowledgement mismatch`);
    } else throw new Error(`unknown vector kind: ${vector.kind}`);
    checked += 1;
  }
  let duplicateRejected = false;
  try { strictJsonParse('{"restriction":1,"\\u0072estriction":2}'); } catch { duplicateRejected = true; }
  if (!duplicateRejected) throw new Error("duplicate JSON keys were accepted");
  console.log(`JavaScript verifier: ${checked} vectors verified; duplicate JSON keys rejected`);
}

main();
