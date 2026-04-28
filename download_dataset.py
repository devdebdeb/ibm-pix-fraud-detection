import shutil
import kagglehub
from pathlib import Path

path = kagglehub.dataset_download("mlg-ulb/creditcardfraud")

dest = Path("data/raw")
dest.mkdir(parents=True, exist_ok=True)

for file in Path(path).iterdir():
    shutil.copy(file, dest / file.name)
    print(f"Copied {file.name} -> {dest / file.name}")

print("Done. Dataset available at data/raw/")
