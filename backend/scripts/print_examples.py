import json
with open("../data/enron_evaluation/manifest.json", "r", encoding="utf-8") as f:
    manifest = json.load(f)

for i, idx in enumerate([0, 150, 350], 1):
    item = manifest[idx]
    print(f"=== EXAMPLE {i}: {item['document_id']} ({item['split'].upper()}) ===")
    print(f"Filename:  {item['filename']}")
    print(f"Custodian: {item['custodian']} (Folder: {item['folder']})")
    print(f"Date:      {item['date']}")
    print(f"From:      {item['sender']}")
    print(f"To:        {item['recipient']}")
    print(f"Subject:   {item['subject']}")
    print(f"Preview:   {item['text_preview'][:200]}...\n")
