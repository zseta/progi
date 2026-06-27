# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0](https://github.com/zseta/progi/compare/v0.3.2...v0.4.0) (2026-06-27)


### Features

* add adhoc step tool ([b43f93f](https://github.com/zseta/progi/commit/b43f93f289ddcfbd2bb17a85f39cbc959729ffeb))
* add parallel execution support for workflow steps (UI-only) ([#36](https://github.com/zseta/progi/issues/36)) ([82753f9](https://github.com/zseta/progi/commit/82753f92c2440e66bcb331445053efd84cd05746))
* add Playbook library ([#26](https://github.com/zseta/progi/issues/26)) ([1cd6842](https://github.com/zseta/progi/commit/1cd684282443a3ab3bc950f116638b2d470e66e5))
* add rename workflow button ([#22](https://github.com/zseta/progi/issues/22)) ([125fc6f](https://github.com/zseta/progi/commit/125fc6f43570a034160bc04086055d9b571f4668))
* Add support for looping workflows ([#23](https://github.com/zseta/progi/issues/23)) ([1804e91](https://github.com/zseta/progi/commit/1804e91aa6001ad17269ec809fb65d12a0220e51))
* add tools for managing workflow steps (add, edit, delete) ([8998cad](https://github.com/zseta/progi/commit/8998cad3e01dac758be505ef68848f903250613f))
* Board view updates ([#25](https://github.com/zseta/progi/issues/25)) ([becd27b](https://github.com/zseta/progi/commit/becd27b7cf08723bf286371469f6510f453f2666))
* copy button on library playbook card ([75fa634](https://github.com/zseta/progi/commit/75fa634fd2e1f28b1fc68d5ba5613350c1c91c3d))
* delete task ([cd3207d](https://github.com/zseta/progi/commit/cd3207d02c15a94b6780edee4e4325d4dc271faf))
* exportable workflow, remove update tool ([fd1d93d](https://github.com/zseta/progi/commit/fd1d93d404fbda839eaa1a2bb17c9af14ffed666))
* new tool for adhoc requests related to a task, even after completion ([dab9b9d](https://github.com/zseta/progi/commit/dab9b9df42197a22742e045aa06cfff07b8e98a6))
* remove specs and standardize playbooks ([#35](https://github.com/zseta/progi/issues/35)) ([b8f2cb4](https://github.com/zseta/progi/commit/b8f2cb46df3cda68e525a728267037b507b00aee))


### Bug Fixes

* add logo ([f5f29d9](https://github.com/zseta/progi/commit/f5f29d9c3941519d4d605a1c1b6dc9700931a222))
* add status filter ([73fd1a5](https://github.com/zseta/progi/commit/73fd1a5e98167d22e7d2f965a82c086d84eb839b))
* don't show progress notes on board view ([#19](https://github.com/zseta/progi/issues/19)) ([0720fa3](https://github.com/zseta/progi/commit/0720fa350f5c9e5e5b94ea307dd7968cbae7850b))
* font size (was too small) ([#27](https://github.com/zseta/progi/issues/27)) ([d5efa81](https://github.com/zseta/progi/commit/d5efa81a13b271ab6ce186b648d4ba177f897206))
* handle missing description in task input specification ([869dc8f](https://github.com/zseta/progi/commit/869dc8fe6c80c516fa00b0c517ea5e1edf7d8cd7))
* none edge by LLM ([a59213a](https://github.com/zseta/progi/commit/a59213aa4c023618b767b673460c09409e93d9a5))
* Penguin UI style fixes ([#28](https://github.com/zseta/progi/issues/28)) ([a1af7b7](https://github.com/zseta/progi/commit/a1af7b7e1a6def36ee45d64252b3f6d04b902c19))
* progress notes layout ([#24](https://github.com/zseta/progi/issues/24)) ([a301c51](https://github.com/zseta/progi/commit/a301c51b4bf1ad15e4e682afb4a4324769323d08))
* remove duplicated content in output ([82670cc](https://github.com/zseta/progi/commit/82670cc2cf77249466ffd6135ca3ce92f17d28e2))
* tighten MCP tool output hints ([#18](https://github.com/zseta/progi/issues/18)) ([3fdcfc9](https://github.com/zseta/progi/commit/3fdcfc92d43d87e5d1f173d4dccfd300d569a22f))

## [0.3.2](https://github.com/zseta/progi/compare/v0.3.1...v0.3.2) (2026-06-16)


### Bug Fixes

* trigger pypi vol2 ([#15](https://github.com/zseta/progi/issues/15)) ([5ad1c6d](https://github.com/zseta/progi/commit/5ad1c6d6bc69fd5b414d963d094d620a5d9879f8))

## [0.3.1](https://github.com/zseta/progi/compare/v0.3.0...v0.3.1) (2026-06-16)


### Bug Fixes

* delete workflows ([389f1ef](https://github.com/zseta/progi/commit/389f1ef94af4b2842b911526dabef0aa21845b86))
* display monitoring URL in MCP responses ([#12](https://github.com/zseta/progi/issues/12)) ([dde8538](https://github.com/zseta/progi/commit/dde85388c4c49c2a60cfe762988efa43a9ea54bc))

## [0.3.0](https://github.com/zseta/progi/compare/v0.2.1...v0.3.0) (2026-06-16)


### Features

* implement zoom and pan functionality for workflow editor ([#8](https://github.com/zseta/progi/issues/8)) ([da8dec2](https://github.com/zseta/progi/commit/da8dec26c062b61e145a0c9037327eadfcc16b83))


### Bug Fixes

* increase base font sizes for readability ([#9](https://github.com/zseta/progi/issues/9)) ([0b7b907](https://github.com/zseta/progi/commit/0b7b907039f54d19475760baf04fd0d882298aa1))

## [0.2.1](https://github.com/zseta/progi/compare/v0.2.0...v0.2.1) (2026-06-15)


### Bug Fixes

* bundle alembic/ inside the package ([#6](https://github.com/zseta/progi/issues/6)) ([9065c58](https://github.com/zseta/progi/commit/9065c581edfd0daa961ed4fd658c0295211255dc))

## [0.2.0](https://github.com/zseta/progi/compare/v0.1.2...v0.2.0) (2026-06-15)


### Features

* add favicon ([a500a91](https://github.com/zseta/progi/commit/a500a919c3aabca63b1853e5ea346c3c5ff65077))
* auto-run Alembic migrations on startup ([19fe3b5](https://github.com/zseta/progi/commit/19fe3b5b5042a9f4e9a97ea0bf91899ff4643d00))


### Documentation

* add workflow authoring example ([d5cafb1](https://github.com/zseta/progi/commit/d5cafb1612b3ca97fbe2a7adf257e9acf870bfd3))
* keep commit messages short ([42a4641](https://github.com/zseta/progi/commit/42a46418d0d96966528fad7a53f4ad29c7c79cbd))

## [0.1.2](https://github.com/zseta/progi/compare/v0.1.1...v0.1.2) (2026-06-15)


### Bug Fixes

* correct Tailwind ([#4](https://github.com/zseta/progi/issues/4)) ([8eb2ed8](https://github.com/zseta/progi/commit/8eb2ed83725f06adb89480cd36a0c805fb9cd49f))


### Documentation

* fix ruff check path and add commit convention to AGENTS.md ([5776890](https://github.com/zseta/progi/commit/577689074badde3d555ba2037eee6db1bf258dbc))
* move conventional commits guide to CONTRIBUTING.md, add note to CLAUDE.md ([9e1a3bf](https://github.com/zseta/progi/commit/9e1a3bf7d8b06550539b95f0d4d66d4bdeb82436))

## [0.1.1](https://github.com/zseta/progi/compare/v0.1.0...v0.1.1) (2026-06-15)


### Documentation

* move conventional commits guide to CONTRIBUTING.md, add note to CLAUDE.md ([9e1a3bf](https://github.com/zseta/progi/commit/9e1a3bf7d8b06550539b95f0d4d66d4bdeb82436))

## [0.1.1] - 2026-06-15

### Changed

- Added PyPI metadata: keywords, classifiers, project URLs.

[0.1.1]: https://github.com/zseta/progi/releases/tag/v0.1.1

## [0.1.0] - 2026-06-15

### Added

- Initial release.

[0.1.0]: https://github.com/zseta/progi/releases/tag/v0.1.0
