# Stimulus and evaluation rules

Required reading before interpreting, coding or judging these experiments.
See [frames.csv](../data/design/frames.csv) for the exact frames and the manuscript
(maintained outside this repository) for the stimulus rationale. The rules here
govern evaluation and reporting.

Interpret each response against the entire prompt: the task instruction, exact
lexicon entry, frame-specific instruction about that entry, and source sentence.
The source alone does not define the requested translation. This applies equally
when the supplied meaning agrees with the conventional meaning: the lexicon can
specify an intended sense or rendering that the no-rule prompt leaves implicit.
Examples and judge inputs must retain that information. An agreeing-rule versus
no-rule comparison changes the available guidance; assess each response against
its own prompt as well as comparing the outputs.

Experiment 1 pairs words from different semantic categories and places each
mapping in two sentence contexts: one compatible with the conventional meaning,
the other with the lexicon meaning. Experiment 2 pairs words within a category
and uses one context compatible with both meanings. Implausibility is intentional;
making a sentence more plausible is not permission to change its meaning.

Use these display labels for the two comparison translations:

| Label | Example |
|---|---|
| Source | 这些码农已经熟到可以吃了。 |
| Familiar | These programmer are ripe enough to eat. |
| Supplied | These peach are ripe enough to eat. |

**Familiar** translates the word actually in the source using its familiar
meaning (`literal_pk_en`, or baseline `literal_expected_en`). **Supplied**
applies the prompt's definition to that word (`literal_ck_en`). Both preserve the
remaining sentence meaning, including intentional nonsense. They are defined
translations under two lexical rules, not predictions of a model's response or
evidence about its internal knowledge. The saved template grammar stays verbatim;
acceptable output grammar and paraphrases are assessed separately. Mandarin-target
score fields use the corresponding `_zh` suffixes. Earlier HTML reports use the
old labels: Conventional = Familiar, Use Lexicon = Supplied, and Conventional-Meaning
Control or conventional meaning baseline = agreeing-definition control. Code
identifiers (`conventional_meaning`, `literal_ck_en`, `may_mean`) are unchanged.

| Condition | Task-correct lexical reading |
|---|---|
| No-rule baseline; F1, ignore the rule | Familiar |
| F2, bare lexicon; F3, newly documented variety; F4, language game; F5, explicit override | Supplied |
| Agreeing-definition control | The two readings agree |

This mapping applies to asserted definitions. The `may_mean` manipulation makes
the definition tentative: retain both readings and the exact frame wording rather
than silently applying an unconditional correctness label. PK/CK context names
describe sentence compatibility, not which reading is task-correct. Changing the
required lexical reading between F1 and F5 is the experimental manipulation.

Evaluate three things separately:

- **Lexical choice:** use the accepted-form inventory, including variants such
  as `apricot` and `apricots`. `Peaches` is a different meaning. Distinguish use
  in the translation from a mention in an explanation; existing automatic labels
  measure presence anywhere in the response.
- **Remaining sentence meaning:** preserve actions, participants and relations
  outside the redefined word. With apple → sedan under F5, using `sedan` is
  correct; changing `eat` to `drive` is an additional semantic alteration.
- **Output format:** assess untranslated source-language material, repeated task
  details, explanations and run-on generation separately from lexical choice and
  sentence meaning. An accepted word inside a malformed response does not make
  the whole response a successful translation.

## Scores and comparisons

Show Familiar and Supplied scores separately under every frame where
both have been computed, and identify the task-correct reading using the rules
above. A high score against the other reading does not establish task success.
Keep a paired score difference on the same reference; do not subtract a
Familiar score from a Supplied score. Baselines without Supplied scores
have that comparison unavailable, not zero. COMET sees the source, response and
reference, not the prompt's lexical instruction. No metric alone establishes
lexical correctness, sentence fidelity or instruction adherence.

Every nonempty response is scored verbatim, including explanations. Empty
responses remain with null scores. BLEU and chrF++ are divided by 100; COMET
keeps its native scale. Scores are rounded to four decimals, matching the copied
scorer. chrF++ uses word order 2; these are sentence scores, and their means
are not corpus BLEU/chrF. COMET uses `Unbabel/wmt22-comet-da`; an exact zero
is null under the copied scorer's failure convention.

Reports include all ten frame pairs within each experiment and each follow-up
(may_mean, reiteration, thinking_on) versus main. Matching requires the same
model, mapping, source, reference and context; follow-ups also hold frame fixed.
Differences are right minus left, using only jointly scored pairs. Sources,
references and item identities must agree. Exp1 and Exp2 are not paired.
Baseline EXPECTED/OTHER labels supply separate strata; they describe lexical
matches, not human judgments. No significance tests are implemented yet.
