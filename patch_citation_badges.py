from pathlib import Path


path = Path("ui/components.py")

text = path.read_text(
    encoding="utf-8"
)


old = """
                    if url:
                        return (
                            f"[{title}]({url})"
                        )
"""


new = """
                    if url:
                        return (
                            f'<a class="tc-citation-badge" '
                            f'href="{escape(url)}" '
                            'target="_blank">'
                            f'🔗 Web {index + 1}'
                            '</a>'
                        )
"""


assert old in text, (
    "citation link block not found"
)


text = text.replace(
    old,
    new,
    1,
)


path.write_text(
    text,
    encoding="utf-8",
)


print(
    "citation badges added"
)