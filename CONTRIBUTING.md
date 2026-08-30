# Contributing

This project welcomes contributions and suggestions. Most contributions require you to
agree to a Contributor License Agreement (CLA) declaring that you have the right to,
and actually do, grant us the rights to use your contribution. For details, visit
https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need
to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the
instructions provided by the bot. You will only need to do this once across all repositories using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/)
or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Ways to Contribute

We welcome several types of contributions:

- 🐛 **Bug fixes** - Fix issues and improve reliability
- ✨ **New features** - Add new commands or functionality  
- 📖 **Documentation** - Improve guides, examples, and API docs
- 🧪 **Tests** - Add or improve test coverage
- 💬 **Help others** - Answer questions and provide support
- 💡 **Feature suggestions** - Propose new capabilities

## Contribution process
To avoid cases where submitted PRs are rejected, please follow the following steps:
- To report a new issue, follow [Create an issue](#creating-an-issue)
- To work on existing issue, follow [Find an issue to work on](#finding-an-issue-to-work-on)
- To contribute code, follow [Pull request process](#pull-request-process)

### Creating an issue

Before reporting a new bug or suggesting a feature, please search the [GitHub Issues page](https://github.com/microsoft/fabric-cli/issues) to check if one already exists.

All reported bugs or feature suggestions must start with creating an issue in the GitHub Issues pane. Please add as much information as possible to help us with triage and understanding. Once the issue is triaged, labels will be added to indicate its status (e.g., "need more info", "help wanted").

When creating an issue please select the relevant topic - bug, new feature or general question - and provide all required input.

We aim to respond to new issues promptly, but response times may vary depending on workload and priority.

### Finding an issue to work on

#### For Beginners
If you're new to contributing, look for issues with these labels:
- **`good-first-issue`** - Beginner-friendly tasks that are well-scoped and documented
- **`help wanted`** - Issues where community contributions are especially welcome
- **`documentation`** - Improve docs, examples, or help text (great for first contributions)

#### Getting Started Tips
1. **Start small** - Look for typo fixes, documentation improvements, or simple bug fixes
2. **Read existing code** - Familiarize yourself with the codebase by exploring similar commands
3. **Ask questions** - Comment on issues to clarify requirements or get guidance
4. **Test locally** - Always test your changes thoroughly before submitting

#### Before You Code
All PRs must be linked with a "help wanted" issue. To avoid rework after investing effort:
1. **Comment on the issue** - Express interest and describe your planned approach
2. **Wait for acknowledgment** - Get team confirmation before starting significant work
3. **Ask for clarification** - Don't hesitate to ask questions about requirements

Please review [engineering guidelines](https://github.com/microsoft/fabric-cli/wiki) for coding guidelines and common flows to help you with your task. 

### Pull request process

Please use a descriptive title and provide a clear summary of your changes.

All pull requests (PRs) should be linked to an approved issue, please start the PR description with `- Resolves #issue-number`

Before submitting the pull request please verify that:
- The PR is focused on the related task
- Tests coverage is kept and all tests pass
- Your code is aligned with the code conventions of this project
- Your code is formatted (see [Code formatting](#code-formatting) below)

Before your PR can be merged, make sure to address and resolve all review comments. PR will be labeled as "need author feedback" when there are comments to resolve. Approved PRs will be merged by the Fabric CLI team.

### Code formatting

This project uses [Black](https://black.readthedocs.io/) for code formatting and
[isort](https://pycqa.github.io/isort/) for import ordering. Both are configured in
`pyproject.toml`, which is the single source of truth — your editor, `tox` and CI
all read that same configuration.

Format your changes before pushing:

```bash
tox -e format
```

Check without modifying anything (this is what CI runs):

```bash
tox -e lint
```

CI runs `tox -e lint`, which **fails** if any file is unformatted, so running
`tox -e format` before you commit will save you a round-trip.

#### Automating it (recommended)

If you use VS Code, this is already set up: `.vscode/settings.json` enables
format-on-save and import sorting, and points both extensions at the versions
installed in your environment, so saving a file formats it the same way CI will.

There is no committed git hook. If you want one, the repository does not manage it
for you — the CI check is the enforcement point.

#### Version pinning

Black's output changes between releases, so the versions are pinned exactly. If you
upgrade one, you must upgrade **both** together or the tools will disagree about
what "formatted" means:

- `tox.toml` — `[env.lint]` and `[env.format]`
- `requirements-dev.txt`

CI enforces this with `python scripts/check_formatter_pins.py`, which reads the
declared version out of both files and fails if they disagree. Run it locally after
bumping a pin (on Python 3.10 it needs `tomli` from the dev requirements, since it
parses `tox.toml` with a real TOML parser rather than guessing with regular
expressions). It also rejects a pin that is declared more than once in a file, that
is not an exact `==`, or that is missing from either tox environment — the mutating
`format` environment drifting away from the checking `lint` one would mean
`tox -e format` produced output that `tox -e lint` rejects.

#### `git blame` and the formatting commit

This repository was reformatted wholesale in a single commit. `.git-blame-ignore-revs`
exists so such commits do not obscure real authorship. Configure git to use it:

```bash
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

GitHub's blame view applies this file automatically.

> **Maintainers:** pull requests here are squash-merged, so the SHA of a formatting
> commit inside a PR never reaches `main`, and a squash collapses every commit in a
> PR into one. That means the reformat must land as a PR containing **nothing but**
> the reformat — otherwise the squash commit also carries real changes, and listing
> it would hide their authorship. After merging such a PR, take the squashed SHA
> from `main` and append it to `.git-blame-ignore-revs`. Git silently ignores
> entries that do not resolve to a real commit, so a wrong or placeholder SHA fails
> **open** — blame keeps pointing at the formatting commit with no warning that the
> entry is dead.

### Documenting Changes with Changie

All pull requests must include proper change documentation using [changie](https://changie.dev), which is pre-installed in the development container. This ensures that release notes are automatically generated and changes are properly tracked.

#### Requirements

**Every PR must include at least one change entry** created using `changie new`. You may add multiple entries if your PR introduces multiple distinct changes.

#### How to Add Change Entries

1. **From the Terminal, run `changie new` command**:
   ```bash
   changie new
   ```

2. **Select the appropriate change type** from the available options:
   - **⚠️ Breaking Change** - For changes that break backward compatibility
   - **🆕 New Items Support** - For adding support for new Fabric item types
   - **✨ New Functionality** - For new features, commands, or capabilities
   - **🔧 Bug Fix** - For fixing existing issues or incorrect behavior
   - **⚡ Additional Optimizations** - For performance improvements or optimizations
   - **📝 Documentation Update** - For documentation improvements or updates

3. **Provide a clear description** of your change:
   - Write in present tense (e.g., "Add support for..." not "Added support for...")
   - Be specific and user-focused
   - Include the affected command or feature if applicable
   - Keep it concise but informative

#### Examples of Good Change Descriptions

- `Add new 'fab describe capacity' command for viewing capacity details`
- `Fix authentication timeout issue in interactive mode`
- `Update workspace examples with new folder hierarchy patterns`
- `Optimize API response caching to reduce network calls`

#### Guidelines

- **One logical change per entry**: If your PR fixes a bug and adds a feature, create two separate entries
- **User-facing perspective**: Describe what users will experience, not internal implementation details
- **Clear and actionable**: Users should understand what changed and how it affects them
- **Consistent formatting**: Follow the examples and existing patterns in the changelog

The change entries will be automatically included in the release notes when a new version is published. This process ensures that all improvements, fixes, and new features are properly communicated to users.

## Resources to help you get started
Here are some resources to help you get started:
- A good place to start learning about Fabric CLI is the [Fabric CLI documentation](https://microsoft.github.io/fabric-cli/)
- If you want to contribute code, please check more details about coding guidelines, major code flows and code building block in [Engineering guidelines](https://github.com/microsoft/fabric-cli/wiki)
- Browse [existing commands](https://microsoft.github.io/fabric-cli/commands/) to understand patterns and conventions
- Check out [usage examples](https://microsoft.github.io/fabric-cli/examples/) to see the CLI in action

## Engineering guidelines
For detailed engineering guidelines please refer to our [Wiki pages](https://github.com/microsoft/fabric-cli/wiki).

The Wiki contains essential information and requirements for contributors, including: Code Style and Standards, Architecture Overview, Testing and more.

Before contributing code, please review these guidelines to ensure your contributions align with the project's standards and practices.

## Areas with Restricted Contributions

Some areas require special consideration:
- **Authentication module** - Changes preferred to be made by Fabric CLI team due to security implications
- **Core infrastructure** - Major architectural changes require team discussion

## Need Help?

### Getting Support
- **[GitHub Discussions](https://github.com/microsoft/fabric-cli/discussions)** - Ask questions and discuss ideas
- **[GitHub Issues](https://github.com/microsoft/fabric-cli/issues)** - Report specific problems
- **[Documentation](https://microsoft.github.io/fabric-cli/)** - Check comprehensive guides

### Communication Guidelines
- **Be patient** - Maintainers balance multiple responsibilities
- **Be respectful** - Follow the code of conduct
- **Be specific** - Provide clear, detailed information
- **Be collaborative** - Work together to improve the project

Thank you for contributing to Microsoft Fabric CLI! Your contributions help make this tool better for the entire Fabric community.
