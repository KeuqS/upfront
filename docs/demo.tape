# Regenerate docs/demo.gif: vhs docs/demo.tape   (run from the repository root)
Output docs/demo.gif
Set Shell bash
Set FontSize 14
Set Width 1380
Set Height 820
Set Padding 18
Set Theme "Builtin Dark"
Set TypingSpeed 45ms

Hide
Type "export HOME=$(mktemp -d) PS1='$ ' && uv run upfront --version >/dev/null && clear"
Enter
Sleep 2s
Show

Type "uv run upfront examples/demo --yes --top 2"
Sleep 400ms
Enter
Sleep 9s
Hide
Type "clear"
Enter
Show
Type "uv run upfront --tools-file examples/servers/issue-scenarios.tools.json | sed -n '/compatibility/,$p'"
Sleep 400ms
Enter
Sleep 7s
