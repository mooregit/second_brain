The previous model output failed JSON validation.

Validation error:
{{validation_error}}

Invalid output:
{{invalid_output}}

Return corrected JSON only. Do not use markdown. Do not add commentary. Preserve the original extracted meaning unless correction is required for valid schema compliance.

Required schema:
{
  "summary": "string",
  "memory_type": "note | task | idea | decision | question | resource | email | file",
  "projects": ["string"],
  "people": ["string"],
  "tasks": [
    {
      "title": "string",
      "description": "string|null",
      "priority": "low|medium|high|null",
      "due_date": "string|null",
      "status": "open"
    }
  ],
  "ideas": ["string"],
  "decisions": [
    {
      "title": "string",
      "rationale": "string|null",
      "confidence": 0.0
    }
  ],
  "open_questions": ["string"],
  "tags": ["string"],
  "entities": ["string"],
  "relationships": [
    {
      "source": "string",
      "target": "string",
      "relationship": "string"
    }
  ],
  "suggested_actions": ["string"],
  "confidence": 0.0
}

If the invalid output has task strings, convert each string into a task object with that string as `title`.
If the invalid output has a `title` but no `summary`, use the title as the summary.
If confidence is missing, choose a reasonable value between 0 and 1.
If the invalid output is a glossary, study guide, course note, or reference summary with headings and defined terms, preserve the summary but also extract broad headings as `tags`, important defined terms as `entities`, and category-to-term `relationships` using relationship "includes".
