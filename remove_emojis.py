import re

# Read the file
with open(r'c:\Users\gustu\OneDrive\Desktop\project web\sub project\emitscanindonesia-main\emitscanindonesia-main\app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove all emojis
emojis_to_remove = ['📊', '💰', '📈', '📝', '🎯', '🛡️', '↗️', '↘️', '↔️', '🎩', '💡']
for emoji in emojis_to_remove:
    content = content.replace(emoji, '')

# Write back
with open(r'c:\Users\gustu\OneDrive\Desktop\project web\sub project\emitscanindonesia-main\emitscanindonesia-main\app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("All emojis removed successfully!")
