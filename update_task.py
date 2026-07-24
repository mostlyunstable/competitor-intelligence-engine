
with open(".gemini/antigravity/brain/ea14955e-78eb-41cc-b3f3-c927b767700e/task.md") as f:
    content = f.read()

content = content.replace("- `[/]` 1. Resolve all compilation errors", "- `[x]` 1. Resolve all compilation errors")
content = content.replace("- `[ ]` 2. Resolve import errors", "- `[x]` 2. Resolve import errors")
content = content.replace("- `[ ]` 3. Resolve linting issues (Ruff)", "- `[x]` 3. Resolve linting issues (Ruff)")
content = content.replace("- `[ ]` 4. Resolve formatting issues", "- `[x]` 4. Resolve formatting issues")
content = content.replace("- `[ ]` 5. Resolve type-checking issues (MyPy)", "- `[x]` 5. Resolve type-checking issues (MyPy)")
content = content.replace("- `[ ]` 6. Verify database migrations", "- `[/]` 6. Verify database migrations")

with open(".gemini/antigravity/brain/ea14955e-78eb-41cc-b3f3-c927b767700e/task.md", "w") as f:
    f.write(content)
