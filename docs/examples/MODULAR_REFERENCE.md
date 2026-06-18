# Modular Reference Example

This example shows how to use the template's architecture without assuming a specific product, framework, or runtime.

The goal is not to provide production code. The goal is to show the dependency direction:

```text
plugins -> providers -> core
```

`core/` owns stable behavior. `providers/` adapt outside systems. `plugins/` compose optional capabilities.

## Example scenario

Imagine a project needs to normalize an input item, save it somewhere, and optionally expose that behavior as an extension.

This can be modeled without committing to a database, API, queue, CLI, or web framework.

## 1) Core behavior

`core/` defines the stable rules and contracts.

```text
core/item-normalizer.pseudo

function normalizeItem(input): NormalizedItem
  require input.name is not empty

  return {
    name: trim(input.name),
    slug: lowercase(replaceSpaces(input.name, "-"))
  }
```

Why it belongs in `core/`:

- it does not know where data came from
- it does not know where data will be stored
- it is easy to test in isolation
- it can be reused by many interfaces

## 2) Provider adapter

`providers/` connects the core behavior to an outside system.

```text
providers/item-store.pseudo

interface ItemStore
  save(item): SaveResult

class FileItemStore implements ItemStore
  save(item)
    write item to configured file path
```

Why it belongs in `providers/`:

- file storage is an implementation detail
- it can later be swapped for an API, database, queue, or memory store
- `core/` does not need to change when storage changes

## 3) Optional plugin

`plugins/` wires optional behavior together.

```text
plugins/save-normalized-item.pseudo

function createSaveNormalizedItemPlugin(itemStore)
  return function run(input)
    item = normalizeItem(input)
    return itemStore.save(item)
```

Why it belongs in `plugins/`:

- it composes core behavior with a provider
- it can be enabled, replaced, or removed
- it keeps optional workflow logic outside the core layer

## 4) Configuration

`config/` documents runtime choices without hardcoding machine-specific values.

```text
config/item-store.example

ITEM_STORE_KIND=file
ITEM_STORE_PATH=./data/items.json
```

Keep real secrets, local-only paths, and machine-specific values out of committed files.

## 5) Tests

`tests/` should start closest to the core behavior.

```text
tests/unit/item-normalizer.test.pseudo

input:  { name: " Example Item " }
output: { name: "Example Item", slug: "example-item" }
```

Suggested test layers:

- unit tests for `core/` behavior
- integration tests for `providers/`
- plugin tests for composition boundaries

## Dependency rule

The important rule is direction:

```text
core: knows only stable rules
providers: know outside systems and implement contracts
plugins: compose optional workflows
```

Avoid this:

```text
core -> providers
core -> plugins
```

That direction makes the template harder to reuse and harder to test.

## How to adapt this example

When starting a real project:

1. Put pure behavior and contracts in `core/`.
2. Put external systems in `providers/`.
3. Put optional feature wiring in `plugins/`.
4. Put safe examples and schemas in `config/`.
5. Put validation coverage in `tests/`.

Keep the seams boring. Boring seams make future changes cheap.
