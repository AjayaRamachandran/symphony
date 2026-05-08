import re

raw = open("scripts/packages_raw.txt").read()

packages = []
for line in raw.strip().splitlines():
    match = re.match(r"(.+?):\s+Bytes :\s+(\d+)", line)
    if match:
        name = match.group(1).strip()
        size = int(match.group(2))
        packages.append((name, size))

packages.sort(key=lambda x: x[1], reverse=True)

with open("scripts/packages_sorted.md", "w") as f:
    f.write("| Package | Size (MB) |\n")
    f.write("|---|---|\n")
    for name, size in packages:
        mb = round(size / (1024 * 1024), 1)
        f.write(f"| {name} | {mb} |\n")
    f.write(f"\n**Total: {round(sum(s for _, s in packages) / (1024*1024), 1)} MB**\n")

print("Written to packages_sorted.md")