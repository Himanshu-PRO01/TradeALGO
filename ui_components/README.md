# TradeALGO UI Components

This folder is the shared drop-zone for UI components, assets, snippets, and design files that will be used to improve the TradeALGO interface.

## How to use this folder

Paste/download UI component files into this folder. Keep the original filenames when possible.

Supported examples:
- HTML/CSS component snippets
- JavaScript/TypeScript UI components
- SVG icons
- PNG/WebP/JPG assets
- JSON theme/config files
- component documentation
- ZIP files containing a component

## Integration rule

Components placed here are **source material**. They should not automatically be imported everywhere.

When updating TradeALGO UI:
1. Inspect the component and its dependencies.
2. Identify the page(s) where it improves the UX.
3. Adapt it to TradeALGO's Streamlit architecture and existing dark trading-desk theme.
4. Preserve existing navigation, safety behavior, and functionality.
5. Reuse shared components across pages when appropriate instead of duplicating code.
6. Test the affected page(s) before committing.

## Recommended organization

You can optionally create subfolders such as:

- `ui_components/cards/`
- `ui_components/buttons/`
- `ui_components/navigation/`
- `ui_components/charts/`
- `ui_components/animations/`
- `ui_components/icons/`
- `ui_components/backgrounds/`

You can also simply drop files into this folder and I will organize them when we integrate them.

## Important

Do not put API keys, passwords, broker credentials, private tokens, or other secrets in this folder.
