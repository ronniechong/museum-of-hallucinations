# museum-of-hallucinations

A public gallery website that exhibits confidently wrong LLM answers as works of art. An LLM is deliberately
asked unanswerable or trick questions; its confidently wrong answer becomes a museum exhibit, complete with a
formal plaque — title, medium, year, curatorial description — written by a second "curator" model.

Status: early scaffold, not yet implemented.

## Setup
After cloning, enable the gitleaks pre-commit hook (requires `brew install gitleaks`):

```
git config core.hooksPath .githooks
```
