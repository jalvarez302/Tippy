"""The vocabulary the thinking screen chews through.

These are the present-participle status words Claude Code shows while it works.
Short ones make quick rounds, long ones make a real chase, so the list is kept
deliberately mixed.
"""

THINKING_WORDS = [
    "Ruminating",
    "Contemplating",
    "Pondering",
    "Deliberating",
    "Percolating",
    "Noodling",
    "Marinating",
    "Synthesizing",
    "Cogitating",
    "Puzzling",
    "Mulling",
    "Distilling",
    "Untangling",
    "Considering",
    "Brewing",
    "Musing",
    "Simmering",
    "Incubating",
    "Finagling",
    "Wrangling",
    "Schlepping",
    "Conjuring",
    "Divining",
    "Reticulating",
    "Vibing",
    "Spelunking",
    "Tinkering",
    "Whirring",
    "Contriving",
    "Perusing",
]


def shortest(words=None):
    """Shortest word in the list, used to size the board."""
    return min(len(w) for w in (words or THINKING_WORDS))


def longest(words=None):
    """Longest word in the list, used to size the board."""
    return max(len(w) for w in (words or THINKING_WORDS))
