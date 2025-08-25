"""
Quick fix for BUDDY backend type annotations
"""

import re

def fix_type_annotations():
    file_path = r"C:\Users\shrim\Documents\WASE_PROJECT\BUDDY_2.0\enhanced_backend.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace BuddyDatabase = Depends with Optional[BuddyDatabase] = Depends
    content = re.sub(
        r'db: BuddyDatabase = Depends\(get_db\)',
        r'db: Optional[BuddyDatabase] = Depends(get_db)',
        content
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed type annotations successfully!")

if __name__ == "__main__":
    fix_type_annotations()
