# Search Fix Report: Tokenized Query Matching

## Status

COMPLETE — all tests green.

## Problem

`KnowledgeGraph.search` matched the entire query string as a substring against
each field.  A natural-language question like
`"What authentication method is used for stateless tokens?"` scored 0 on every
note and returned `[]`, even when notes contained the individual keywords
"authentication" and "tokens".  Single keywords worked; multi-word questions did not.

## Fix

**File:** `src/linked_notes_mcp/graph.py`

Changes:
1. Added `import re` at the top of the file.
2. Added module-level constant `_STOPWORDS` (set of common English stop-words
   and question words to exclude from tokenization).
3. Extracted per-field scoring into a new private method `_match_score(self, note, needle)`.
   Contains the original scoring logic verbatim for a single lowercased `needle`:
   title +10, alias exact +9 / in +6, tag +5, summary +6, project +5,
   entity_type +4, status +3, relation_type +4, content +1.
   `_note_priority` is NOT called in this helper.
4. Rewrote `search(self, query, limit=20)` to:
   - Tokenise `query` with `re.split(r"[^a-z0-9]+", ql)`, keeping tokens
     of length >= 3 that are not in `_STOPWORDS`.
   - Fall back to the full stripped query if no tokens survive.
   - Score each note as `_note_priority(note)` + sum of `_match_score` for
     every term + (if multi-term) a whole-phrase bonus via `_match_score(note, ql)`.
   - Keep `if score > 0` guard and `limit` slice unchanged.

Single-keyword queries produce a `terms` list of length 1 equal to the keyword,
so behavior is identical to before.

## Test Written

**File:** `tests/test_graph.py` — added
`TestKnowledgeGraph::test_search_natural_language_question`

Creates a one-note vault whose title, summary, tags, and content all contain
"authentication" and/or "tokens", then asserts that
`graph.search("What authentication method is used for stateless tokens?")`
returns that note as the top result.  The test **failed** before the fix and
**passes** after.

## Test Command and Result

```
uv run pytest -q
```

**Result:** 158 passed in 0.56s  (was 157 before adding the new test)

## Tests Changed

None of the pre-existing 157 tests were modified.  The salience tests in
`tests/test_get_context_salience.py` use a single-word query (`"foobar"`) whose
tokenization is identical to the old substring path, so all four salience tests
pass unchanged.

## Concerns

- The `_STOPWORDS` set is deliberately conservative.  Words shorter than 3
  characters are already filtered by the `len(t) >= 3` guard, so short
  conjunctions like "or", "of" etc. need to be in the set explicitly.
- The whole-phrase bonus (`score += self._match_score(note, ql)`) fires only
  when `len(terms) > 1`, preserving exact-phrase ranking for multi-word queries.
- Stemming / fuzzy matching are out of scope; this fix addresses the most
  common failure mode (question phrasing) without introducing new dependencies.
