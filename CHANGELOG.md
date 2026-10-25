# Changelog

The versions of this package have three parts, `design.breaking.compatible`: the first changes with a redesign, the second with a change that breaks existing users, the third with every other change. Newest first. Each entry is written from the issues closed since the previous release.

## 1.1.0-alpha (2026-10-25)

* Breaking change: The package needs Primitives 1.1.0-alpha or later, whose types check what their standards say; its dependency ranges end before the first pre-release of the next second part (#10).
* Fixed: Four tests use a UTI that does not start with a valid LEI (#3).

## 1.0.0-alpha (2026-10-23)

* Added: The first version of the package.
