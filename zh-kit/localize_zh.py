#!/usr/bin/env python3
"""Apply the Chinese layer and bump the app version.

Runs in a checkout that was just reset to the upstream tree, with this folder
(`zh-kit/`) copied in from the fork's automation branch.

  python3 zh-kit/localize_zh.py

It changes four things and nothing else:
  1. apps/robertn_store/locales/zh-CN.json: the word overrides below, plus the
     hmiLanguages / rhmiTexts / font defaults it needs to be offered at all.
  2. apps/robertn_store/src/store.js: i18n.setHmiLanguage(value) is pinned to
     CHINESISCH_SIMPLE, so the drawn pages are Chinese whatever the unit's HMI
     language is. Exactly one occurrence, else it stops.
  3. apps/robertn_store/package/package.json: the credit line in description.
  4. apps/robertn_store/mgu-app.json + package/package.json: version bumped one
     patch above upstream, which is what makes the car see an update at all
     (the updater compares only the first three segments, js/catalog.js).

Stale robertn_store@*.src.tgz / *.tgz committed in the tree are removed: the
unit's own build writes the one its version names.
"""

import json
import pathlib
import re
import sys

FORCED_HMI_LANGUAGE = "CHINESISCH_SIMPLE"
CREDIT = "Translation by: LEON HAU"
KIT = pathlib.Path(__file__).resolve().parent


def fail(message):
    print("zh-kit: " + message, file=sys.stderr)
    sys.exit(1)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


app = pathlib.Path("apps/robertn_store")
if not app.is_dir():
    fail("apps/robertn_store is not here; run this from the repository root")

manifest_path = app / "mgu-app.json"
package_path = app / "package/package.json"
locales_path = app / "locales/zh-CN.json"
store_js = app / "src/store.js"

for path in (manifest_path, locales_path, store_js):
    if not path.is_file():
        fail("%s is missing; upstream changed the layout" % path)

# 1. words
overrides = load(KIT / "zh_overrides.json").get("words") or {}
data = load(locales_path)
words = data.get("words") or {}
if not words:
    fail("locales/zh-CN.json has no words")
applied, skipped = 0, []
for key, value in overrides.items():
    if key in words:
        if words[key] != value:
            words[key] = value
            applied += 1
    else:
        skipped.append(key)
data.setdefault("hmiLanguages", ["CHINESISCH_SIMPLE", "KANTONESISCH_SIMPLE"])
data.setdefault("rhmiTexts", ["zh_CN", "zh_yue_Hans_CN"])
data.setdefault("font", "chinese")
save(locales_path, data)

# 2. pinned language
code = store_js.read_text(encoding="utf-8")
pattern = re.compile(r"i18n\.setHmiLanguage\(\s*value\s*\)")
if len(pattern.findall(code)) != 1:
    fail("store.js no longer has exactly one i18n.setHmiLanguage(value); "
         "the language choice moved, review this step by hand")
store_js.write_text(pattern.sub("i18n.setHmiLanguage('%s')" % FORCED_HMI_LANGUAGE, code), encoding="utf-8")

# 3. credit
pkg = load(package_path)
if CREDIT not in (pkg.get("description") or ""):
    pkg["description"] = ((pkg.get("description") or "") + "（" + CREDIT + "）").strip()
    save(package_path, pkg)

# 4. version: one patch above upstream, so the car sees an update
manifest = load(manifest_path)
upstream = str(manifest.get("version") or "")
parts = upstream.split(".")
if len(parts) != 3 or not all(p.isdigit() for p in parts):
    fail("mgu-app.json version %r is not x.y.z" % upstream)
bumped = "%s.%s.%d" % (parts[0], parts[1], int(parts[2]) + 1)
manifest["version"] = bumped
save(manifest_path, manifest)
pkg = load(package_path)
pkg["version"] = bumped
save(package_path, pkg)

for stale in list(app.glob("robertn_store@*.src.tgz")) + list(app.glob("robertn_store@*.tgz")):
    stale.unlink()

print("zh-kit: words %d, overridden %d%s" % (len(words), applied,
                                             (", skipped %s" % skipped) if skipped else ""))
print("zh-kit: version %s -> %s" % (upstream, bumped))
