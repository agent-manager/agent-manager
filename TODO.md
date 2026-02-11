# Initial release:
Test the code output (ensure it works with AI agent)
Create LICENSE.md file
Push the code somewhere?

# Feature ideas

## Provenance tracking (`whatprovides` command)
Add a command like `agent-manager whatprovides ~/.claude/some_file` that reports:
- "Local only (not managed by agent-manager)"
- "Merged from: Platform Services → Red Hat" (with hierarchy order)
- "Single source: Personal"

Implementation options:
1. **Manifest file**: Store a `.agent-manager/manifest.json` tracking which files were written and their sources
2. **Scan repos**: On-demand scan all configured repos to find which ones have that file
3. **Metadata in files**: Already adding headers to merged files - could parse those

Related features:
- `agent-manager diff <file>` - show what each hierarchy level contributes
- `agent-manager status` - show which files would be overwritten on next run
- `--dry-run` flag for `agent-manager run`

## Cache md5 sums
Cache md5 sums of the files in the different repos so we can quickly know if we need to merge on a subsequent run.

## Support local git checkouts as repo sources
Currently we have:
- **Git repos**: Cloned from remote URLs, managed in `~/.agent-manager/repos/`
- **File repos**: Local directories (read-only, no git operations)

Add support for using an existing local git checkout as a repo source.

Options:
1. **New repo type**: `local_git` - points to an existing checkout, can optionally pull updates
2. **Extend git repo type**: Accept a file path instead of URL, validate `.git` folder exists
3. **Extend file repo type**: Auto-detect if directory has `.git` and offer to pull updates

Benefits:
- No duplication of repos already checked out locally
- User maintains control of the checkout (branch, uncommitted changes, etc.)
- Useful for repos you're actively developing (like personal_ai)

Considerations:
- Should we auto-pull on `agent-manager run`? Or require explicit `--pull` flag?
- How to handle dirty working directories?
- Should we warn if local checkout is behind remote?

## Git repo branch configuration
Allow specifying which branch a git repo should sync from.

Currently git repos clone and pull from the default branch. Add support for:
- Config option to specify branch per hierarchy level: `branch: develop`
- CLI flag to override: `agent-manager run --branch personal=feature-x`
- Validation that the branch exists before syncing

Example config:
```yaml
hierarchy:
  - name: organization
    url: https://github.com/org/config.git
    repo_type: git
    branch: main  # explicit branch
  - name: personal
    url: https://github.com/user/config.git
    repo_type: git
    branch: develop  # different branch
```

## Handle Claude-generated files (skills, etc.)
The `claude /init` command (via npx) creates default files like `skills/skills-creator.md`.
How should agent-manager handle these?

Options:
1. **Ignore them**: Don't manage files created by Claude's init - they're "local only"
2. **Preserve them**: Before writing, check if file exists and wasn't sourced from a repo - skip overwriting
3. **Merge them**: Treat Claude-generated files as a "system" layer below all user-defined layers
4. **Backup them**: Before sync, backup existing files to `.agent-manager/backup/` for recovery
5. **Explicit exclude list**: Config option to list files/patterns that should never be overwritten
6. **Make agent-manager aware of other managers**

Related questions:
- Should `agent-manager run` have a `--preserve-local` flag?
- Should the manifest track "local-only" files separately?
- Should there be a way to "adopt" a local file into a repo layer?

# Create process
Create a background process that would somehow detect changes and auto-update repos for users.

## Agent Plugin API Versioning

Add version compatibility checking for agent plugins.

Problem:
- As AbstractAgent evolves (new methods, changed signatures, refactored helpers), third-party agent plugins may become incompatible
- Users might have outdated agents that still "work" but miss new features or use deprecated patterns
- Breaking changes could cause silent failures or unexpected behavior

Proposed solution:
1. **API version in AbstractAgent**: Define `AGENT_API_VERSION = "1.0"` in AbstractAgent
2. **Declared compatibility in plugins**: Agents declare `supported_api_versions = ["1.0", "1.1"]`
3. **Runtime warning**: On load, warn if agent's supported versions don't include current API version
4. **Deprecation notices**: Mark deprecated methods/patterns and warn when agents use them

Example warning:
```
Warning: Plugin 'cursor' (am_agent_cursor 0.0.1) was built for API v1.0 but current API is v2.0.
Some features may not work correctly. Consider updating the plugin.
```

Related considerations:
- Semantic versioning for API (major = breaking, minor = additive, patch = fixes)
- Grace period for deprecated features before removal
- Documentation of API changes in CHANGELOG
- Test suite that plugins can run to verify compatibility

# Alternative Markdown Merge Strategy
Instead of just appending one after another can we merge sections based on heading in the markdown?
i.e. if one file had the section: # Top Level > ## Indented One
     and a subsequent file had: # Top Level > ## Indent One

    We currently output:
    # Top Level
    ## Indent One
    Content A
    <!-- Notification that the following has higher priority -->
    # Top Level
    ## Indent One
    Content B
    
    Instead could we do:
    # Top Level
    ## Indent One
    Content A
    <!-- notification -->
    Content B

