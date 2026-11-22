# Search Arena — Documentation

This folder documents the design and implementation of Search Arena. For setup and the demo
walkthrough, see the top-level [README](../README.md).

| Document | Contents |
|---|---|
| [architecture.md](architecture.md) | Module layout, dependency direction, data flow from UI to search |
| [state-and-actions.md](state-and-actions.md) | `Grid`, `State`, `Action`, `Problem`, terrain costs, goal test |
| [rules.md](rules.md) | The five constraint rules, evaluation order, `RuleLog` |
| [heuristics.md](heuristics.md) | The three heuristics with admissibility proofs |
| [search.md](search.md) | Successor model, the five strategies, safety caps, determinism, `SearchTrace` |
| [scenarios.md](scenarios.md) | The four maps, what each one demonstrates, measured results |
| [ui.md](ui.md) | Streamlit app: sidebar, tabs, animation, caching, rendering |
| [testing.md](testing.md) | Test suite layout and what each test proves |
| [development.md](development.md) | Tooling, Makefile, code style, git workflow |
| [design-decisions.md](design-decisions.md) | Where and why the implementation deviates from the original brief |
