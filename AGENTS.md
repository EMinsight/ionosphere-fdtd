# Repository contribution rules

## Commit messages

- Use Conventional Commits: `<type>(optional-scope): <imperative summary>`.
- Use one of these prefixes unless another established type is more precise:
  `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`,
  or `revert`.
- Keep the title concise (preferably 72 characters or fewer), imperative, and
  without a trailing period.
- Always add a commit body after a blank line. Explain what changed and why;
  include important design choices, compatibility notes, or test evidence when
  useful.
- Mark breaking changes with `!` in the prefix and add a `BREAKING CHANGE:`
  footer describing the migration impact.
- Keep each commit focused on one coherent change and do not mix unrelated
  formatting or cleanup.

Example:

```text
feat(mesh): add geodesic grid generation

Generate an icosphere and its pentagon-hexagon dual topology with NumPy.
Document the supported subdivision levels and verify spherical area closure.
```
