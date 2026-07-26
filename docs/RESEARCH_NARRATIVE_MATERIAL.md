# Research narrative — raw material, not a draft

**What this file is:** a factual timeline of decisions, dead ends, and reversals from this
project, for you to draw on when you write your own essay, personal statement, or interview
answers, in your own voice. **What this file is not:** a personal statement, an essay draft, or
anything meant to be copied in. The reflection — what a moment meant to you, why you made a call
the way you did, what you'd do differently — has to be yours; that's the part a reader is
actually evaluating, and it's also the part that would read as false coming from anyone else.
This mirrors the same boundary used on the earlier incentive-allocation project: AI can produce
code, analysis, and a factual scaffold; it should not produce your reflection on your own
research experience.

Every beat below is something that is actually in the repository — the commit history, the
pre-registration amendments, the results JSON files — not a dramatized version of events.

## The beats

**1. The pivot that started this project.** An earlier research direction (a reinforcement
learning simulation of incentive allocation) was carried through a full empirical pipeline —
200-seed runs, calibration against real HR data, a 19-agent adversarial review — before an
honest audit concluded its core mechanism was a numerical instantiation of a 1991 economics
theorem (Holmström–Milgrom), not new. That project was not deleted; it was kept as a validated
negative-result note, and its incumbent status was weighed against candidates before choosing
this one. *Possible essay material: what it takes to recognize your own project's real weakness,
and choose to demote a working result rather than oversell it.*

**2. Why this direction, specifically.** The winning direction was chosen by an explicit
elimination process across multiple candidates, scored against a rubric before any candidate was
built out — not chosen because it was the most interesting one to work on. The decisive factor
was that its identification strategy needed no fitted model and no gold label, avoiding a
circularity that had already sunk two other candidates. *Possible essay material: choosing a
research question for a structural reason rather than a topical one.*

**3. The theorem that undercut the headline before it existed.** Partway through implementing
the null model, a derivation showed the paper's central planned claim (mean co-failure
"exceeds" a random baseline) was mathematically impossible to observe — the quantity is
literally fixed by the item difficulty and cannot vary. This was discovered *before* running the
confirmatory analysis, and amended into the pre-registration with a dated entry, rather than
quietly rewriting the hypothesis after the fact. See `PREREGISTRATION.md`, "AMENDMENT 1."
*Possible essay material: the moment a clean plan turns out to be mathematically empty, and what
you do in the hour after that.*

**4. Finding out your own idea already existed.** An adversarial review — deliberately run to
attack the project's own conclusions, not requested by anyone else — found that the "new"
identity from beat 3 is Schluter's V-ratio (ecology, 1984) and Cronbach's alpha (psychometrics,
1937), independently rediscovered without knowing either literature existed. Rather than
claiming novelty, the paper now cites both and states plainly what is not new. See
`docs/PRIOR_ART_LEDGER.md`. *Possible essay material: the specific discomfort of learning your
result is 40-90 years old, and the difference between hiding that and building the paper's
credibility on being the one who found it and said so.*

**5. Withdrawing your own headline number.** A follow-up statistic ("~1,362 models behave like
~24 independent ones") was computed, looked clean, and was written into a first draft. A second
adversarial pass proved — algebraically, checkable by hand — that the statistic cannot
distinguish "one weak shared trend" from "24 genuine clusters." The number was pulled from the
paper's headline and replaced with the diagnostics that can actually tell those two apart. This
happened after the number was already in a compiled draft. See `results/RESULTS_DIGEST.md`,
section "C2." *Possible essay material: deleting your best sentence.*

**6. A test you ran against yourself, and lost.** Part of the project was a critique of a
published claim in prior work (that more accurate AI models make more similar mistakes) —
arguing it might be a measurement artifact. A test of that critique was written into the
pre-registration *before* running it, with an explicit condition for what would count as the
critique failing. It failed: the original claim survives almost fully. That outcome is reported
in the paper as prominently as it would have been if the critique had succeeded. See
`PREREGISTRATION.md`, "AMENDMENT 2," and paper Section 6.8. *Possible essay material: designing
a test that could prove you wrong, and reporting it when it did.*

**7. A scooping risk, handled by looking rather than hoping.** A closely related paper (on the
same public archive) was found through a deliberate search for prior art, not stumbled into. The
project's response was not to abandon the direction but to identify the specific open question
that paper leaves unresolved, and answer that one. *Possible essay material: what changes when
you go looking for reasons your work might not be original, instead of avoiding that search.*

**8. Turning the project into something that outlives the paper.** The repository includes a
scheduled process, running independently on GitHub's infrastructure, that re-checks the public
archive every month and appends new evidence to a public record — designed specifically not to
end when the paper is submitted. *Possible essay material: what "finished" means for a project
you actually care about.*

## Facts for context, not for dramatizing

- Substrate: 1,228–1,373 open language models per benchmark, harvested from public evaluation
  logs at $0 compute cost (no GPU, no API budget) by reading only the accuracy column of each
  file.
- Two real data-engineering bugs were found and fixed during harvesting: item identifiers
  silently changed format mid-archive (a naive join returns zero matches), and the evaluation
  harness restructured its schema partway through. Both are documented, not silently patched.
- AI assistance (Claude, Anthropic) wrote the code, ran the analyses, and assisted in drafting,
  under direction. This is disclosed identically in the paper, the repository README, and the
  project page — nowhere is it minimized or omitted.

## A note on honesty in how you write about this

Every beat above is a real reversal, not a manufactured one — real reversals are more convincing
than invented ones, and an admissions reader who has seen a hundred "I overcame a challenge"
essays can generally tell the difference. Write about what you actually decided and why, in
plain language. Resist the pull to sand the story down into something that sounds more like a
TED talk than a lab notebook.
