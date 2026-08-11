# VastuAI Platform v5.0.0 — Portfolio Consultant

Built from the tested v4.9.0 Buyer Workspace / Shortlist baseline.

## Added

- New **Portfolio Consultant** Professional workspace page.
- New `professional_app/services/portfolio_consultant_service.py` deterministic portfolio analysis service.
- Cross-project comparison of shortlisted immutable PDPs.
- Best Overall, Best Vastu Fit and Best Numerology Fit callouts.
- Ranked shortlist comparison table.
- Property-level strengths, concerns and trade-off explanations.
- Deterministic consultant recommendation.
- New v5.0.0 regression tests.

## Ranking policy

Portfolio Consultant does not create a new score and does not recalculate saved assessments.

1. Saved PDP **Overall Professional Score** is the primary ranking basis.
2. If Overall scores are equal, fewer **Critical / High** findings wins.
3. If still tied, higher **Vastu score** wins.
4. If still tied, higher **Numerology score** wins.
5. Original shortlist order is the final stable tie-breaker.

This avoids double-counting because the existing Overall Professional Score already combines Vastu and Numerology according to the platform's scoring rules.

## Validation

Clean regression run: **119 passed**.

## Next version

v5.1.x can add a conversational portfolio consultant for questions such as:
- Which shortlisted property should I investigate first?
- Compare property A with property B.
- Why is property #1 ranked above #2?
- Which option has the lowest Vastu risk?
- What am I compromising if I select property #2?
