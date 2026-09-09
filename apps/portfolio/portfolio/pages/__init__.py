# Page registry: (module name, fallback title). Pages are imported lazily,
# one at a time, and evicted from sys.modules when the user navigates away
# so a no-PSRAM board only ever holds one page's bytecode and widgets.

PAGES = (
    ("p01_home", "Home"),
    ("p02_about", "About"),
    ("p03_skills", "Skills"),
    ("p04_stack", "Stack"),
    ("p05_projects", "Projects"),
    ("p06_experience", "Experience"),
    ("p07_opensource", "Open Source"),
    ("p08_media", "Talks & Media"),
    ("p09_interests", "Interests"),
    ("p10_contact", "Contact"),
)
